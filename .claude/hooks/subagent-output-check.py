#!/usr/bin/env python3
"""SubagentStop hook for the spec-driven-design skill collection.

Reads the subagent's initial prompt for a magic comment of the form:

    # expected_output: <absolute-path>

If found, checks the file exists and is non-empty. Prints a warning to stderr
if not. Always exits 0 (advisory only in v1). Logs activity to
~/.claude/spec-driven-design.log so we can iterate the contract.

Registered as a SubagentStop hook in .claude/settings.json.
"""

from __future__ import annotations

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


def extract_first_user_text(transcript_path: str) -> str | None:
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
        log(f"transcript not found: {transcript_path}")
        return None
    except Exception as e:
        log(f"error reading transcript {transcript_path}: {e}")
        return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        log("stdin not JSON; skipping")
        return 0

    transcript_path = (
        payload.get("transcript_path")
        or payload.get("transcriptPath")
        or payload.get("subagent", {}).get("transcript_path")
    )
    if not transcript_path:
        log(f"no transcript_path in payload keys: {list(payload.keys())}")
        return 0

    prompt = extract_first_user_text(transcript_path)
    if not prompt:
        log(f"no user prompt in {transcript_path}")
        return 0

    match = MAGIC_RE.search(prompt)
    if not match:
        # No magic comment - subagent did not opt in to the contract.
        log(f"no expected_output comment in {os.path.basename(transcript_path)}")
        return 0

    expected = match.group(1).strip()
    expected_path = Path(expected).expanduser()

    if not expected_path.exists():
        msg = (
            f"WARN spec-driven-design: subagent declared expected_output "
            f"'{expected_path}' but the file does not exist. "
            f"(transcript: {os.path.basename(transcript_path)})"
        )
        print(msg, file=sys.stderr)
        log(msg)
        return 0  # advisory only in v1

    try:
        size = expected_path.stat().st_size
    except Exception as e:
        log(f"stat error for {expected_path}: {e}")
        return 0

    if size == 0:
        msg = (
            f"WARN spec-driven-design: expected_output '{expected_path}' exists "
            f"but is empty. (transcript: {os.path.basename(transcript_path)})"
        )
        print(msg, file=sys.stderr)
        log(msg)
        return 0

    log(f"OK {expected_path} ({size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
