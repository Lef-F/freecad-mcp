# Adding or Modifying MCP Tools

Step-by-step guide for the full lifecycle of an MCP tool.

## 1. Define the RPC method (addon side)

In `addon/FreeCADMCP/rpc_server/rpc_server.py`, add a method to `FreeCADRPC`:

```python
def my_new_method(self, doc_name, param):
    # For mutations: use the GUI task queue
    rpc_request_queue.put(lambda: self._my_new_method_gui(doc_name, param))
    return rpc_response_queue.get()

def _my_new_method_gui(self, doc_name, param):
    try:
        doc = FreeCAD.getDocument(doc_name)
        # ... do work on GUI thread ...
        doc.recompute()
        rpc_response_queue.put({"success": True, "result": "..."})
    except Exception as e:
        rpc_response_queue.put({"success": False, "error": str(e)})
```

For read-only operations, skip the queue and access FreeCAD directly.

## 2. Add connection method (MCP server side)

In `src/freecad_mcp/server.py`, add to `FreeCADConnection`:

```python
def my_new_method(self, doc_name: str, param: str) -> dict:
    return self.server.my_new_method(doc_name, param)
```

## 3. Define the MCP tool

In `src/freecad_mcp/server.py`, add the tool function:

```python
@mcp.tool()
def my_new_tool(doc_name: str, param: str) -> list[TextContent | ImageContent]:
    """Clear docstring explaining what this tool does and when to use it."""
    conn = get_connection()
    result = conn.my_new_method(doc_name, param)

    if not result["success"]:
        return [TextContent(type="text", text=f"Error: {result['error']}")]

    response = [TextContent(type="text", text=f"Done: {result['result']}")]

    # Include screenshot for mutation tools
    screenshot = conn.get_active_screenshot()
    if screenshot and not _only_text_feedback:
        response.append(ImageContent(type="image", data=screenshot, mimeType="image/png"))

    return response
```

## 4. Verify

- Run `uv run ruff check src/` and `uv run mypy src/`
- Test manually: start FreeCAD with addon, start RPC server, run `uv run freecad-mcp`
- Confirm the tool appears in Claude Desktop's tool list

## Conventions

- Mutation tools return a screenshot; read-only tools may include one for context
- Tool docstrings should include usage examples (see `create_object` for reference)
- RPC responses always use `{"success": bool, ...}` shape
- Error messages should be actionable (tell the user what went wrong and how to fix it)
- Parameters use `doc_name` for document, `obj_name` for object (consistent naming)
