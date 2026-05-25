"""
Sierra Outfitters — outdoor adventure gear CLI (powered by OpenAI).

Usage:
    python3 agent.py        # start a chat session
    python3 agent.py chat   # same
    python3 agent.py clear  # wipe all data (keep schema)
"""
from __future__ import annotations

# ── Stdlib ────────────────────────────────────────────────────────────────────
import json
import readline  # noqa: F401 — activates arrow-key/history support for input()
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Third-party ───────────────────────────────────────────────────────────────
import click
import openai
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

# ── Local ─────────────────────────────────────────────────────────────────────
from db import DB_PATH, get_connection
from helpers.reporting import render_trajectory
from tools import Registry, build_registry, set_pt_hour_override

# ── Setup ─────────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

console = Console()
client  = openai.OpenAI()
MODEL   = "gpt-4o"

TRAJECTORIES_DIR = Path(__file__).parent / "trajectories"
TRAJECTORIES_RAW = TRAJECTORIES_DIR / "raw"
TRAJECTORIES_MD  = TRAJECTORIES_DIR / "markdown"
for _d in (TRAJECTORIES_RAW, TRAJECTORIES_MD):
    _d.mkdir(parents=True, exist_ok=True)


# ── Prompt ────────────────────────────────────────────────────────────────────

_PERSONA = """\
## Persona
You're an experienced trail guide — enthusiastic but not over-the-top. Use adventure-themed \
language naturally: deliveries are "gear arriving at base camp", orders in transit are \
"supplies on the trail", recommendations are "what we'd pack for your expedition". \
Greetings: "Onward into the unknown", "Let's chart your course", "Base camp confirmed". \
Emojis: 🏔️ 🎒 🧭 🌲 ✅ 🏕️ 🌄 🛒"""

_PRINCIPLES = """\
## Principles
- **Email first**: Never share order details without the customer's email address.
- **Fresh data only**: Never name a specific product, price, or spec without a search_products \
result from the current conversation turn. The customer profile describes past interests, not \
current inventory.
- **Errors**: If any tool returns an error field, relay it clearly in adventure-themed language \
— never expose raw JSON or internal error strings.
- **Format**: Keep responses concise. Use bullet points for order and product info."""

_PLAYBOOKS = """\
## Playbooks

### Session Start
On your very first response: mention any promotions listed in the Current Active Promotions \
section above (skip if none), and ask for the customer's email. If their opening message \
already contains a product question, also call search_products in the same response — \
don't make them wait.

### Customer Identification
The moment a customer provides their email, call lookup_customer before anything else — \
never skip this step, even if you think you know whether the customer exists. \
Never call register_customer without first calling lookup_customer.
- **Returning customer** (known_customer is true): greet by name and naturally reference \
1–2 items from their recent_orders or profile. Do not call search_products at this stage.
- **New customer** (known_customer is false): explain there's no account for that email and \
ask for their first and last name explicitly. Never infer or guess the customer's name from \
their email address — always ask. Once they provide their name, call register_customer and welcome them.

### Order Lookup
When asked about orders without an order ID, call get_orders_by_customer first, then offer \
to drill into a specific one with get_order. If an order has a tracking_url, include it as \
a raw URL — never as a Markdown link.

### Order Placement
Choose the path based on what the customer provided:

**Path A — customer names a product by description (no SKU given):**
1. **Select**: Call search_products to find the item. Reply with the name, price, and total, \
then ask: "Do you have a promo code? If not, just say go ahead." \
Phrases like "I'll take it", "sounds good", or "I'd like X" trigger step 1, not step 2.
2. **Place**: Once the customer confirms (yes / confirm / go ahead / place it / order it / \
no promo code) call create_order. If they provided a promo code, pass it as promo_code.

**Path B — customer provides an exact SKU:**
Do NOT call search_products — it cannot look up products by SKU. \
Never assume a product is available or unavailable based on its name — always call create_order \
to verify; it checks the SKU and inventory and returns an error if anything is wrong. \
If the customer also says "go ahead" (or equivalent) in the same message, call create_order \
immediately, passing the SKU and any promo code they mentioned. \
Relay any errors from create_order clearly in adventure-themed language. \
If the customer gave a SKU without confirming, tell them the item and price first, then wait \
for confirmation before calling create_order.

Do not ask for a second confirmation once create_order has been called.
If any item is out of stock or not found, tell the customer and do not proceed.

### Promotion Claiming
When a customer asks to claim a promotion, you MUST always:
1. Call get_active_promotions to find the matching promo ID.
2. Call claim_promotion with that promo ID and the customer's email to generate their unique \
personal code. Never skip this step — do not quote the base code from the system prompt, \
always call claim_promotion to get the customer's personal code.
3. Present the returned code prominently to the customer.

### Product Search
Any time a customer asks about products, call search_products — even if you have prior results \
in context, always search for the specific item they named."""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _try_parse_json(value: Any) -> Any:
    """Return parsed JSON if value is a JSON string, otherwise return value as-is."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _messages_for_storage(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a copy of messages with JSON strings expanded into objects for readable storage."""
    result = []
    for msg in messages:
        m = dict(msg)
        if m.get("role") == "tool":
            m["content"] = _try_parse_json(m.get("content"))
        if m.get("tool_calls"):
            m["tool_calls"] = [
                {
                    **tc,
                    "function": {
                        **tc["function"],
                        "arguments": _try_parse_json(tc["function"].get("arguments")),
                    },
                }
                for tc in m["tool_calls"]
            ]
        result.append(m)
    return result


# ── Session ───────────────────────────────────────────────────────────────────

class Session:
    def __init__(self, db: sqlite3.Connection, registry: Registry):
        self.db = db
        self.registry = registry
        self.id = str(uuid.uuid4())
        self.messages:   list[dict[str, Any]] = []
        self.trajectory: list[dict[str, Any]] = []
        self._customer_id:      str | None = None
        self._customer_profile: str        = ""
        self._persist_errors:   list[str]  = []
        # Eagerly fetch promotions so they are always present in the system prompt,
        # removing reliance on the LLM deciding to call get_active_promotions itself.
        self._active_promotions: list[dict[str, Any]] = self.registry.execute("get_active_promotions")
        self._claimed_code: str | None = None
        db.execute("INSERT INTO sessions (id) VALUES (?)", (self.id,))
        db.commit()

    # ── Identity ──────────────────────────────────────────────────────────────

    def identify(self, email: str) -> None:
        if self._customer_id is not None:
            return
        row = self.db.execute(
            "SELECT id, profile FROM customers WHERE email = ?", (email,)
        ).fetchone()
        if row:
            self._customer_id = row["id"]
            self._customer_profile = row["profile"] or ""
            self.db.execute(
                "UPDATE sessions SET customer_id = ? WHERE id = ?",
                (self._customer_id, self.id),
            )
            self.db.commit()

    def system_prompt(self) -> str:
        if self._active_promotions:
            promo_lines = "\n".join(
                f"- {p['title']} (code: {p['code']}, {p['discount_pct']}% off)"
                for p in self._active_promotions
            )
            promo_section = f"## Current Active Promotions\n{promo_lines}"
        else:
            promo_section = "## Current Active Promotions\n(none currently active)"

        parts = [_PERSONA, _PRINCIPLES, promo_section, _PLAYBOOKS]
        if self._claimed_code:
            parts.append(f"## Claimed Promo Code This Session\nThe customer's personal code is: **{self._claimed_code}**. Always show this code when relevant.")
        if self._customer_profile:
            parts.append("## Returning Customer Profile\n" + self._customer_profile)
        return "You are Sierra, the Sierra Outfitters outdoor adventure assistant.\n\n" + "\n\n".join(parts)

    # ── Turn loop ─────────────────────────────────────────────────────────────

    def _build_messages(self) -> list[dict[str, Any]]:
        return [{"role": "system", "content": self.system_prompt()}] + self.messages

    def drive_turn(
        self,
        trajectory: list[dict[str, Any]] | None = None,
        debug: bool = False,
        max_tool_rounds: int = 10,
    ) -> str:
        """Run the inner tool-use loop for one user turn. Returns the final reply text."""
        rounds = 0
        while rounds < max_tool_rounds:
            built = self._build_messages()
            if debug and trajectory is not None:
                trajectory.append({
                    "type": "llm_call",
                    "round": rounds + 1,
                    "messages": _messages_for_storage(built),
                })
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=1024,
                tools=self.registry.openai_tools(),
                messages=built,
            )
            choice = response.choices[0]
            msg    = choice.message
            rounds += 1

            if choice.finish_reason == "stop":
                self.messages.append({"role": "assistant", "content": msg.content})
                if trajectory is not None:
                    trajectory.append({"type": "assistant", "content": msg.content or ""})
                return msg.content or ""

            if choice.finish_reason == "tool_calls":
                self.messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
                tool_results = self.execute_tools(msg.tool_calls)

                if trajectory is not None:
                    for tc, result_msg in zip(msg.tool_calls, tool_results):
                        try:
                            args = json.loads(tc.function.arguments)
                        except Exception:
                            args = {}
                        try:
                            result = json.loads(result_msg["content"])
                        except Exception:
                            result = result_msg["content"]
                        trajectory.append({
                            "type": "tool_call",
                            "name": tc.function.name,
                            "args": args,
                            "result": result,
                        })

                self.messages.extend(tool_results)
        return ""

    def execute_tools(self, tool_calls: Any) -> list[dict[str, Any]]:
        results = []
        for tc in tool_calls:
            name   = tc.function.name
            args   = json.loads(tc.function.arguments)
            result = self.registry.execute(name, **args)

            # Identify after the tool runs so register_customer is committed first.
            if self._customer_id is None:
                email = args.get("customer_email")
                if email:
                    self.identify(email)

            if name == "claim_promotion" and isinstance(result, dict) and "code" in result:
                self._claimed_code = result["code"]

            results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })
        return results

    # ── Persistence ───────────────────────────────────────────────────────────

    def _generate_summary(self, debug: bool) -> str:
        """Call the LLM to summarise the session; returns empty string on failure."""
        summary_messages = [
            *self.messages,
            {
                "role": "user",
                "content": (
                    "Extract only facts we can naturally reference in a future conversation with this customer.\n"
                    "One short bullet per fact, no prose.\n"
                    "Only include if critical: why they bought (reason, occasion, who it's for), budget, upcoming trips or events.\n"
                    "Omit everything else — products, name, email, browsing history."
                ),
            },
        ]
        if debug:
            self.trajectory.append({
                "type": "llm_call",
                "round": "session-summary",
                "messages": _messages_for_storage(summary_messages),
            })
        try:
            resp    = client.chat.completions.create(model=MODEL, max_tokens=512, messages=summary_messages)
            summary = resp.choices[0].message.content or ""
        except Exception as e:
            self._persist_errors.append(f"summary: {e}")
            return ""
        if debug and summary:
            self.trajectory.append({"type": "note", "content": f"Session summary: {summary}"})
        return summary

    def _merge_profile(self, summary: str, debug: bool) -> None:
        """Merge new session facts into the customer profile via LLM and write to DB."""
        now = datetime.now(timezone.utc).isoformat()
        profile_messages = [
            {
                "role": "user",
                "content": (
                    f"Existing profile:\n{self._customer_profile or '(none)'}\n\n"
                    f"New facts from this session:\n{summary}\n\n"
                    "Merge into a single bullet list of facts we can reference in future conversations.\n"
                    "One short bullet per fact, no prose.\n"
                    "Only keep if critical: why they bought, who they bought for, budget, upcoming trips or events.\n"
                    "Omit: products, name, email. Update changed facts; remove duplicates."
                ),
            },
        ]
        if debug:
            self.trajectory.append({
                "type": "llm_call",
                "round": "profile-merge",
                "messages": profile_messages,
            })
        try:
            resp        = client.chat.completions.create(model=MODEL, max_tokens=512, messages=profile_messages)
            new_profile = resp.choices[0].message.content or ""
            if debug:
                self.trajectory.append({"type": "note", "content": f"Updated profile: {new_profile}"})
            self.db.execute(
                "UPDATE customers SET profile = ?, profile_updated_at = ? WHERE id = ?",
                (new_profile, now, self._customer_id),
            )
            self.db.commit()
        except Exception as e:
            self._persist_errors.append(f"profile_update: {e}")

    def _write_trajectory(self) -> None:
        """Write raw JSON and rendered markdown trajectory files."""
        (TRAJECTORIES_RAW / f"{self.id}.json").write_text(json.dumps(self.trajectory, indent=2))
        (TRAJECTORIES_MD  / f"{self.id}.md").write_text("\n".join(render_trajectory(self.trajectory)))

    def persist(self, debug: bool = False) -> None:
        now = datetime.now(timezone.utc).isoformat()

        if not self.messages:
            self.db.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (now, self.id))
            self.db.commit()
            return

        self._persist_errors = []
        summary = self._generate_summary(debug)

        if self._customer_id and summary:
            self._merge_profile(summary, debug)

        self.db.execute(
            "UPDATE sessions SET summary = ?, ended_at = ? WHERE id = ?",
            (summary, now, self.id),
        )
        try:
            self._write_trajectory()
        except OSError as e:
            self._persist_errors.append(f"trajectory: {e}")
        self.db.commit()

        if self._persist_errors:
            self.db.execute(
                "UPDATE sessions SET persist_error = ? WHERE id = ?",
                ("\n".join(self._persist_errors), self.id),
            )
            self.db.commit()


# ── debug_email helpers ───────────────────────────────────────────────────────

def _render_customer_panel(customer: sqlite3.Row) -> Panel:
    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column(style="bold cyan", no_wrap=True)
    info.add_column()
    info.add_row("ID",              customer["id"])
    info.add_row("Name",            customer["name"])
    info.add_row("Email",           customer["email"])
    info.add_row("Created",         customer["created_at"] or "—")
    info.add_row("Profile updated", customer["profile_updated_at"] or "—")
    return Panel(info, title="[bold]Customer[/bold]", border_style="cyan")


def _render_orders_panels(order_rows: list[sqlite3.Row]) -> list[Panel]:
    """Group order rows by order ID and return one Panel per order."""
    orders: dict[str, dict[str, Any]] = {}
    for r in order_rows:
        if r["id"] not in orders:
            orders[r["id"]] = {
                "id": r["id"], "status": r["status"],
                "tracking": r["tracking_number"], "promo_code": r["promo_code"],
                "items": [], "total": 0.0,
            }
        orders[r["id"]]["items"].append(f"{r['product_name']}  (${r['price']:.2f})")
        orders[r["id"]]["total"] += r["price"]

    panels = []
    for order in orders.values():
        t = Table(show_header=False, box=None, padding=(0, 1))
        t.add_column(style="bold", no_wrap=True)
        t.add_column()
        t.add_row("Status",     order["status"])
        t.add_row("Tracking",   order["tracking"] or "—")
        t.add_row("Promo Code", order["promo_code"] or "—")
        t.add_row("Items",      "\n".join(order["items"]))
        t.add_row("Total",      f"${order['total']:.2f}")
        panels.append(Panel(t, title=f"[bold]Order {order['id']}[/bold]", border_style="magenta"))
    return panels


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--debug-trajectory", "debug_trajectory", is_flag=True, default=False,
              help="Include full LLM prompts in trajectory files (JSON + markdown).")
@click.option("--pt-hour", "pt_hour", type=click.IntRange(0, 23), default=None,
              help="Override the current Pacific Time hour (0-23) for testing time-gated promotions.")
@click.pass_context
def cli(ctx, debug_trajectory: bool, pt_hour: int | None):
    """Sierra Outfitters — outdoor adventure gear assistant."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat, debug_trajectory=debug_trajectory, pt_hour=pt_hour)


@cli.command()
@click.option("--debug-trajectory", "debug_trajectory", is_flag=True, default=False,
              help="Include full LLM prompts in trajectory files (JSON + markdown).")
@click.option("--pt-hour", "pt_hour", type=click.IntRange(0, 23), default=None,
              help="Override the current Pacific Time hour (0-23) for testing time-gated promotions.")
def chat(debug_trajectory: bool, pt_hour: int | None) -> None:
    """Start an interactive chat session with Sierra Outfitters."""
    if pt_hour is not None:
        set_pt_hour_override(pt_hour)

    db       = get_connection()
    registry = build_registry(db)
    session  = Session(db, registry)

    click.echo("Sierra Outfitters  🏔️   (type 'exit' or 'quit' to leave)\n")
    if pt_hour is not None:
        click.echo(f"[pt-hour override: {pt_hour:02d}:xx PT]\n")
    if debug_trajectory:
        click.echo("[debug-trajectory on — LLM prompts will be written to trajectory files]\n")

    try:
        while True:
            try:
                user_input = input("You > ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break

            session.messages.append({"role": "user", "content": user_input})
            session.trajectory.append({"type": "user", "content": user_input})
            reply = session.drive_turn(trajectory=session.trajectory, debug=debug_trajectory)
            console.print(Panel(Markdown(reply), title="Sierra Outfitters 🏔️", border_style="green"))
    finally:
        click.echo("\nWrapping up your expedition... 🏕️")
        session.persist(debug=debug_trajectory)
        db.close()


@cli.command()
def seed() -> None:
    """Clear and re-seed sierra.db from data/: products, customer orders, and promotions."""
    import shutil
    from db import init_schema
    from loader import load_customers_and_orders, load_products, load_promotions

    if DB_PATH.exists():
        DB_PATH.unlink()
    db = get_connection()
    init_schema(db)
    load_products(db)
    load_customers_and_orders(db)
    load_promotions(db)
    db.close()

    if TRAJECTORIES_DIR.exists():
        shutil.rmtree(TRAJECTORIES_DIR)
    TRAJECTORIES_RAW.mkdir(parents=True)
    TRAJECTORIES_MD.mkdir(parents=True)


@cli.command(name="clear")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
def clear_db(yes: bool) -> None:
    """Delete all data from sierra.db (schema is preserved)."""
    if not DB_PATH.exists():
        click.echo("sierra.db does not exist — nothing to clear.")
        return
    if not yes:
        click.confirm(
            "This will delete all customers, orders, sessions, and products. Continue?",
            abort=True,
        )
    db = get_connection()
    for table in ("order_items", "orders", "sessions", "promotion_claims",
                  "promotion_tags", "promotions", "product_tags", "products", "customers"):
        db.execute(f"DELETE FROM {table}")
    db.commit()
    db.close()
    click.echo("All data cleared. Schema intact.")


@cli.command(name="debug_email")
@click.argument("email")
def debug_email(email: str) -> None:
    """[DEBUG] Show stored profile and session history for a customer email."""
    db       = get_connection()
    customer = db.execute(
        "SELECT id, name, email, profile, profile_updated_at, created_at "
        "FROM customers WHERE email = ?",
        (email,),
    ).fetchone()
    if not customer:
        console.print(f"[red]No customer found with email:[/red] {email}")
        db.close()
        return

    console.print(_render_customer_panel(customer))
    console.print(Panel(
        customer["profile"] or "[dim]No profile stored yet.[/dim]",
        title="[bold]Stored Profile[/bold]",
        border_style="yellow",
    ))

    order_rows = db.execute(
        "SELECT o.id, o.status, o.tracking_number, o.promo_code, p.name AS product_name, p.price "
        "FROM orders o JOIN order_items oi ON oi.order_id = o.id "
        "JOIN products p ON p.sku = oi.sku WHERE o.customer_id = ? ORDER BY o.id ASC",
        (customer["id"],),
    ).fetchall()
    order_panels = _render_orders_panels(order_rows)
    if not order_panels:
        console.print(Panel("[dim]No orders found.[/dim]", title="[bold]Orders[/bold]", border_style="magenta"))
    else:
        console.print(f"\n[bold]Orders[/bold] ({len(order_panels)} total)\n")
        for panel in order_panels:
            console.print(panel)

    sessions = db.execute(
        "SELECT id, started_at, ended_at, summary "
        "FROM sessions WHERE customer_id = ? ORDER BY started_at DESC",
        (customer["id"],),
    ).fetchall()
    if not sessions:
        console.print(Panel("[dim]No sessions recorded yet.[/dim]", title="[bold]Sessions[/bold]", border_style="green"))
    else:
        console.print(f"\n[bold]Sessions[/bold] ({len(sessions)} total)\n")
        for i, s in enumerate(sessions, 1):
            t = Table(show_header=False, box=None, padding=(0, 1))
            t.add_column(style="bold", no_wrap=True)
            t.add_column()
            t.add_row("Session ID", s["id"])
            t.add_row("Started",    s["started_at"] or "—")
            t.add_row("Ended",      s["ended_at"] or "still open")
            t.add_row("Summary",    s["summary"] or "[dim]No summary yet.[/dim]")
            console.print(Panel(t, title=f"[bold]Session {i}[/bold]", border_style="green"))
    db.close()


if __name__ == "__main__":
    cli()
