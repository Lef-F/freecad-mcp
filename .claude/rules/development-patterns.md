# Development Patterns

## Code Organization

### MCP Server (`src/`)
- All tools defined in `server.py` using `@mcp.tool()` decorators
- `FreeCADConnection` is the XML-RPC client wrapper — add methods here for new RPC calls
- `get_connection()` provides the singleton connection instance (lazy init + ping check)
- CLI argument parsing in `main()` at bottom of file
- Server lifecycle managed via `server_lifespan` async context manager

### Addon (`addon/`)
- `FreeCADRPC` class in `rpc_server.py` handles all incoming RPC requests
- GUI-thread work goes through `rpc_request_queue` / `rpc_response_queue`
- Read-only queries can access FreeCAD directly (no queue)
- Property setting is centralized in `set_object_property()` — extend this for new types
- Serialization logic lives in `serialize.py` — add new serializers for new FreeCAD types
- Parts library is isolated in `parts_library.py`

## Error Handling

- RPC methods return `{"success": bool, "error": str}` — never raise across XML-RPC boundary
- Property errors are caught per-property so one bad property doesn't abort the whole operation
- Screenshot failures return `None` gracefully — the MCP tool handles the absence
- Connection failures are logged and re-raised as exceptions to the MCP framework

## Naming Conventions

- MCP tool parameters: `doc_name`, `obj_name`, `obj_type`, `obj_properties`
- RPC method names match MCP tool names where possible
- GUI-thread helper methods prefixed with `_` and suffixed with `_gui` (e.g., `_create_object_gui`)
- FreeCAD object types use their full qualified name (e.g., `Part::Box`, `Draft::Circle`, `Fem::FemMeshGmsh`)

## Testing Strategy

- `src/` code: validate with ruff, mypy, and pytest
- `addon/` code: manual testing inside FreeCAD (no automated testing possible outside FreeCAD)
- Integration testing: start FreeCAD → start RPC server → run MCP server → invoke tools
- Always test the full round-trip when adding new tools

## What NOT to Do

- Don't import FreeCAD modules in `src/` — they don't exist outside FreeCAD
- Don't run GUI operations outside the task queue in the addon
- Don't add dependencies to pyproject.toml unless absolutely necessary (keep the MCP server lightweight)
- Don't hardcode port 9875 in new locations — it's already defined in the RPC server and connection class
- Don't modify `Init.py` — it must remain empty (FreeCAD convention)
