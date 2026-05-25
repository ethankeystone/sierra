"""
Shared utilities for Sierra Outfitters integration evals.

Not pytest-specific — importable as a regular module from any eval file.

Trajectory format
-----------------
``trajectory`` is a ``list[dict]`` of structured turns:

    {"type": "user",      "content": str}
    {"type": "tool_call", "name": str, "args": dict, "result": any}
    {"type": "assistant", "content": str}

conftest.py handles both rendering (terminal) and serialising (JSONL).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent import Session
from db import get_connection
from tools import build_registry


class ToolCall:
    """Record of a single Registry.execute invocation captured by the tracer."""

    __slots__ = ("name", "kwargs", "result")

    def __init__(self, name: str, kwargs: dict, result):
        self.name = name
        self.kwargs = kwargs
        self.result = result

    def __repr__(self) -> str:
        return f"ToolCall({self.name!r}, {self.kwargs})"


def run_conversation(
    user_messages: list[str],
    trajectory: list[dict] | None = None,
    max_tool_rounds: int = 10,
) -> tuple[Session, str]:
    """
    Drive a Session through a scripted list of user messages against the real LLM.

    Each message in user_messages is sent in turn; the inner tool-use loop runs
    until the model reaches finish_reason=='stop' before the next message is sent.

    If ``trajectory`` is provided it is populated with structured turn dicts
    (see module docstring) so callers can render or serialise the conversation.

    Returns (session, final_assistant_reply_text).
    """
    db = get_connection()
    reg = build_registry(db)
    session = Session(db, reg)
    final_reply = ""

    for user_msg in user_messages:
        if trajectory is not None:
            trajectory.append({"type": "user", "content": user_msg})
        session.messages.append({"role": "user", "content": user_msg})
        final_reply = session.drive_turn(trajectory=trajectory, max_tool_rounds=max_tool_rounds)

    db.close()
    return session, final_reply
