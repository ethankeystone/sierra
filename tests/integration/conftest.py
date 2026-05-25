"""
Shared fixtures and pytest plugin for Sierra Outfitters integration evals.

Fixtures
--------
seeded_db   — clears and re-seeds the DB before every test from a known
              deterministic state. Function-scoped so tests never bleed into
              each other. Returns {sku_a, sku_b} metadata.

tracer      — spy on Registry.execute: records every tool call without
              changing behaviour. Yields list[ToolCall].

trajectory  — autouse list[dict] attached to each test node; passed to
              run_conversation() so the conversation is captured and written
              into the markdown report.

Plugin hooks (in call order)
-----------------------------
pytest_addoption        → startup: register --save-trajectories flag
pytest_configure        → startup: register weight marker
pytest_sessionstart     → before any tests: wipe reports dir
pytest_runtest_makereport  → after each test body: attach eval metadata to report
pytest_runtest_logreport   → after each test body: write markdown + accumulate results
pytest_terminal_summary    → after all tests: print scorecard, write summary report
"""
from __future__ import annotations

import inspect
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent import cli
from db import get_connection
from tools import Registry

from .helpers import ToolCall
from helpers.reporting import (
    REPORTS_DIR,
    extract_failure_reason,
    write_test_report,
    write_summary_report,
)


# ── Module-level plugin state ─────────────────────────────────────────────────

_RESULTS: list[dict] = []
_terminal_reporter   = None
_TRAJECTORIES_DIR    = Path(__file__).parent / "trajectories"


# ── DB seed ───────────────────────────────────────────────────────────────────

def _do_seed() -> dict:
    """
    Clear the DB via CLI, seed products via CLI, then insert deterministic
    test fixtures directly. Returns {sku_a, sku_b} so tests have concrete SKUs.
    """
    runner = CliRunner()

    result = runner.invoke(cli, ["clear", "--yes"])
    assert result.exit_code == 0, f"'clear' failed:\n{result.output}"

    result = runner.invoke(cli, ["seed"])
    assert result.exit_code == 0, f"'seed' failed:\n{result.output}"

    conn = get_connection()

    # Wipe seed promotions — tests define their own controlled fixtures below,
    # preventing PROMO-EARLY-RISERS from the seed data interfering with claim tests.
    conn.execute("DELETE FROM promotion_tags")
    conn.execute("DELETE FROM promotions")
    conn.commit()

    # Two known customers with fixed IDs matching CreateOrderTool's format
    conn.executemany(
        "INSERT OR REPLACE INTO customers (id, name, email) VALUES (?,?,?)",
        [
            ("USR-001", "Alice Anderson", "alice@test.com"),
            ("USR-002", "Bob Baker",      "bob@test.com"),
        ],
    )

    # Two guaranteed in-stock SKUs from the real products.json seed
    rows = conn.execute(
        "SELECT sku, name, price FROM products WHERE inventory > 0 ORDER BY sku LIMIT 2"
    ).fetchall()
    assert len(rows) >= 2, "Need at least 2 in-stock products from products.json"
    sku_a = dict(rows[0])
    sku_b = dict(rows[1])

    # Pre-existing orders for Alice (TORD-001, TORD-002) and Bob (TORD-003).
    # Prefixed with TORD- so they never collide with real order IDs (W001–W010)
    # from the seed data and don't corrupt the DB after tests finish.
    conn.executemany(
        "INSERT OR REPLACE INTO orders (id, customer_id, status, tracking_number) "
        "VALUES (?,?,?,?)",
        [
            ("TORD-001", "USR-001", "in_transit", "TRK-TEST-001"),
            ("TORD-002", "USR-001", "delivered",  "TRK-TEST-002"),
            ("TORD-003", "USR-002", "pending",     None),
        ],
    )
    conn.executemany(
        "INSERT INTO order_items (order_id, sku) VALUES (?,?)",
        [
            ("TORD-001", sku_a["sku"]),
            ("TORD-002", sku_b["sku"]),
            ("TORD-003", sku_a["sku"]),
        ],
    )

    # Always-out-of-stock product for OOS rejection tests
    conn.execute(
        "INSERT OR REPLACE INTO products (sku, name, inventory, price, description) "
        "VALUES (?,?,?,?,?)",
        ("OOS-TEST", "Perpetually Out-of-Stock Widget", 0, 9.99,
         "Internal test product — always has zero inventory."),
    )
    conn.execute(
        "INSERT OR IGNORE INTO product_tags (sku, tag) VALUES (?,?)",
        ("OOS-TEST", "Hiking"),
    )

    # Active promotion — must be surfaced by the agent on first turn
    conn.execute(
        "INSERT OR REPLACE INTO promotions "
        "(id, title, code, discount_pct, valid_from, valid_until, description) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            "PROMO-ACTIVE", "Trail Blazer Sale", "TRAIL20", 20,
            "2020-01-01 00:00:00", "2099-12-31 23:59:59",
            "20% off all hiking gear for early risers.",
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO promotion_tags (promo_id, tag) VALUES (?,?)",
        ("PROMO-ACTIVE", "Hiking"),
    )

    # Expired promotion — must never appear in responses
    conn.execute(
        "INSERT OR REPLACE INTO promotions "
        "(id, title, code, discount_pct, valid_from, valid_until, description) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            "PROMO-EXPIRED", "Ancient Deal", "OLD99", 99,
            "2000-01-01 00:00:00", "2000-12-31 23:59:59",
            "Long-expired promotion — should never be surfaced.",
        ),
    )

    conn.commit()
    conn.close()

    return {"sku_a": sku_a, "sku_b": sku_b}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def seeded_db():
    """Fresh clear+seed before every test. Returns {sku_a, sku_b} metadata."""
    return _do_seed()


@pytest.fixture
def tracer():
    """
    Spy on Registry.execute for the duration of one test.

    Wraps the real method so every tool call is recorded in a list of
    ToolCall(name, kwargs, result) without changing behaviour.
    """
    calls: list[ToolCall] = []
    original = Registry.execute

    def _spy(self, name: str, **kwargs):
        result = original(self, name, **kwargs)
        calls.append(ToolCall(name, kwargs, result))
        return result

    with patch.object(Registry, "execute", _spy):
        yield calls


@pytest.fixture(autouse=True)
def trajectory(request):
    """
    Per-test conversation log (autouse — always present even if not requested).

    Tests pass this list to run_conversation(trajectory=trajectory) to capture
    every user turn, tool call, and assistant reply. Written into the markdown
    report by pytest_runtest_logreport.
    """
    traj: list[dict] = []
    request.node._eval_trajectory = traj
    yield traj


# ── Hooks ─────────────────────────────────────────────────────────────────────

# Called once at startup before collection — registers custom CLI flags.
def pytest_addoption(parser):
    parser.addoption(
        "--save-trajectories",
        action="store_true",
        default=False,
        help=(
            f"Save eval trajectories to {_TRAJECTORIES_DIR}/. "
            "One JSON file per test, organised by domain."
        ),
    )


# Called once at startup after option parsing — registers custom markers.
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "weight(n): point value of this eval test (default 1). "
        "Use 2 for important checks, 3 for critical correctness/security.",
    )


# Called once before any tests are collected or run.
def pytest_sessionstart(session):
    global _terminal_reporter
    _terminal_reporter = session.config.pluginmanager.get_plugin("terminalreporter")

    # Wipe and recreate reports dir so each run is a clean slate
    if REPORTS_DIR.exists():
        shutil.rmtree(REPORTS_DIR)
    REPORTS_DIR.mkdir()

    # Wipe trajectories dir only when --save-trajectories is active
    if session.config.getoption("--save-trajectories"):
        if _TRAJECTORIES_DIR.exists():
            shutil.rmtree(_TRAJECTORIES_DIR)
        _TRAJECTORIES_DIR.mkdir()


# Called after each test phase (setup / call / teardown).
# hookwrapper=True lets us yield first so pytest generates the report object,
# then we augment it with eval-specific metadata before it's consumed downstream.
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if call.when != "call":
        return

    report = outcome.get_result()

    weight = 1
    for m in item.iter_markers("weight"):
        weight = m.args[0]
        break
    report.eval_weight = weight

    fn = getattr(item, "function", None)
    report.eval_docstring = inspect.getdoc(fn) if fn else ""

    report.eval_failure_reason = (
        extract_failure_reason(report.longrepr) if not report.passed else ""
    )

    report.eval_trajectory = list(getattr(item, "_eval_trajectory", []))


# Called after makereport for each phase — we act only on the "call" phase
# (the test body itself) to write the per-test markdown and accumulate results.
def pytest_runtest_logreport(report):
    if report.when != "call":
        return
    if "integration" not in report.nodeid:
        return

    weight = getattr(report, "eval_weight", 1)
    traj   = getattr(report, "eval_trajectory", [])

    domain = (
        Path(report.nodeid.split("::")[0]).name
        .replace("eval_", "")
        .replace(".py", "")
        .replace("_", " ")
        .title()
    )

    # Optionally persist raw trajectory JSON alongside the markdown
    if (
        _terminal_reporter is not None
        and _terminal_reporter.config.getoption("--save-trajectories")
    ):
        domain_dir = _TRAJECTORIES_DIR / domain.lower().replace(" ", "_")
        domain_dir.mkdir(exist_ok=True)
        (domain_dir / f"{report.nodeid.split('::')[-1]}.json").write_text(
            json.dumps({
                "nodeid": report.nodeid,
                "domain": domain,
                "passed": report.passed,
                "weight": weight,
                "turns":  traj,
            }, indent=2)
        )

    # Accumulate result and write per-test markdown report
    result = {
        "nodeid":         report.nodeid,
        "domain":         domain,
        "passed":         report.passed,
        "weight":         weight,
        "docstring":      getattr(report, "eval_docstring", ""),
        "failure_reason": getattr(report, "eval_failure_reason", ""),
        "trajectory":     traj,
    }
    _RESULTS.append(result)

    domain_dir = REPORTS_DIR / domain.lower().replace(" ", "_")
    domain_dir.mkdir(exist_ok=True)
    write_test_report(result, domain_dir)


# Called once after all tests finish — prints the scorecard to the terminal
# and writes the summary markdown report.
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    integration = [r for r in _RESULTS if "integration" in r["nodeid"]]
    if not integration:
        return

    from collections import defaultdict
    by_domain: dict[str, list] = defaultdict(list)
    for r in integration:
        by_domain[r["domain"]].append(r)

    terminalreporter.write_sep("=", "SIERRA EVAL SCORECARD")
    terminalreporter.write_line("")

    rows = []
    total_earned = total_possible = total_passed = total_count = 0

    for domain, results in sorted(by_domain.items()):
        earned   = sum(r["weight"] for r in results if r["passed"])
        possible = sum(r["weight"] for r in results)
        tp = sum(1 for r in results if r["passed"])
        tt = len(results)
        pct = int(100 * earned / possible) if possible else 0
        rows.append((domain, tp, tt, earned, possible, pct))
        total_earned   += earned
        total_possible += possible
        total_passed   += tp
        total_count    += tt

    col_w  = max(len(r[0]) for r in rows) + 2
    header = f"  {'Domain':<{col_w}}  {'Tests':>8}  {'W.Score':>9}  {'Pct':>5}  {'Progress':}"
    terminalreporter.write_line(header)
    terminalreporter.write_line("  " + "-" * (len(header) - 2))

    for domain, tp, tt, earned, possible, pct in rows:
        bar    = "█" * (pct // 10) + "░" * (10 - pct // 10)
        status = "✓" if pct == 100 else ("~" if pct >= 60 else "✗")
        terminalreporter.write_line(
            f"  {domain:<{col_w}}  {tp:>3}/{tt:<4}  {earned:>4}/{possible:<4}  "
            f"{pct:>3}%  {bar}  {status}"
        )

    overall_pct = int(100 * total_earned / total_possible) if total_possible else 0
    terminalreporter.write_line("  " + "-" * (len(header) - 2))
    terminalreporter.write_line(
        f"  {'OVERALL':<{col_w}}  {total_passed:>3}/{total_count:<4}  "
        f"{total_earned:>4}/{total_possible:<4}  {overall_pct:>3}%"
    )
    terminalreporter.write_line("")
    terminalreporter.write_sep("=", "")

    write_summary_report(_RESULTS)
    terminalreporter.write_line(f"  Per-test reports written to: {REPORTS_DIR}")
