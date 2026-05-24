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

### Safe deletion of a PartDesign Body (and its children)

Calling `doc.removeObject()` while iterating `doc.Objects` (or a body's `Group`) raises `Cannot access attribute of deleted object` as soon as the first child is gone — the live references in the iterator become stale. PartDesign Bodies hold Sketches, Pads, Patterns, ShapeBinders, and Datums that should be removed together to avoid orphaned dependencies.

**Pattern**: collect every child's `Name` into a plain list (strings only, no live references) first, then iterate the list and remove by name. Remove the Body last.

```python
def delete_body(doc, body):
    child_names = [o.Name for o in body.Group if o is not None]  # snapshot strings
    for name in child_names:
        if doc.getObject(name) is not None:
            doc.removeObject(name)
    doc.removeObject(body.Name)
    doc.recompute()
```

The same pattern (snapshot names first, iterate strings, remove by name) applies to any bulk-deletion that uses live object references — including DocumentObjectGroup members and dependent feature trees.

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

### Sampling terrain elevation via vertical line section

To find the ground Z at an arbitrary (X, Y) sample point, intersect the terrain shape with a vertical `Part.LineSegment` spanning safely below to safely above the terrain, then read the intersection vertices. This gives exact elevations including multi-layer terrains (overhangs, caves, stacked surfaces). Reading from a BoundBox or projecting the nearest vertex is unreliable on non-flat or multi-shell terrain.

```python
import Part

def sample_terrain_top_z(terrain_obj, x, y, z_lo=-1000, z_hi=10000):
    """Return the highest Z where a vertical line at (x, y) hits the terrain shape."""
    line = Part.LineSegment(
        FreeCAD.Vector(x, y, z_lo),
        FreeCAD.Vector(x, y, z_hi),
    ).toShape()
    section = terrain_obj.Shape.section(line, True)
    zs = sorted((v.Z for v in section.Vertexes), reverse=True)
    return zs[0] if zs else None
```

Useful for fall-protection regulations ("fence top must be ≥1.1m above outside ground"), drainage analysis, or any check that depends on the real ground level at a position. Sample at multiple positions along a perimeter to find the worst-case ground height.

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
- `saveImage()` fails on TechDraw, Spreadsheet, and Drawing views. For TechDraw specifically, the QGraphicsScene render workaround documented in `.claude/context/freecad-drawings.md` § "Rendering a TechDraw Page to PNG" lets you produce PNGs anyway.
- FreeCAD's embedded Python version may differ from the system Python
- **Version compatibility**: Guard `isinstance` checks on FreeCAD types with `hasattr` (e.g., `hasattr(App, "Color") and isinstance(value, App.Color)`). Some types don't exist in all FreeCAD versions.
- **Screenshot size**: Always pass explicit `width`/`height` dimensions for MCP responses to avoid oversized images on high-DPI displays
- **Serialization safety**: `serialize_value()` must never raise — catch exceptions and fall back to `str(value)`. See `.claude/context/known-issues.md` for details.
