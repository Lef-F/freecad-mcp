---
name: adding-mcp-tool
description: Guides through the full implementation of a new MCP tool, from RPC handler to MCP definition, ensuring both components are updated consistently.
---

# Adding an MCP Tool

## When to Use
When implementing a new tool that LLM clients can invoke to interact with FreeCAD.

## Prerequisites
- Understand what FreeCAD API calls the tool needs (read `.claude/context/freecad-patterns.md`)
- Know whether the operation needs GUI thread access (mutations do, reads usually don't)

## Steps

Follow `.claude/context/tool-lifecycle.md` for code templates. Summary:

### 1. Implement the RPC handler
File: `addon/FreeCADMCP/rpc_server/rpc_server.py`

Add a public method to `FreeCADRPC` class that queues work and wraps the result.
The `_gui` helper **returns** its result — `process_gui_tasks()` handles the queue.
The public method wraps the raw return value into `{"success": bool, ...}` dict.

### 2. Add the connection method
File: `src/freecad_mcp/server.py`

Add a method to `FreeCADConnection` that calls `self.server.<rpc_method>(...)`.

### 3. Define the MCP tool
File: `src/freecad_mcp/server.py`

Add a `@mcp.tool()` function with `ctx: Context` as first parameter.
Use `get_freecad_connection()` and `add_screenshot_if_available()`.

### 4. Update serialization (if needed)
File: `addon/FreeCADMCP/rpc_server/serialize.py`

If the tool returns new FreeCAD object types, extend `serialize_value()` to handle them.

## Verification

1. `uv run ruff check src/` — no lint errors
2. `uv run ruff format --check src/` — formatting correct
3. `uv run mypy src/` — type checks pass
4. Manual test: Start FreeCAD → Start RPC Server → run MCP server → invoke tool via Claude Desktop or MCP inspector
