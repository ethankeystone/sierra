"""
Report generation for Sierra Outfitters.

Writes two kinds of output after each test run:
  - One markdown file per test in reports/<domain>/<test_name>.md
  - A summary index at reports/report.md
"""
from __future__ import annotations

import json
import textwrap
from collections import defaultdict
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

REPORTS_DIR = Path(__file__).parent.parent / "tests" / "integration" / "reports"


# ── Failure extraction ────────────────────────────────────────────────────────

def extract_failure_reason(longrepr) -> str:
    """Pull a concise failure message out of pytest's longrepr object."""
    if longrepr is None:
        return ""
    text = str(longrepr)
    e_lines = [l for l in text.splitlines() if l.strip().startswith("E ")]
    if e_lines:
        return "\n".join(l.strip()[2:].strip() for l in e_lines[:6])
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


# ── Trajectory rendering ──────────────────────────────────────────────────────

def _render_note(turn: dict[str, Any]) -> list[str]:
    return [f"> ℹ️ *{turn['content']}*\n"]


def _render_user(turn: dict[str, Any]) -> list[str]:
    return [f"> **User:** {turn['content']}\n"]


def _render_assistant(turn: dict[str, Any]) -> list[str]:
    return [f"> **Sierra Outfitters:** {turn.get('content') or ''}\n"]


def _render_tool_call(turn: dict[str, Any]) -> list[str]:
    name   = turn.get("name", "?")
    args   = json.dumps(turn.get("args", {}), indent=2)
    result = json.dumps(turn.get("result"), indent=2)
    return [
        f"**🔧 `{name}`**\n",
        f"**Args:**\n```json\n{args}\n```\n",
        f"**Result:**\n```json\n{result}\n```\n",
    ]


def _render_llm_call(turn: dict[str, Any]) -> list[str]:
    round_num = turn.get("round", "?")
    messages  = turn.get("messages", [])
    label = f"#{round_num}" if isinstance(round_num, int) else round_num
    lines = [f"<details><summary>🤖 LLM Call {label} — {len(messages)} messages</summary>\n"]
    for msg in messages:
        role    = msg.get("role", "?")
        content = msg.get("content") or ""
        if msg.get("tool_calls"):
            tc_text = json.dumps(msg["tool_calls"], indent=2)
            lines.append(f"\n**[{role}]** *(tool calls)*\n```json\n{tc_text}\n```\n")
        elif role == "tool":
            result_text = json.dumps(content, indent=2) if not isinstance(content, str) else content
            tool_id = msg.get("tool_call_id", "")
            lines.append(f"\n**[tool result]** `{tool_id}`\n```json\n{result_text}\n```\n")
        else:
            lines.append(f"\n**[{role}]**\n```\n{content}\n```\n")
    lines.append("</details>\n")
    return lines


_RENDERERS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "note":      _render_note,
    "user":      _render_user,
    "assistant": _render_assistant,
    "tool_call": _render_tool_call,
    "llm_call":  _render_llm_call,
}


def render_trajectory(traj: list[dict[str, Any]]) -> list[str]:
    """Convert a list of trajectory turn dicts into markdown lines."""
    lines: list[str] = []
    for turn in traj:
        renderer = _RENDERERS.get(turn.get("type"))
        if renderer:
            lines.extend(renderer(turn))
    return lines


# ── Per-test report ───────────────────────────────────────────────────────────

def write_test_report(r: dict[str, Any], domain_dir: Path) -> None:
    """Write a single test's markdown report into domain_dir."""
    test_name = r["nodeid"].split("::")[-1]
    icon      = "✅" if r["passed"] else "❌"

    lines: list[str] = []
    lines.append(f"# {icon} {test_name}\n")
    lines.append(f"**Domain:** {r['domain']}  ")
    lines.append(f"**Date:** {date.today().isoformat()}\n")
    lines.append("---\n")

    docstring = r.get("docstring", "").strip()
    if docstring:
        lines.append("## What this test checks\n")
        lines.append(textwrap.indent(docstring, "> "))
        lines.append("")

    lines.append("## Outcome\n")
    if r["passed"]:
        lines.append("**PASSED** — all assertions met.\n")
    else:
        lines.append("**FAILED**\n")
        reason = r.get("failure_reason", "")
        if reason:
            lines.append(f"**Failure reason:**\n```\n{reason}\n```\n")

    traj = r.get("trajectory", [])
    if traj:
        lines.append("## Conversation\n")
        lines.extend(render_trajectory(traj))

    (domain_dir / f"{test_name}.md").write_text("\n".join(lines))


# ── Summary report ────────────────────────────────────────────────────────────

def write_summary_report(results: list[dict[str, Any]]) -> None:
    """Write reports/report.md — a top-level index linking to every test report."""
    integration = [r for r in results if "integration" in r["nodeid"]]
    if not integration:
        return

    total_passed   = sum(1 for r in integration if r["passed"])
    total_earned   = sum(r["weight"] for r in integration if r["passed"])
    total_possible = sum(r["weight"] for r in integration)

    lines: list[str] = []
    lines.append(f"# Sierra Outfitters Eval Summary — {date.today().isoformat()}\n")
    lines.append(f"**{total_passed}/{len(integration)} tests passed**\n")
    lines.append("")

    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in integration:
        by_domain[r["domain"]].append(r)

    for domain, dresults in sorted(by_domain.items()):
        earned       = sum(r["weight"] for r in dresults if r["passed"])
        possible     = sum(r["weight"] for r in dresults)
        passed_count = sum(1 for r in dresults if r["passed"])
        pct          = int(100 * earned / possible) if possible else 0
        bar          = "█" * (pct // 10) + "░" * (10 - pct // 10)
        icon         = "✅" if pct == 100 else ("⚠️" if pct >= 60 else "❌")
        domain_slug  = domain.lower().replace(" ", "_")

        lines.append(f"## {icon} {domain} — {pct}% ({passed_count}/{len(dresults)} tests)\n")
        lines.append(f"`{bar}`\n")

        for r in dresults:
            test_name = r["nodeid"].split("::")[-1]
            status    = "✅" if r["passed"] else "❌"
            rel_path  = f"{domain_slug}/{test_name}.md"
            reason    = (
                f" — {r['failure_reason'].splitlines()[0]}"
                if not r["passed"] and r.get("failure_reason") else ""
            )
            lines.append(f"- {status} [{test_name}]({rel_path}){reason}")

        lines.append("")

    (REPORTS_DIR / "report.md").write_text("\n".join(lines))
