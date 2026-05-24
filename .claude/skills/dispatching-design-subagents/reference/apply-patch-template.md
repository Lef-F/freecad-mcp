# Archetype: Apply-Patch

Surgical code edit with exact before/after blocks. The subagent's job is `apply_diff`, not `interpret_intent`.

## When to use
- The parent has identified the exact lines to change and the exact replacement text.
- Single-file or few-file edits with no ambiguity about what to change.
- Side-effect code emerging from a design session (new MCP tool param, addon fix).

## When NOT to use
- The parent isn't sure what the change should look like (run an Explore first).
- The change spans many files with structural redesign (planning gap - split the work).
- The change requires running tests to validate (use a different orchestration; tests should be verified by the parent or a Review reviewer afterwards).

## Required tool surface
- `Read`
- `Edit`

No Bash, no WebFetch, no Write. The subagent does not run linters or tests; that's a separate verification step run by the parent or a reviewer.

## Prompt template

```
PURPOSE: <one-line goal, e.g., "Add max-dimension cap to _save_active_screenshot">

BACKGROUND: <2-3 sentences explaining WHY this change is needed, with reference to the spec or research that surfaced it>

EXACT CHANGE REQUIRED

File: /Users/lef/Repos/lef/freecad-mcp/<absolute-path>

Find these lines (around line <N>):
```python
<exact before block, copy-pasted from the actual file>
```

Replace with:
```python
<exact after block>
```

That's the only change needed in this file.

CONSTRAINTS:
- Do NOT run ruff, mypy, or any tests (verification happens separately)
- Do NOT touch any other lines in this file
- Do NOT touch any other files
- Addon code (`addon/`) cannot be linted with external tools anyway

VERIFICATION (do this after the edit):
- Read back lines <N-4> through <N+8> of the file and quote them in your final output.
- Confirm the before block no longer appears and the after block is present.

RETURN: Write a 10-line summary to `<journal-path>/build/<task-id>.md`:
- Path edited
- Exact quoted lines after the edit
- Confirmation that no other lines changed
Your chat reply: file path + 2-line headline.

# expected_output: <journal-path>/build/<task-id>.md
```

## Pre-flight checks (parent runs before dispatching)
1. Confirm the target file exists.
2. Confirm the "before block" text appears in the file at the expected location (`Grep` for the first line).
3. If editing addon code, confirm the "Do NOT run ruff/mypy" constraint is in the prompt.
4. If editing `src/freecad_mcp/server.py`, expect a follow-up Review of the change before commit.

## Anti-patterns to avoid
- Open-ended "improve this function" prompts (use Explore + a new Apply-Patch with concrete changes).
- Letting the subagent decide which lines to change ("Find the line that does X and replace it with Y").
- Multiple unrelated edits in one Apply-Patch - split them.

## Evidence this works
- `agent-a607a851df9026ba5`: 11-message transcript for a 3-line change, zero drift, exact verification.
- `agent-aac44a95335cc139d`: 7 numbered changes to `server.py`, all applied cleanly because each had its own before/after block.
