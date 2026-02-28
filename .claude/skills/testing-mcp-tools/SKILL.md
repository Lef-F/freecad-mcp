---
name: testing-mcp-tools
description: Systematically tests MCP tools against a running FreeCAD instance, documenting findings and updating known-issues.md.
---

# Testing MCP Tools

## When to Use

- After modifying serialization logic, RPC methods, or MCP tool definitions
- After upgrading FreeCAD to a new version
- When investigating a reported bug in tool behavior
- Before a release to verify all tools work end-to-end

## Prerequisites

- FreeCAD running with the MCP addon's RPC server started
- MCP server running (`uv run freecad-mcp`)
- At least one document open in FreeCAD with some objects

## Steps

### 1. Check FreeCAD version
```python
# via execute_code
import FreeCAD
print(f"FreeCAD version: {FreeCAD.Version()}")
```
Record the version for the compatibility table in `known-issues.md`.

### 2. Test read-only tools first

These are safest and reveal serialization issues:

1. **`list_documents`** — Should return a list of open document names
2. **`get_objects(doc_name)`** — Should return `{"success": true, "objects": [...]}`. Watch for:
   - Raw XML-RPC faults (serialization crash)
   - `<error: ...>` strings in property values (per-property serialization failure)
   - Missing `success` key (old response format)
3. **`get_object(doc_name, obj_name)`** — Same checks as `get_objects`, plus:
   - `NoneType` errors for non-existent objects
   - ViewObject serialization failures (e.g., `ShapeColor` with missing `App.Color`)

### 3. Test mutation tools

1. **`create_document("TestDoc")`** — Should succeed and return document name
2. **`create_object("TestDoc", "Part::Box", "TestBox")`** — Should create and return screenshot
3. **`edit_object("TestDoc", "TestBox", {"Length": 20})`** — Should modify and return screenshot
4. **`delete_object("TestDoc", "TestBox")`** — Should delete and return screenshot

### 4. Test screenshot behavior

1. **`get_view("Isometric")`** — Default dimensions (check size)
2. **`get_view("Isometric", width=300, height=300)`** — Explicit dimensions (should be smaller)
3. **`get_view("Front")`** — Different view angle

### 5. Test optional addon tools

1. **`get_parts_list()`** — Returns parts or empty message if addon missing
2. **`insert_part_from_library(path)`** — Only if parts library is installed

### 6. Document findings

Update `.claude/context/known-issues.md` with:
- Any new issues discovered
- Version compatibility changes
- Fixes verified as working

## Verification

- All read-only tools return structured `{"success": ...}` responses (no raw faults)
- All mutation tools return screenshots (unless `--only-text-feedback` is active)
- No `AttributeError` or `TypeError` crashes from serialization
- Property values don't contain `<error: ...>` strings (except for genuinely unserializable edge cases)
- `known-issues.md` is up to date with test results
