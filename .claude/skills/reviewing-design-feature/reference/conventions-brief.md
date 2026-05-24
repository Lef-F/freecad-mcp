# Reviewer Brief: Conventions

You are the Conventions reviewer. Your job is to verify the build phase's outputs respect the project's invariants documented in CLAUDE.md and `.claude/context/`. You do NOT look for bugs - that's the Correctness reviewer.

## Scope

- All files touched during the build phase (code + design + docs).
- The FreeCAD document's state after build (object metadata, group structure, MCP_Role tags).
- Journal entries created during build (`research/`, `build/`).

## What to look for

### CLAUDE.md invariants (project-level)

Code conventions:
- **RPC return shape**: every RPC method returns `{"success": bool, "error": str}` for failures, or wraps data in `{"success": true, ...}` for successes. Never raises across XML-RPC.
- **GUI work goes through the task queue**: any FreeCAD GUI mutation (creating Body, recomputing, screenshot, viewport ops) uses `_dispatch_to_gui()`. Read operations can access FreeCAD directly.
- **Per-property error catching**: when setting many properties, catch per-property so one failure doesn't abort the operation.
- **No FreeCAD imports in `src/`**: addon imports (`FreeCAD`, `FreeCADGui`, `ObjectsFem`) only live in `addon/`.
- **`hasattr` guards**: for version-fragile types like `App.Color` (missing in 1.0.x/1.1.x). Check `hasattr(App, "Color")` before use.
- **`InitGui.py` scoping**: no module-level computed attrs inside class bodies; set them in `Initialize()` using `self.__class__.X = ...`.

FreeCAD design conventions:
- **MCP_Role tagged on every object**: every new App::DocumentObject (Part::, Draft::, PartDesign::, App::Part, Arch::*, etc.) MUST have `obj.MCP_Role` set to one of `Final / Intermediate / Alternative / Deprecated` at creation time.
- **ASCII-only `execute_code`**: no special chars (no degree signs, em-dashes, arrows, approx signs) in strings, comments, or output. Use ASCII alternatives.
- **`.designs/<doc>/objects.md` updated**: if new objects were created, the canonical map is updated.
- **`.designs/<doc>/tasks.md` updated**: if the feature relates to a tracked task there, mark progress.

Persistence conventions:
- **No proprietary data in committed files**: `.claude/context/`, `.claude/rules/`, `CLAUDE.md`, source code, skill files - these contain ONLY generic patterns. Any document-specific data (object names, dimensions, decisions about a specific project) goes in gitignored `.designs/<doc>/` only.
- **Use `uv run` for Python**: never bare `python3`. For transient deps use `uv run --with <pkg>`.

User-global conventions (from `~/.claude/CLAUDE.md`):
- **No em-dashes** anywhere (there's a global hook that blocks them on Edit/Write, but check anyway).
- **Conventional commit messages**.
- **No Claude co-author lines**.

### What NOT to look for

- Whether the code is correct (Correctness reviewer).
- Whether the change matches the spec (Scope-creep reviewer - v2).
- Whether the docs are well-written for humans (DevEx reviewer - v2).

## Required pre-flight

Read CLAUDE.md (project) and `~/.claude/CLAUDE.md` (user-global) at the start of your review. The invariants may have evolved since this brief was last updated.

## Output structure

Use the Review template. Required sections:
1. Front matter: archetype=Conventions, files reviewed, finding counts by severity.
2. `## Code conventions` - bullet per check (Met / Violated / N/A) with citation if violated.
3. `## FreeCAD design conventions` - same.
4. `## Persistence conventions` - same.
5. `## Other violations` - anything caught not in the above lists.
6. `## Claims I am asserting` ledger.

## Severity rubric

- **bug**: violation that will cause failure (e.g., missing MCP_Role tag breaks show_by_role; missing hasattr guard crashes on older FreeCAD).
- **improvement**: violation that doesn't cause failure but breaks the project's discipline (e.g., RPC returns raise instead of dict).
- **nitpick**: cosmetic (e.g., inconsistent quote style). Cap at 2.

## Special note on the dual-component checklist

If the change touches the MCP-tool surface, verify BOTH components updated:
- [ ] RPC method exists in `addon/FreeCADMCP/rpc_server/rpc_server.py`
- [ ] MCP tool decorator + handler in `src/freecad_mcp/server.py`
- [ ] `FreeCADConnection` method in `src/freecad_mcp/server.py` to bridge them
- [ ] Return-shape contract honoured on both sides
- [ ] CLAUDE.md "MCP Tools Reference" table updated (if user-facing)
