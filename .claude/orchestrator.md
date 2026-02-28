# Orchestrator

Read this file on every prompt to determine the correct approach.

## Step 1: Classify the request

Determine which area(s) the user's request falls into:

| Area | Scope | Key files |
|------|-------|-----------|
| `mcp-server` | MCP tool definitions, connection handling, CLI args, FastMCP lifecycle | `src/freecad_mcp/server.py` |
| `rpc-handler` | XML-RPC methods, GUI task queue, property setting, FEM creation | `addon/FreeCADMCP/rpc_server/rpc_server.py` |
| `serialization` | FreeCAD object → JSON conversion, shape/view/property serialization | `addon/FreeCADMCP/rpc_server/serialize.py` |
| `parts-library` | Parts library search, insertion, caching | `addon/FreeCADMCP/rpc_server/parts_library.py` |
| `addon-ui` | Workbench registration, menu commands, toolbar, settings UI | `addon/FreeCADMCP/InitGui.py`, `addon/FreeCADMCP/rpc_server/rpc_server.py` (GUI command classes) |
| `packaging` | pyproject.toml, versioning, PyPI distribution, entry points | `pyproject.toml` |
| `examples` | ADK / LangChain integration examples | `examples/` |
| `remote-access` | IP filtering, host validation, remote connection toggle | `addon/FreeCADMCP/rpc_server/rpc_server.py`, `src/freecad_mcp/server.py` |
| `testing-compatibility` | Version-specific bugs, serialization issues, known limitations | `.claude/context/known-issues.md`, `addon/FreeCADMCP/rpc_server/serialize.py` |
| `freecad-modeling` | Collaborative CAD modeling sessions — building geometry, iterating with screenshots, human checkpoints | Use skill `modeling-in-freecad`; read `.claude/context/freecad-modeling-guide.md` |

## Step 2: Load context

Based on the classified area(s), load the relevant context files:

- **Any area** → Read `CLAUDE.md` (project conventions)
- `mcp-server` or `rpc-handler` → Read `.claude/context/architecture.md`
- `rpc-handler` or `serialization` → Read `.claude/context/freecad-patterns.md`
- `mcp-server` (adding/modifying tools) → Read `.claude/context/tool-lifecycle.md`
- `testing-compatibility` or `serialization` → Read `.claude/context/known-issues.md`
- `packaging` or release work → Read skill `preparing-release`
- `freecad-modeling` → Read `.claude/context/freecad-modeling-guide.md`, use skill `modeling-in-freecad`

## Step 3: Understand the two-component boundary

Every feature that adds new FreeCAD functionality touches **both** components:

```
MCP Server (src/)              Addon (addon/)
─────────────────              ──────────────
Runs on host machine           Runs inside FreeCAD
Python 3.12+, typed            FreeCAD embedded Python
Can be linted/tested           Cannot be linted outside FreeCAD
Exposes tools to LLM           Executes against FreeCAD API
Connects via XML-RPC client    Serves via XML-RPC server
```

**Critical rule**: Changes to one side almost always require changes to the other. When adding a new capability, trace the full path: MCP tool → FreeCADConnection method → RPC method → GUI task → FreeCAD API call → serialized response.

## Step 4: Apply constraints

- The addon code (`addon/`) imports FreeCAD-only modules (`FreeCAD`, `FreeCADGui`, `ObjectsFem`). It **cannot** be type-checked, linted, or unit-tested outside FreeCAD.
- Only `src/` code can be validated with ruff, mypy, and pytest.
- Screenshots are returned as base64 PNGs. When `--only-text-feedback` is active, they are omitted.
- The GUI task queue pattern is mandatory for any operation that touches FreeCAD's Qt UI thread.
