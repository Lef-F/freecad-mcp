# FreeCAD API Patterns

Common patterns used throughout the addon code. Reference this when working on `addon/FreeCADMCP/`.

## Core Modules

| Import | Alias | Purpose |
|--------|-------|---------|
| `FreeCAD` | `App` | Documents, objects, geometry, vectors, placements |
| `FreeCADGui` | `Gui` | GUI operations, views, selections, screenshots |
| `ObjectsFem` | — | Factory methods for FEM objects |
| `femmesh.gmshtools` | — | Mesh generation with Gmsh |

## Document & Object Operations

```python
# Documents
doc = FreeCAD.newDocument("MyDoc")
doc = FreeCAD.getDocument("MyDoc")
names = list(FreeCAD.listDocuments().keys())

# Objects
obj = doc.addObject("Part::Box", "MyBox")
obj = doc.getObject("MyBox")
doc.removeObject("MyBox")
doc.recompute()

# Properties
obj.PropertiesList          # list of all property names
getattr(obj, "Length")      # read property
setattr(obj, "Length", 10)  # write property
```

## Placement & Geometry

```python
# Vectors
v = FreeCAD.Vector(x, y, z)

# Rotations (axis + angle in degrees)
r = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 45)

# Placement = position + rotation
p = FreeCAD.Placement(
    FreeCAD.Vector(10, 20, 0),
    FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0)
)
obj.Placement = p
```

## View Operations

```python
view = FreeCADGui.ActiveDocument.ActiveView

# Standard views
view.viewIsometric()
view.viewFront()
view.viewTop()
view.viewRight()
view.viewBack()
view.viewLeft()
view.viewBottom()
view.viewDimetric()
view.viewTrimetric()

# Screenshots (width/height are optional — omit to use viewport size)
view.saveImage("/tmp/screenshot.png", width, height)
view.saveImage("/tmp/screenshot.png")  # uses current viewport dimensions

# Selection & fit
FreeCADGui.Selection.addSelection(obj)
FreeCADGui.Selection.clearSelection()
view.fitAll()  # zoom to fit all objects
```

## FEM Objects

```python
# Analysis container
analysis = ObjectsFem.makeAnalysis(doc, "Analysis")

# Mesh (requires geometry reference)
mesh = ObjectsFem.makeMeshGmsh(doc, "FEMMesh")
mesh.Part = geometry_obj
from femmesh.gmshtools import GmshTools
GmshTools(mesh).create_mesh()

# Constraints & Materials
constraint = ObjectsFem.makeConstraintFixed(doc, "Fixed")
material = ObjectsFem.makeMaterialSolid(doc, "Steel")
```

## Property Type Mapping

When setting properties via `set_object_property()`:

| Input Type | Target | Conversion |
|-----------|--------|------------|
| `dict` with x/y/z | Vector property | `FreeCAD.Vector(d["x"], d["y"], d["z"])` |
| `dict` with Base/Rotation | Placement | `FreeCAD.Placement(base_vec, rotation)` |
| `str` (for Base/Tool/Source/Profile) | Object reference | `doc.getObject(value)` |
| `list` of `[obj_name, face]` | References list | Resolved to object + subshape tuples |
| `dict` with nested keys | ViewObject | Applied to `obj.ViewObject` via `setattr` |
| primitives | Direct property | `setattr(obj, key, value)` |

## Console Logging

```python
FreeCAD.Console.PrintMessage("Info\n")
FreeCAD.Console.PrintWarning("Warning\n")
FreeCAD.Console.PrintError("Error\n")
```

## InitGui.py Loading — Critical Scoping Trap

FreeCAD loads `InitGui.py` via `exec(compile(f.read(), InstallFile, 'exec'))` with **no explicit globals/locals** (see `vendor/FreeCAD/src/Gui/FreeCADGuiInit.py`, `RunInitGuiPy()`, line ~143).

**What this means:** Names imported at the top of `InitGui.py` (e.g. `import os`) are added to the *local scope of `RunInitGuiPy`*, not to the exec's globals. Class bodies look up free variables against the **exec's globals** (i.e. `FreeCADGuiInit.py`'s globals) — where those names don't exist. This causes `NameError` at class-definition time.

**The trap:** This code fails:
```python
import os  # goes into RunInitGuiPy's locals
class MyWorkbench(Workbench):
    Icon = os.path.join(os.path.dirname(__file__), "icon.svg")  # NameError: 'os' not defined
```

**The correct pattern**: set workbench attributes inside `Initialize()` using `self.__class__`. Do NOT use `__file__` — it is also not set in the exec scope. Instead, derive the addon directory from a real module's `__file__`:
```python
class MyWorkbench(Workbench):
    MenuText = "My Addon"  # string literals are fine — no name lookup needed

    def Initialize(self):
        import os
        from rpc_server import rpc_server  # real module with a real __file__
        # rpc_server/rpc_server.py → dirname → rpc_server/ → dirname → FreeCADMCP/
        addon_dir = os.path.dirname(os.path.dirname(rpc_server.__file__))
        self.__class__.Icon = os.path.join(addon_dir, "mcp_workbench.svg")
        # ... rest of initialization
```

**Rule:** Never reference imported names in `InitGui.py` class bodies. Only string/number literals are safe there. Move all computed values into `Initialize()`, `Activated()`, or other methods. `__file__` is also unavailable — use a real module's `__file__` instead.

## Important Constraints

- All GUI operations must run on the Qt main thread (use the task queue)
- `obj.ViewObject` is only available when FreeCADGui is loaded
- `saveImage()` fails on TechDraw, Spreadsheet, and Drawing views
- FreeCAD's embedded Python version may differ from the system Python
- **Version compatibility**: Guard `isinstance` checks on FreeCAD types with `hasattr` (e.g., `hasattr(App, "Color") and isinstance(value, App.Color)`). Some types don't exist in all FreeCAD versions.
- **Screenshot size**: Always pass explicit `width`/`height` dimensions for MCP responses to avoid oversized images on high-DPI displays
- **Serialization safety**: `serialize_value()` must never raise — catch exceptions and fall back to `str(value)`. See `.claude/context/known-issues.md` for details.
