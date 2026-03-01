# FreeCAD MCP - Developer Guide

## Project Overview

FreeCAD MCP bridges Claude (or other LLMs) with FreeCAD through the Model Context Protocol. It consists of two components:

1. **MCP Server** (`src/freecad_mcp/server.py`) — A FastMCP server exposing CAD tools to LLM clients
2. **FreeCAD Addon** (`addon/FreeCADMCP/`) — An XML-RPC server running inside FreeCAD that executes commands

Communication flow: `LLM Client → MCP (stdio) → MCP Server → XML-RPC (port 9875) → FreeCAD Addon → FreeCAD GUI Thread`

## Architecture

```
src/freecad_mcp/
  server.py              # FastMCP server, all MCP tools, CLI entry point
  __init__.py             # Empty package marker
  py.typed                # PEP 561 type stub marker

addon/FreeCADMCP/
  Init.py                 # Empty (FreeCAD requires it)
  InitGui.py              # Workbench registration, menu/toolbar commands
  rpc_server/
    __init__.py            # Re-exports rpc_server module
    rpc_server.py          # XML-RPC server, GUI task queue, FreeCADRPC handler, settings, IP filtering
    serialize.py           # FreeCAD objects → JSON-serializable dicts
    parts_library.py       # Parts library search and insertion

examples/
  adk/                    # Google ADK integration example
  langchain/              # LangChain ReAct agent example
```

## Key Design Patterns

### GUI Task Queue (Thread Safety)
FreeCAD GUI operations must run on the main Qt thread. The addon uses a queue-based pattern:
- RPC methods put lambdas into `rpc_request_queue`
- A Qt timer (`process_gui_tasks`, 500ms interval) picks tasks from the queue and executes them on the GUI thread
- Results are returned via `rpc_response_queue`
- The RPC thread blocks on `rpc_response_queue.get()` until the GUI thread responds

See `rpc_request_queue`, `rpc_response_queue`, and `process_gui_tasks()` in `addon/FreeCADMCP/rpc_server/rpc_server.py`.

### Property Setting
`set_object_property()` in `rpc_server.py` handles complex type mapping:
- **Placement**: dict → `FreeCAD.Placement` (accepts both "Base" and "Position" keys)
- **Vectors**: `{x, y, z}` dict → `FreeCAD.Vector`
- **References**: object name strings → resolved FreeCAD object references
- **ViewObject**: nested dict applied to `obj.ViewObject`
- **Fallback**: direct `setattr` for simple types

### FEM Object Creation
FEM objects use `ObjectsFem.make*()` factory methods with a naming convention map. `Fem::FemMeshGmsh` has special handling that runs `GmshTools().create_mesh()` after creation. FEM objects are auto-added to their parent Analysis.

### Screenshot Feedback
Most mutation tools return a base64 PNG screenshot. The addon checks view compatibility first (TechDraw/Spreadsheet views don't support `saveImage`). Screenshots are captured to temp files, base64-encoded, and cleaned up. Use `--only-text-feedback` to disable this and save tokens.

**Size behavior**: When `width`/`height` are omitted from `get_view` or `get_active_screenshot`, the viewport dimensions are used. On high-DPI (Retina) displays this can produce images >300KB. Pass explicit small dimensions (200–400px) to keep responses compact.

**Graceful degradation**: When the active view doesn't support `saveImage` (TechDraw, Spreadsheet), the screenshot is skipped and a text note is returned instead. The tool never fails due to a missing screenshot.

### Known Limitations

- **`FreeCAD.Color` missing in FreeCAD 1.0.2**: The `App.Color` class doesn't exist in older releases. `serialize.py` guards this with `hasattr(App, "Color")` to avoid `AttributeError` crashes in `get_objects`/`get_object`.
- **Screenshot size overflow**: On high-DPI displays, default viewport screenshots can exceed 300KB. Always pass explicit `width`/`height` to `get_view`.
- **Parts library dependency**: `get_parts_list` and `insert_part_from_library` require the optional [FreeCAD Parts Library addon](https://github.com/FreeCAD/FreeCAD-library). They return empty/error responses if it's not installed.
- **Serialization fragility**: Unhandled FreeCAD types in `serialize_value()` fall back to `str()`. If `serialize_object()` itself raises, `get_objects`/`get_object` return `{"success": false, "error": ...}` instead of crashing.
- **`InitGui.py` class body scoping**: FreeCAD loads `InitGui.py` via `exec()` without an explicit globals dict, so module-level imports are NOT visible inside class bodies (only string/number literals are safe there). Always set computed attributes like `Icon` inside `Initialize()` using `self.__class__.Icon = ...`. See `.claude/context/freecad-patterns.md` for the full explanation and source reference.

## MCP Tools Reference

| Tool | Purpose | Notes |
|------|---------|-------|
| `create_document` | Create new FreeCAD document | No screenshot |
| `create_object` | Create Part::, Draft::, PartDesign::, Fem:: objects with properties | Returns screenshot |
| `edit_object` | Modify existing object properties | Returns screenshot |
| `delete_object` | Remove object from document | Returns screenshot |
| `execute_code` | Run arbitrary Python in FreeCAD context | `capture_screenshot=False` to skip screenshot on read-only queries |
| `get_view` | Capture screenshot (Isometric/Front/Top/Right/Back/Left/Bottom/Dimetric/Trimetric) | Pass explicit dimensions to control size |
| `get_objects` | List all objects — compact summary by default (Name/Label/TypeId/Placement/Shape) | Pass `detailed=True` for full properties; prefer `execute_code` for targeted reads on large docs |
| `get_object` | Full properties for a single object | Use for discovery when you don't know property names; prefer `execute_code` once you do |
| `insert_part_from_library` | Load part from FreeCAD parts library | Requires Parts Library addon |
| `get_parts_list` | List available .FCStd files in parts library | Requires Parts Library addon |
| `list_documents` | List open document names | No screenshot, read-only |
| `snapshot_view` | Store a "before" screenshot + Gemini pre-analysis for before/after comparison | Gemini-enhanced if CLI available; graceful fallback otherwise |
| `analyze_view` | Capture screenshot + Gemini visual analysis (recommended for verification) | Gemini-enhanced if CLI available; returns screenshot only otherwise |

There is also a prompt `asset_creation_strategy` that guides LLMs through proper CAD creation workflows.

### Querying strategy (tiered)

Use the lowest-cost tool that answers the question:

| Goal | Tool |
|------|------|
| What objects exist in the document? | `get_objects` (summary, default) |
| What properties does an unfamiliar object have? | `get_object` (full detail, one object) |
| Targeted read of known properties / cross-object queries / computed values | `execute_code(capture_screenshot=False)` |

`execute_code` is strictly better for surgical reads once you know the property name:
```python
# Returns one line instead of 40 serialized properties
doc = FreeCAD.getDocument("MyDoc")
w = doc.getObject("WallSouth")
print(f"height={w.Height} width={w.Width}")
```

For cross-object queries:
```python
walls = [o for o in doc.Objects if o.TypeId == "Arch::Wall"]
for w in walls:
    print(f"{w.Label}: h={w.Height} w={w.Width}")
```

## Development Setup

### Prerequisites
- Python 3.11+ (see `.python-version`) — matches FreeCAD's bundled Python 3.11
- `uv` package manager
- FreeCAD installed locally

> **Note:** FreeCAD bundles its **own Python 3.11** interpreter (verified: 3.11.13 in FreeCAD 1.0.2 on macOS).
> Addon code in `addon/` runs under Python 3.11 — do not use Python 3.12+ syntax there.
> See `.claude/context/known-issues.md` for how to verify the version locally on any platform.

### Install / update addon (local dev)
This is how you "deploy" the addon locally — copy `addon/FreeCADMCP` into FreeCAD's user Mod directory.
Run this after every change to addon code to pick up changes in FreeCAD (requires FreeCAD restart).

```bash
# macOS (confirmed path):
cp -r addon/FreeCADMCP ~/Library/Application\ Support/FreeCAD/Mod/

# Linux:
cp -r addon/FreeCADMCP ~/.local/share/FreeCAD/Mod/   # or ~/.FreeCAD/Mod/

# Linux Snap:
cp -r addon/FreeCADMCP ~/snap/freecad/common/Mod/

# Windows:
# xcopy /E /I addon\FreeCADMCP %APPDATA%\FreeCAD\Mod\FreeCADMCP
```

Verify the copy is in sync (only `__pycache__` should differ):
```bash
diff -r addon/FreeCADMCP ~/Library/Application\ Support/FreeCAD/Mod/FreeCADMCP
```

### Claude Desktop config (local dev)
The `~/Library/Application Support/Claude/claude_desktop_config.json` file is the config for the
Claude Desktop app. Add the `freecad` entry under `mcpServers` (use the absolute path to this repo):

```json
{
  "mcpServers": {
    "freecad": {
      "command": "/Users/lef/.local/bin/uv",
      "args": ["--directory", "/Users/lef/Repos/lef/freecad-mcp", "run", "freecad-mcp"]
    }
  }
}
```

### Clone FreeCAD source (for AI-assisted development)
```bash
./scripts/setup-freecad-source.sh
```
Clones FreeCAD at the version in `.FREECAD_VERSION` into `vendor/FreeCAD/` (gitignored).
Claude uses this to look up object types, property names, and API signatures.
See `.claude/context/freecad-source.md` for grep patterns and directory layout.

### Run MCP server (dev mode)
```bash
uv run freecad-mcp
# or with options:
uv run freecad-mcp --only-text-feedback --host 192.168.1.100
```

## Code Quality

### Tools
- **ruff** — linting and formatting
- **mypy** — type checking

Run before committing:
```bash
uv sync --group dev   # installs ruff, mypy into the venv
uv run ruff check src/
uv run ruff format src/
uv run mypy src/
```

Note: The addon code (`addon/`) runs inside FreeCAD's embedded Python and imports FreeCAD-specific modules (`FreeCAD`, `FreeCADGui`, `ObjectsFem`, `femmesh`). It cannot be type-checked or linted outside FreeCAD.

### Pre-commit Hooks
Git pre-commit hooks are configured. Ensure your venv is activated before committing so hooks can find the required tools.

## Design Knowledge Store

Any session that creates or modifies a FreeCAD design **must** maintain `.designs/<document-name>/`.
This folder is gitignored (local only) but the convention is defined in `.claude/context/designs-store.md` and shared with all Claude instances through this file.

**Mandatory**: At the start of every design session, check for `.designs/<doc-name>/` and either read it to restore context or create it. At the end, update `objects.md`, `tasks.md`, and `README.md` with what changed.

See `.claude/context/designs-store.md` for the full convention: file structure, templates, and session lifecycle rules.

## Conventions

### Commits
Use [conventional commits](https://www.conventionalcommits.org/):
```
feat: add new tool for sketch creation
feat(addon): add IP filtering for remote connections
fix(mcp): handle missing view object gracefully
docs: update installation instructions
chore: bump version to 0.1.17
```

Do not include co-author lines in commits.

### Code Style
- Follow existing patterns in each component
- MCP tools use `get_freecad_connection()` to obtain the singleton `FreeCADConnection`
- RPC methods return `{"success": bool, "error": str}` dicts
- Property errors are caught per-property (don't fail the whole operation)
- Use `FreeCAD.Console.PrintMessage/PrintError/PrintWarning()` for logging in addon code

### Error Response Format

RPC methods return `{"success": bool, "error": str}` dicts. Read-only methods (`get_objects`, `get_object`) also use this format, wrapping their data in `{"success": true, "objects": [...]}` or `{"success": true, "object": {...}}`. MCP tools translate errors into `TextContent` messages prefixed with `"Error: "`. Connection-level failures (e.g., FreeCAD not running) raise Python exceptions caught by the MCP tool's `try/except`.

### Adding a New MCP Tool
See `.claude/context/tool-lifecycle.md` for the full step-by-step guide with code templates.

### Adding a New RPC Method
1. Add the method to `FreeCADRPC` in `rpc_server.py`
2. For GUI-thread work: put a lambda into `rpc_request_queue`, wait on `rpc_response_queue`
3. The `_gui` helper should **return** its result (not put it into the queue) — `process_gui_tasks()` handles the queue
4. The public method wraps the raw result from the queue into `{"success": bool, ...}` dict
5. For read-only operations (like `get_objects`): access FreeCAD directly (no queue needed)

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `AttributeError: module 'FreeCAD' has no attribute 'Color'` | FreeCAD 1.0.2 lacks `App.Color` | Fixed: `serialize.py` uses `hasattr(App, "Color")` guard |
| Screenshot >300KB / token overflow | High-DPI viewport used as default size | Pass explicit `width`/`height` (200–400px) to `get_view` |
| `get_parts_list` returns empty | Parts Library addon not installed | Install the FreeCAD Parts Library addon |
| `get_objects` returns raw XML-RPC fault | Unhandled serialization error | Fixed: `get_objects`/`get_object` wrap errors in `{"success": false}` |
| `NoneType` error in `get_object` | Object name doesn't exist in document | Fixed: returns `{"success": false, "error": "Object '...' not found"}` |
| `Connection refused` on tool call | FreeCAD not running or RPC server not started | Start FreeCAD, then click "Start MCP Server" in the addon toolbar |

## Important Constants

| Constant | Value | Location |
|----------|-------|----------|
| RPC port | `9875` | rpc_server.py |
| GUI task timer | 500ms | rpc_server.py (`process_gui_tasks`) |
| Settings file | `freecad_mcp_settings.json` | rpc_server.py (in FreeCAD user data dir) |
| Default allowed IPs | `127.0.0.1` | rpc_server.py (`_DEFAULT_SETTINGS`) |

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]>=1.12.2` | FastMCP framework with CLI |
| `validators>=0.34.0` | IP/hostname validation for `--host` flag |

## Build & Release

- Build system: **hatchling**
- Entry point: `freecad-mcp = "freecad_mcp.server:main"`
- Published to PyPI as `freecad-mcp`
- Users install with `uvx freecad-mcp`
- `assets/` and `results/` are excluded from the distribution
