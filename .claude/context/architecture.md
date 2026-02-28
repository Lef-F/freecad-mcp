# Architecture

## Communication Flow

```
LLM Client (Claude Desktop / ADK / LangChain)
    │  MCP protocol (stdio)
    ▼
MCP Server (src/freecad_mcp/server.py)
    │  XML-RPC over HTTP (port 9875)
    ▼
FreeCAD Addon RPC Server (addon/FreeCADMCP/rpc_server/)
    │  GUI task queue (thread-safe)
    ▼
FreeCAD Application (Qt main thread)
```

## Components

### MCP Server (`src/freecad_mcp/server.py`)
- Built on **FastMCP** framework
- Exposes 11 tools + 1 prompt to LLM clients
- Manages a singleton `FreeCADConnection` (XML-RPC client)
- Handles CLI args: `--only-text-feedback`, `--host`
- Validates host with `validators` library
- Lifecycle: attempts connection at startup (warns if unavailable), reconnects lazily on first tool call if needed

### FreeCAD Addon (`addon/FreeCADMCP/`)
- Registers as a FreeCAD Workbench with toolbar and menu
- Runs `FilteredXMLRPCServer` in a daemon thread on port 9875
- `FreeCADRPC` class handles all incoming RPC calls
- Settings persisted to `freecad_mcp_settings.json` in FreeCAD user data dir

### Thread Safety Model
FreeCAD's Qt event loop requires GUI operations on the main thread. The addon solves this with:

1. RPC method receives request on background thread
2. Wraps operation as lambda, puts it in `rpc_request_queue`
3. `process_gui_tasks()` timer (500ms) picks up tasks on GUI thread
4. Result returned via `rpc_response_queue`
5. RPC method unblocks and returns to caller

Read-only operations (e.g., `get_objects`, `get_object`) skip the queue and access FreeCAD directly.

## Data Serialization

FreeCAD objects are converted to JSON-compatible dicts by `serialize.py`:
- `serialize_object()` → full object with Name, Label, TypeId, Properties, Placement, Shape, ViewObject
- `serialize_value()` → handles Vector, Rotation, Placement, primitives, collections
- `serialize_shape()` → Volume, Area, vertex/edge/face counts
- `serialize_view_object()` → ShapeColor, Transparency, Visibility

## Remote Access

When remote connections are enabled:
- Server binds to `0.0.0.0` instead of `localhost`
- `FilteredXMLRPCServer` validates client IPs against allowed list (supports CIDR)
- MCP server accepts `--host` flag to connect to remote FreeCAD instances
