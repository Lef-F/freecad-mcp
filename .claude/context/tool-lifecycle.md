# Adding or Modifying MCP Tools

Step-by-step guide for the full lifecycle of an MCP tool.

## 1. Define the RPC method (addon side)

In `addon/FreeCADMCP/rpc_server/rpc_server.py`, add a method to `FreeCADRPC`.

The public method queues a lambda and wraps the raw result into a response dict:

```python
def my_new_method(self, doc_name, param):
    rpc_request_queue.put(lambda: self._my_new_method_gui(doc_name, param))
    res = rpc_response_queue.get()
    if res is True:
        return {"success": True, "result": "..."}
    else:
        return {"success": False, "error": res}
```

The `_gui` helper **returns** a value — it does NOT put into the queue directly.
`process_gui_tasks()` handles putting the return value into `rpc_response_queue`:

```python
def _my_new_method_gui(self, doc_name, param):
    try:
        doc = FreeCAD.getDocument(doc_name)
        # ... do work on GUI thread ...
        doc.recompute()
        return True
    except Exception as e:
        return str(e)
```

For read-only operations, skip the queue and access FreeCAD directly.

## 2. Add connection method (MCP server side)

In `src/freecad_mcp/server.py`, add to `FreeCADConnection`:

```python
def my_new_method(self, doc_name: str, param: str) -> dict:
    return self.server.my_new_method(doc_name, param)
```

Note: some connection methods contain pre-processing logic (e.g., `get_active_screenshot` checks view compatibility before calling the RPC method). Keep connection methods thin when possible.

## 3. Define the MCP tool

In `src/freecad_mcp/server.py`, add the tool function:

```python
@mcp.tool()
def my_new_tool(ctx: Context, doc_name: str, param: str) -> list[TextContent | ImageContent]:
    """Clear docstring explaining what this tool does and when to use it."""
    conn = get_freecad_connection()
    result = conn.my_new_method(doc_name, param)

    if not result["success"]:
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    response = [TextContent(type="text", text=f"Done: {result['result']}")]

    # Include screenshot for mutation tools
    screenshot = conn.get_active_screenshot()
    add_screenshot_if_available(response, screenshot)

    return response
```

Key points:
- First parameter is always `ctx: Context`
- Use `get_freecad_connection()` (not `get_connection`)
- Use `add_screenshot_if_available()` helper for screenshot handling (it also adds an informative message when screenshots are unavailable)

## 4. Update serialization (if needed)

File: `addon/FreeCADMCP/rpc_server/serialize.py`

If the tool returns new FreeCAD object types, extend `serialize_value()` to handle them.

## 5. Verify

- `uv run ruff check src/` — no lint errors
- `uv run ruff format --check src/` — formatting correct
- `uv run mypy src/` — type checks pass
- Manual test: start FreeCAD → Start RPC Server → run `uv run freecad-mcp` → invoke tool via Claude Desktop or MCP inspector

## Conventions

- Mutation tools return a screenshot; read-only tools may include one for context
- Tool docstrings should include usage examples (see `create_object` for reference)
- RPC responses always use `{"success": bool, ...}` shape
- Error messages should be actionable (tell the user what went wrong and how to fix it)
- Parameters use `doc_name` for document, `obj_name` for object (consistent naming)
