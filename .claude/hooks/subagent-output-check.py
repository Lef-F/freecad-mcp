#!/usr/bin/env python3
"""SubagentStop hook for the spec-driven-design skill collection.

When a dispatched subagent stops, this hook locates that subagent's own
transcript, reads its initial prompt for a magic comment of the form:

    # expected_output: <absolute-path>

and, if present, checks the declared file exists and is non-empty. Prints a
warning to stderr if not. Always exits 0 (advisory only in v1). Logs activity
to ~/.claude/spec-driven-design.log so the contract can be iterated.

## Why this is not as simple as reading `transcript_path`

On a SubagentStop event the `transcript_path` field carries the PARENT
session transcript (the UUID-named .jsonl), NOT the subagent's. The first
v1 of this hook trusted `transcript_path` and therefore always parsed the
human's opening message (no magic comment) -- it never verified a single
subagent. The fix below resolves the subagent's OWN transcript:

  1. Probe the payload for an explicit subagent-transcript field (so if a
     future Claude Code release exposes one, we use it directly).
  2. Otherwise derive it: the subagent transcripts for a session live in a
     sibling directory `<session-uuid>/subagents/agent-*.jsonl`. The
     just-stopped subagent is the most-recently-modified such file.

Registered as a SubagentStop hook in .claude/settings.json.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

LOG_PATH = Path.home() / ".claude" / "spec-driven-design.log"
MAGIC_RE = re.compile(r"^#\s*expected_output:\s*(\S+)", re.MULTILINE)


def log(line: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as f:
            f.write(f"{datetime.now().isoformat()}  {line}\n")
    except Exception:
        pass


def first_user_text(transcript_path: str) -> str | None:
    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") != "user":
                    continue
                msg = ev.get("message", {})
                content = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            return c.get("text", "")
        return None
    except FileNotFoundError:
        return None
    except Exception as e:
        log(f"error reading transcript {transcript_path}: {e}")
        return None


def explicit_subagent_path(payload: dict) -> str | None:
    """Probe known/plausible payload fields for the subagent's own transcript."""
    for key in (
        "subagent_transcript_path",
        "agent_transcript_path",
        "sidechain_transcript_path",
        "subagentTranscriptPath",
        "agentTranscriptPath",
    ):
        val = payload.get(key)
        if isinstance(val, str) and val.endswith(".jsonl"):
            return val
    for parent_key in ("subagent", "agent", "sidechain"):
        sub = payload.get(parent_key)
        if isinstance(sub, dict):
            val = sub.get("transcript_path") or sub.get("transcriptPath")
            if isinstance(val, str) and val.endswith(".jsonl"):
                return val
    return None


def derived_subagent_paths(transcript_path: str) -> list[str]:
    """Derive candidate subagent transcripts from the parent transcript path.

    `<dir>/<uuid>.jsonl` -> subagents live in `<dir>/<uuid>/subagents/agent-*.jsonl`.
    Returns agent transcripts sorted newest-first, excluding compaction stubs.
    Returns the few most recent so a parallel-dispatch batch is all covered.
    """
    if not transcript_path.endswith(".jsonl"):
        return []
    session_dir = transcript_path[: -len(".jsonl")]
    subagents_dir = os.path.join(session_dir, "subagents")
    if not os.path.isdir(subagents_dir):
        return []
    agents = [
        p
        for p in glob.glob(os.path.join(subagents_dir, "agent-*.jsonl"))
        if "acompact" not in os.path.basename(p)
    ]
    agents.sort(key=os.path.getmtime, reverse=True)
    # Cover a small recent window so a parallel fan-out is all checked, not just
    # the single newest file.
    return agents[:6]


def check_one(transcript_path: str) -> str:
    """Return a one-word status for a single subagent transcript:
    'ok' | 'missing' | 'empty' | 'no-comment' | 'no-prompt'.
    Side effect: warns to stderr + logs on missing/empty.
    """
    prompt = first_user_text(transcript_path)
    if not prompt:
        return "no-prompt"
    match = MAGIC_RE.search(prompt)
    if not match:
        return "no-comment"
    expected_path = Path(match.group(1).strip()).expanduser()
    name = os.path.basename(transcript_path)
    if not expected_path.exists():
        msg = (
            f"WARN spec-driven-design: subagent declared expected_output "
            f"'{expected_path}' but the file does not exist. (subagent: {name})"
        )
        print(msg, file=sys.stderr)
        log(msg)
        return "missing"
    try:
        size = expected_path.stat().st_size
    except Exception as e:
        log(f"stat error for {expected_path}: {e}")
        return "no-prompt"
    if size == 0:
        msg = (
            f"WARN spec-driven-design: expected_output '{expected_path}' exists "
            f"but is empty. (subagent: {name})"
        )
        print(msg, file=sys.stderr)
        log(msg)
        return "empty"
    log(f"OK {expected_path} ({size} bytes) (subagent: {name})")
    return "ok"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        log("stdin not JSON; skipping")
        return 0

    # Always record the payload shape so the real subagent-transcript field can
    # be discovered empirically across Claude Code releases.
    log(f"payload keys: {sorted(payload.keys())}")

    # 1. Explicit field if the payload provides one.
    explicit = explicit_subagent_path(payload)
    if explicit:
        check_one(explicit)
        return 0

    # 2. Derive from the parent transcript's sibling subagents/ directory.
    parent = payload.get("transcript_path") or payload.get("transcriptPath")
    if not parent:
        log(f"no transcript_path; cannot resolve subagent. keys={sorted(payload.keys())}")
        return 0

    candidates = derived_subagent_paths(parent)
    if not candidates:
        log(f"no subagent transcripts derivable from {parent}")
        return 0

    # Check the most recent candidate (the just-stopped subagent). The wider
    # window is logged but only the newest is authoritative for this event;
    # checking the newest avoids spurious re-warns on already-handled siblings.
    status = check_one(candidates[0])
    log(f"checked newest subagent {os.path.basename(candidates[0])}: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
