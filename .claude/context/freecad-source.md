# FreeCAD Source Reference

The FreeCAD source code is cloned locally at `vendor/FreeCAD/` (gitignored).
Version is pinned in `.FREECAD_VERSION`. Set it up with:

```bash
./scripts/setup-freecad-source.sh
```

If `vendor/FreeCAD/` does not exist, you can still look things up via GitHub:
```
https://github.com/FreeCAD/FreeCAD/tree/<version>/<path>
```
where `<version>` comes from `.FREECAD_VERSION` (e.g. `1.0.2`).

---

## Key Directories

| Path | What's there |
|------|-------------|
| `vendor/FreeCAD/src/Mod/Part/App/` | Part primitives (`.h` headers + `.pyi` stubs) |
| `vendor/FreeCAD/src/Mod/Part/App/PrimitiveFeature.h` | Property definitions for Box, Sphere, Cylinder, Cone, Torus, etc. |
| `vendor/FreeCAD/src/Mod/Draft/draftmake/` | One `make_*.py` per Draft object — pure Python, fully readable |
| `vendor/FreeCAD/src/Mod/Draft/draftobjects/` | Draft object class definitions |
| `vendor/FreeCAD/src/Mod/Fem/ObjectsFem.py` | All 61 FEM `make*()` factory functions — pure Python |
| `vendor/FreeCAD/src/Base/VectorPy.xml` | Vector class Python binding spec |
| `vendor/FreeCAD/src/Base/PlacementPy.xml` | Placement class Python binding spec |
| `vendor/FreeCAD/src/Base/RotationPy.xml` | Rotation class Python binding spec |
| `vendor/FreeCAD/src/App/DocumentPy.xml` | Document Python binding (addObject, getObject, etc.) |
| `vendor/FreeCAD/src/Mod/PartDesign/` | PartDesign Body and features |
| `vendor/FreeCAD/src/Mod/Sketcher/` | Sketcher constraints and geometry |

---

## Common Lookup Patterns

### Find all properties of a Part primitive
```bash
grep -A 30 "class Sphere" vendor/FreeCAD/src/Mod/Part/App/PrimitiveFeature.h
grep -A 30 "class Box" vendor/FreeCAD/src/Mod/Part/App/FeaturePartBox.h
```

### List all Part make* functions
```bash
grep "make" vendor/FreeCAD/src/Mod/Part/App/AppPartPy.cpp | grep "PyDoc_STR\|\"make" | head -30
```

### List all FEM factory functions
```bash
grep "^def make" vendor/FreeCAD/src/Mod/Fem/ObjectsFem.py
```

### Find what type string a Draft object uses
```bash
grep "addObject\|FeaturePython\|Part2DObject" vendor/FreeCAD/src/Mod/Draft/draftmake/make_circle.py
```

### Find all Draft make_* modules
```bash
ls vendor/FreeCAD/src/Mod/Draft/draftmake/make_*.py
```

### Look up a specific Draft object's properties
```bash
grep -n "addProperty\|Proxy\|ViewObject" vendor/FreeCAD/src/Mod/Draft/draftobjects/circle.py
```

### Find object type strings (addObject first argument)
```bash
grep -r "addObject(" vendor/FreeCAD/src/Mod/Part/TestPartApp.py | head -20
grep -r "addObject(" vendor/FreeCAD/src/Mod/Fem/ObjectsFem.py | head -20
```

### Check method signature from XML binding spec
```bash
grep -A 5 "saveImage" vendor/FreeCAD/src/Gui/View3DInventorPy.xml
```

---

## Known Object Types (Quick Reference)

### Part Primitives (via `doc.addObject()`)
- `Part::Box` — Length, Width, Height
- `Part::Sphere` — Radius, Angle1, Angle2, Angle3
- `Part::Cylinder` — Radius, Height, Angle
- `Part::Cone` — Radius1, Radius2, Height, Angle
- `Part::Torus` — Radius1, Radius2, Angle1, Angle2, Angle3
- `Part::Plane` — Length, Width
- `Part::Wedge` — Xmin/Xmax, Ymin/Ymax, Zmin/Zmax, Z2min/Z2max, X2min/X2max
- `Part::Helix` — Pitch, Height, Radius, Angle
- `Part::Feature` — generic (holds a Shape property)

### Part Operations
- `Part::Cut`, `Part::Fuse`, `Part::Common` — boolean ops (Base, Tool)
- `Part::Extrusion`, `Part::Sweep`, `Part::Loft`, `Part::RuledSurface`
- `Part::Chamfer`, `Part::Fillet`, `Part::Mirroring`, `Part::Scale`, `Part::Refine`

### Draft (created via `Draft.make_*()`, not `addObject()` directly)
All Draft objects use `Part::FeaturePython` or `Part::Part2DObjectPython` internally.
Use the Draft Python API: `import Draft; Draft.make_circle(radius)` etc.

### FEM (via `ObjectsFem.make*()`)
Use `grep "^def make" vendor/FreeCAD/src/Mod/Fem/ObjectsFem.py` for the full list.
Key ones: `makeAnalysis`, `makeMeshGmsh`, `makeSolverCalculiX`, `makeConstraintFixed`,
`makeMaterialSolid`, `makeEquationElasticity`.

### Other
- `Sketcher::SketchObject`
- `PartDesign::Body`, `PartDesign::Pad`, `PartDesign::Pocket`
- `Spreadsheet::Sheet`
- `TechDraw::DrawProjGroup`

---

## Version Matching

The version in `.FREECAD_VERSION` should match what FreeCAD reports via:
```python
import FreeCAD; print(FreeCAD.Version()[0:3])  # e.g. ['1', '0', '2']
```

When the user upgrades FreeCAD, update `.FREECAD_VERSION` and re-run the setup script.
