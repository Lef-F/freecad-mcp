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

### 1. Implement the RPC handler
File: `addon/FreeCADMCP/rpc_server/rpc_server.py`

Add a public method to `FreeCADRPC` class:
- For mutations: put a lambda into `rpc_request_queue`, block on `rpc_response_queue.get()`
- For reads: access FreeCAD objects directly
- Return `{"success": True/False, ...}` dict
- If the operation produces data, include it in the response dict

If the operation needs GUI thread work, add a private `_method_gui()` helper that:
- Executes on the main thread via the task queue
- Wraps everything in try/except
- Puts the result dict into `rpc_response_queue`
- Calls `doc.recompute()` after mutations

### 2. Add the connection method
File: `src/freecad_mcp/server.py`

Add a method to `FreeCADConnection` that calls `self.server.<rpc_method>(...)`.

### 3. Define the MCP tool
File: `src/freecad_mcp/server.py`

Add a `@mcp.tool()` function:
- Write a clear docstring (this is what the LLM sees to decide when to use the tool)
- Call `get_connection()` to get the singleton
- Invoke the connection method
- Handle errors (check `result["success"]`)
- Return `list[TextContent | ImageContent]`
- Append screenshot if the tool mutates state and `_only_text_feedback` is False

### 4. Update serialization (if needed)
File: `addon/FreeCADMCP/rpc_server/serialize.py`

If the tool returns new FreeCAD object types, extend `serialize_value()` to handle them.

## Verification

1. `uv run ruff check src/` — no lint errors
2. `uv run ruff format --check src/` — formatting correct
3. `uv run mypy src/` — type checks pass
4. Manual test: Start FreeCAD → Start RPC Server → run MCP server → invoke tool via Claude Desktop or MCP inspector
