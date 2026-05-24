# Archetype: RPC-Exec

Single `mcp__freecad__execute_code` call wrapped in a subagent for token isolation.

## When to use
- Building / modifying FreeCAD geometry that needs >50 lines of Python.
- Querying current document state with computed values across many objects.
- Anything that produces printed output the parent needs in summary, not verbatim.

## When NOT to use
- The parent could just call `mcp__freecad__execute_code` directly with <20 lines of code (no token-isolation benefit).
- The work needs multi-step reasoning between FreeCAD calls (use Explore archetype instead).

## Required tool surface
- `mcp__freecad__execute_code`
- `ToolSearch` (to load the MCP tool schema if not already loaded)

## Prompt template

```
PURPOSE: <one-line goal, e.g., "Create the wood-fence-Z-corrected geometry">

TASK: Use the freecad MCP tool execute_code on doc_name="<doc>" with capture_screenshot=<true|false> to run the following Python. Do NOT split it - run it all in ONE execute_code call.

```python
# All imports at top
import FreeCAD as App
import Part

doc = App.getDocument("<doc>")

# All parameters declared up front
WIDTH = 100
HEIGHT = 200

# Build / query work here

# Last line(s) print a structured summary
print(f"created: {obj.Name} valid={obj.Shape.isValid()}")
print(f"placement: {obj.Placement.Base}")
```

CONSTRAINTS:
- ASCII only (no special chars in strings or comments)
- Every new object must have MCP_Role set: obj.MCP_Role = "<Final|Intermediate|Alternative|Deprecated>"
- Do NOT call doc.save() (the auto-save hook handles it)

RETURN: After execution, write a 10-line summary to `<journal-path>/build/<task-id>.md` containing:
- The exact printed output
- Whether all created objects report .Shape.isValid() == True
- The MCP_Role values set
Your chat reply: just the file path and a 3-line headline.

# expected_output: <journal-path>/build/<task-id>.md
```

## Pre-flight checks (parent runs before dispatching)
1. Confirm `doc_name` matches a currently-open document (`mcp__freecad__list_documents`).
2. Confirm the journal directory exists (`mkdir -p` the build subdir).
3. Confirm `capture_screenshot` value matches the visualisation milestone in the plan.

## Anti-patterns to avoid
- Multiple `execute_code` calls in one subagent - split it into sequential RPC-Exec subagents or do it in-thread.
- Code that mutates state but doesn't print verification output.
- Long inline reasoning between code lines - the subagent should be mostly code.

## Evidence this works
- `agent-a3fa2bbd6c307c7a9` (parking_lot_v6): 170-line single-call geometry construction, isolated 22.7 KB from parent context, returned a clean printed summary.
