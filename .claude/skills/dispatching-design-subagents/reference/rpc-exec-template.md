# Archetype: RPC-Exec

A bounded live-model build/mutation task wrapped in a subagent for token isolation. The natural shape is: an optional read-only discovery call to confirm identifiers against live state, then the mutation call, then an in-call verification print.

## When to use
- Building / modifying live-model geometry (in a FreeCAD session: `mcp__freecad__execute_code`) that needs more than a trivial inline snippet.
- A mutation that should confirm its target identifiers against live state before changing them.
- Anything that produces output the parent wants as a structured build-log artifact, not verbatim in chat.

## When NOT to use
- The parent could run the query/mutation directly with a trivial inline snippet (no token-isolation benefit).
- The work is open-ended investigation with multi-step reasoning (use Explore).
- The work is purely checking/auditing existing state against a rubric (use Review).

## Required tool surface
- The live-model execution tool (FreeCAD session: `mcp__freecad__execute_code`)
- `ToolSearch` (to load the execution tool schema if not already loaded)
- `Read` (to read the inputs the task depends on, e.g. an Explore findings file)
- `Write` (the single expected_output build-log file only)
- `Bash` for `stat` / `wc`-style checks only (no installs, no source edits)

## Prompt template

```
PURPOSE: <one-line goal, e.g., "Create the corrected geometry for <feature>">

TASK: Use the live-model execution tool on the active document to perform this build.
Run it as a SMALL BOUNDED SEQUENCE, each call self-contained and printing a result:

  Call 1 (optional, READ-ONLY discovery): confirm the live-model identifiers this
  task depends on (property names, type ids, object/field names) actually match the
  running model BEFORE mutating. Skip only if a prior Explore already verified them.

  Call 2 (mutation): perform the change. All imports + parameters declared up top.

  Call 3 (in-call verification): print a structured before/after + validity check.

Example mutation call body:
```python
import FreeCAD as App
doc = App.getDocument("<doc>")
# parameters up front
# ... build / mutation work ...
# print structured verification
print(f"created: {obj.Name} valid={obj.Shape.isValid()} role={obj.MCP_Role}")
```

CONSTRAINTS:
- ASCII only (no special chars in strings or comments)
- Every new object must have its role tag set at creation: obj.MCP_Role = "<Final|Intermediate|Alternative|Deprecated>"
- Do NOT call doc.save() (the auto-save hook handles it)
- Keep the sequence BOUNDED (discovery -> mutation -> verify). If you find yourself
  doing open-ended multi-step reasoning across many calls, stop -- that work belongs
  in an Explore task, not here.

RETURN: Write a structured BUILD-LOG to `<journal-path>/build/<task-id>.md`:
- TL;DR (counts of what changed, recompute/validity result)
- Before/after of what changed (the table downstream phases actually consume)
- The exact printed verification output
- A `## Claims I am asserting` ledger (see reference/claims-ledger.md)
Your chat reply: file path + a short headline including the verification result.

# expected_output: <journal-path>/build/<task-id>.md
```

## Pre-flight checks (parent runs before dispatching)
1. Confirm the document/model the task targets is currently open/loaded.
2. Confirm the journal `build/` subdir exists.
3. Confirm `capture_screenshot` (if the tool takes it) matches the plan's visualisation milestone; default False for non-visual build steps.
4. Confirm every live-model identifier the mutation depends on was verified by a prior discovery/Explore step OR that this task's own discovery call (Call 1) will verify it before mutating. Never let the mutation be the first thing to touch an unverified identifier.

## Anti-patterns to avoid
- Unbounded exploratory calls / multi-step reasoning that belongs in Explore. RPC-Exec is discovery -> mutation -> verify, not an open investigation.
- Code that mutates state but prints no verification output.
- Mutating an identifier the task assumed but never confirmed against the live model.
- Returning only a tiny headline when the valuable artifact is the before/after build-log.

## Evidence this works
- A 170-line single-call geometry construction isolated ~23 KB from the parent context and returned a clean printed summary (token-isolation win).
- A discovery-then-mutation sequence (confirm identifiers live, then change them, then verify) caught and avoided acting on a wrong identifier that an upstream plan had assumed.
