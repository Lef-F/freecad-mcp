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

## Important Constraints

- All GUI operations must run on the Qt main thread (use the task queue)
- `obj.ViewObject` is only available when FreeCADGui is loaded
- `saveImage()` fails on TechDraw, Spreadsheet, and Drawing views
- FreeCAD's embedded Python version may differ from the system Python
