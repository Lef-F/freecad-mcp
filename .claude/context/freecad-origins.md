# FreeCAD Origins and Local Coordinate Systems

Source-verified findings from `/vendor/FreeCAD/src/App/` and `/vendor/FreeCAD/src/Mod/PartDesign/`.

---

## What is App::Origin?

Every `App::Part` and `PartDesign::Body` **automatically** gets an `App::Origin` child. Never create one manually.

The origin provides a local coordinate frame with child objects:

| Index | TypeId | Role | Description | Since |
|-------|--------|------|-------------|-------|
| 0 | `App::Line` | `X_Axis` | Local X axis | 1.0 |
| 1 | `App::Line` | `Y_Axis` | Local Y axis | 1.0 |
| 2 | `App::Line` | `Z_Axis` | Local Z axis | 1.0 |
| 3 | `App::Plane` | `XY_Plane` | Local XY plane | 1.0 |
| 4 | `App::Plane` | `XZ_Plane` | Local XZ plane | 1.0 |
| 5 | `App::Plane` | `YZ_Plane` | Local YZ plane | 1.0 |
| 6 | `App::Point` | `Origin` | Local origin point | 1.1 |

Access via `container.Origin.OriginFeatures[i]` — the index order above is guaranteed by the source.

> **FreeCAD 1.1 change**: OriginFeatures now has 7 items (was 6). Indices 0–5 are unchanged. The new `App::Point` at index 6 is part of the PartDesign origin datums rewrite (PR #18126). Files referencing origin datums may be auto-converted on open; converted files are NOT backward-compatible with 1.0.x.

**Inheritance chain** (from FreeCAD source):
```
App::Part → OriginGroupExtension → automatic App::Origin
PartDesign::Body → OriginGroupExtension → automatic App::Origin
```

**Source**: `App/OriginGroupExtension.cpp`, `App/Part.h`, `Mod/Part/App/BodyBase.h`

---

## How Placement Rotation Transforms Children

When an `App::Part` (or `PartDesign::Body`) has a non-identity Placement, all child objects' world positions are computed as:

```
world_placement = parent.Placement × child.Placement
```

This means: if you give a Part a 45° rotation around Z, a child box placed at local (10, 0, 0) appears at the 45°-rotated world position. This is the cleanest way to model a structure that is rotated relative to global axes.

**Source**: `App/OriginGroupExtension.cpp` — `extensionGetSubObject()` multiplies `mat *= placement().getValue().toMatrix()` and `GeoFeatureGroupExtension.cpp` — `recursiveGroupPlacement()`.

---

## Python Patterns

### Accessing axes and planes

```python
body = doc.getObject("MyBody")     # App::Part or PartDesign::Body
origin = body.Origin               # App::Origin container

x_axis    = origin.OriginFeatures[0]
y_axis    = origin.OriginFeatures[1]
z_axis    = origin.OriginFeatures[2]
xy_plane  = origin.OriginFeatures[3]
xz_plane  = origin.OriginFeatures[4]
yz_plane  = origin.OriginFeatures[5]
origin_pt = origin.OriginFeatures[6]  # FreeCAD 1.1+ only
```

### Attaching a sketch to a body's local plane

```python
sketch = doc.addObject("Sketcher::SketchObject", "Sketch1")
body.addObject(sketch)
sketch.AttachmentSupport = (body.Origin.OriginFeatures[3], [""])  # XY_Plane
sketch.MapMode = "FlatFace"
doc.recompute()
```

**Source**: `Mod/PartDesign/TestPartDesignGui.py` lines 155–158.

### Using a local axis for PolarPattern

```python
pattern.Axis = (body.Origin.OriginFeatures[2], [""])   # Z_Axis
```

**Source**: `Mod/PartDesign/PartDesignTests/TestPolarPattern.py`.

### Modeling a rotated structure using a Part as a local frame

```python
import FreeCAD as App

# Create a Part whose Placement defines the local coordinate system
local_part = doc.addObject("App::Part", "ParkingLot")
local_part.Placement = App.Placement(
    App.Vector(0, 0, 0),
    App.Rotation(App.Vector(0, 0, 1), 12.8)  # 12.8° rotation around Z
)
doc.recompute()

# Child objects placed in local coordinates (axis-aligned relative to the Part)
# are automatically transformed to world space via the Part's rotation.
wall = doc.addObject("Part::Box", "Wall")
wall.Length = 5000; wall.Width = 200; wall.Height = 3000
# Place in LOCAL frame (no need to manually apply the rotation):
wall.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())
local_part.addObject(wall)
doc.recompute()
# → wall appears at 12.8° rotation in world space
```

**When to use this pattern**: When an entire structure is rotated relative to global axes (e.g., a building not aligned with the street grid), create a parent App::Part with the rotation baked in, then model everything in axis-aligned local coordinates. Much simpler than manually rotating every solid.

---

## Visibility

`App::Origin`, `App::Line`, `App::Plane`, and `App::Point` should almost never be visible. A document with 30 Part/Body containers has **210 origin objects** in FreeCAD 1.0 (30 x 7) or **240** in 1.1+ (30 x 8). See `freecad-visibility.md` for the canonical noise filter, cleanup scripts, and the full always-hidden type list.
