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

## Gotcha: rotated-shape world BoundBox vs local edge parameters

When a shape is rotated around any axis, `Shape.BoundBox` reports the projection of the geometry onto world axes — not the extents of the shape's local edges. Deriving a parameter along a local edge from a world-axis coordinate (e.g. solving for `t` along an edge using a world-Y value of a corner) silently produces wrong results whenever the edge isn't axis-aligned. The error grows with rotation angle and is invisible in screenshots until parts visibly drift.

**Symptom**: A slab parallelogram rotated ~13° around Z has 4 corners spanning some world-Y range. Computing "where does the south edge of an inner subregion start along the local east edge?" by solving `Y(t) = world_Y_at_that_corner` gives a wrong `t` because the local edge isn't parallel to world Y — its direction has both X and Y components, so a constant world-Y line crosses the local edge at a different `t` than the corner's true position.

**Fix**: Parameterize against the shape's actual vertices and local axis vectors, not against world-axis BB ranges. Recover the local axis by subtracting two corner vertices, then project sample points onto that axis.

```python
# v0, v1 are two adjacent corner vertices defining a local edge
p0 = FreeCAD.Vector(v0.X, v0.Y, v0.Z)
p1 = FreeCAD.Vector(v1.X, v1.Y, v1.Z)
axis = (p1 - p0)
length = axis.Length
unit = axis / length
# Parameter t in [0, length] for a sample world point P along this local edge:
t = (P - p0).dot(unit)
```

The same principle applies when deriving picket positions, fence lengths, or any parametric value along an edge of a rotated structure — always project onto the local axis, never read from world BB extents.

### Corollary: a rotated square's world BoundBox OVERSTATES its side length

A square member of side `w` rotated by angle `t` in the XY plane has an axis-aligned bounding box of `w * (|cos t| + |sin t|)` on each side, NOT `w`. So a 45 mm picket rotated 12 degrees to align with an angled fence reads as ~53.4 mm in its BoundBox (45 * (cos12 + sin12) = 45 * 1.186). Reading the bbox and treating it as the member's true cross-section silently inflates the size (and, if you then rebuild axis-aligned boxes from the bbox, you fatten every member and shrink the gaps).

To recover the true side length of a rotated square member: take the half-diagonal from center to a corner vertex and divide by sqrt(2), times 2 (`side = (corner - center).Length / sqrt(2) * 2`), or inspect a face's actual edge length, never the bbox.

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

## Gotcha: `Body.Shape.BoundBox` returns LOCAL coordinates inside an App::Part

`Body.Shape.BoundBox` (or `Pocket.Shape.BoundBox`, or any feature inside a Body inside an App::Part) returns coordinates in the App::Part's **local frame**, NOT world coordinates. If the App::Part has a non-zero Placement, you will see numbers that disagree with what the object's world position is.

**Example scenario**: An App::Part has `Placement.Z = 3000`. Its child Body reports `Shape.BoundBox.ZMin = 0`, `ZMax = 2400`. The wall the Body represents actually lives at WORLD Z = 3000..5400 — the parent's +3000 Z offset is silently applied at render time but is NOT reflected in the child Body's `Shape.BoundBox`. Treating the reported BB as world coords leads to placing dependent objects (railings, claddings, sections) at the wrong height.

**Diagnostic**: walk up the parent chain and accumulate Placements. Only `App::Part` counts as a true coordinate frame; `App::DocumentObjectGroup` carries no Placement.

```python
def parents_of(o, doc):
    return [p for p in doc.Objects if hasattr(p, 'Group') and o in (p.Group or [])]

def cumulative_world_placement(o, doc):
    pl = FreeCAD.Placement()
    cur = o
    while cur is not None:
        if hasattr(cur, 'Placement') and cur.TypeId not in ("App::DocumentObjectGroup",):
            pl = cur.Placement.multiply(pl)
        parents = parents_of(cur, doc)
        cur = next((p for p in parents if p.TypeId == "App::Part"), None)
    return pl

# To get the true WORLD BoundBox of a Body inside an App::Part:
import Part
sh_world = body.Shape.copy()
sh_world.Placement = cumulative_world_placement(body, doc).multiply(sh_world.Placement)
world_bb = sh_world.BoundBox
```

**Rule of thumb**: if a sketch / feature appears in the *correct visual position* in the GUI but `Shape.BoundBox` numbers look offset, suspect an App::Part parent with a non-zero Placement.

---

## Gotcha: Writing a Shape inside an App::Part (Placement composes, not auto-compensates)

When you `parent.addObject(child)` where `parent` is an `App::Part` with a non-identity Placement, FreeCAD does **NOT** auto-adjust the child's Placement to keep its world position constant. The child inherits the parent's Placement at render time, so:

```
rendered_world_position = parent.Placement × child.Placement × child.Shape.local_coords
```

If you built `child.Shape` in **world coordinates** and then assigned it to a child of an App::Part with `Placement = (0,0,+3000)`, the rendered object will float +3000mm above where you intended.

**Symptom**: An object is geometrically correct in isolation (Shape vertices match the world coords you computed) but renders at a position offset by the parent's Placement. Volume, face count, and shape are right; only the visual Z (or X/Y) is wrong, by exactly the parent's offset.

**Three valid fixes**:

```python
# Option A: keep the object top-level (no App::Part parent at all)
obj = doc.addObject("Part::Feature", "Thing")
obj.Shape = world_shape  # placement (0,0,0), GlobalPlacement (0,0,0), renders at world coords

# Option B: transform Shape to parent-LOCAL coords before assigning
parent_gp = parent.getGlobalPlacement()
local_shape = world_shape.copy()
local_shape.transformShape(parent_gp.inverse().toMatrix())
obj = doc.addObject("Part::Feature", "Thing")
parent.addObject(obj)
obj.Shape = local_shape  # parent.Placement re-applies the offset at render time

# Option C: assign world Shape, then explicitly set Placement to the parent's inverse.
# (Less common, and beware: assigning .Placement on an App::Part child can trigger
# downstream auto-adjustment; verify after recompute that .getGlobalPlacement() is identity.)
```

**Diagnostic**: after `parent.addObject(child)`, compare `child.getGlobalPlacement()` to `child.Placement`. If they differ, the parent's Placement is being inherited. Then check whether `child.Shape.BoundBox` reflects world or local coords (it's local). The actual rendered position is `child.getGlobalPlacement().multVec(shape_point)`.

**Rule of thumb**: if your geometry math was correct and your visualization is off by a constant offset that matches an ancestor App::Part's Placement, this is the bug. Pick option A or B and move on.

---

## Visibility

`App::Origin`, `App::Line`, `App::Plane`, and `App::Point` should almost never be visible. A document with 30 Part/Body containers has **210 origin objects** in FreeCAD 1.0 (30 x 7) or **240** in 1.1+ (30 x 8). See `freecad-visibility.md` for the canonical noise filter, cleanup scripts, and the full always-hidden type list.
