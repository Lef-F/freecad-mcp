---
name: adding-techdraw-dimensions
description: Adds or manipulates dimensions in TechDraw pages by tracing 3D geometry through Section -> Shape2DView -> DrawProjGroupItem -> DrawViewDimension. Covers coordinate mapping, edge identification, and dimension creation.
---

# Adding TechDraw Dimensions

## When to Use

Use when the user wants to add, remove, or edit dimensions on a TechDraw drawing page,
or when programmatic dimension placement is needed for a section view.

---

## Architecture: How Dimensions Work

```
3D objects
  -> Section (App::FeaturePython, BIM/ArchSectionPlane.py)   -- clips objects; defines view plane
  -> Shape2DView (Draft::Shape2DView / Part::Part2DObjectPython) -- projects section to 2D edges
  -> DrawProjGroupItem (TechDraw::DrawProjGroupItem)          -- renders Shape2DView onto page
  -> DrawViewDimension (TechDraw::DrawViewDimension)          -- annotation referencing edges
```

`DrawViewDimension` references edges or vertices from a `DrawProjGroupItem`:
```python
dim.References2D = [(view, ("EdgeN",))]              # single edge (length of that edge)
dim.References2D = [(view, ("EdgeA", "EdgeB"))]      # two edges (distance between them)
dim.References2D = [(view, ("VertexA", "VertexB"))]  # two vertices (point-to-point distance)
```
Edge/vertex numbers are **1-based** (`Edge1`, `Vertex1`, ...) matching `Shape.Edges[N-1]` / `Shape.Vertexes[N-1]`.

`DrawProjGroupItem` inherits from `DrawViewPart` (source: `DrawViewPart.h:91`). Its `Source`
property is a `PropertyLinkList` containing the 3D/Shape2DView objects it renders.

See [`reference/lineage.md`](reference/lineage.md) for the complete bidirectional traversal
map (3D objects ↔ Sections ↔ Shape2DViews ↔ DrawProjGroupItems ↔ Pages).

---

## Step 1 -- Inspect Existing Dimensions

```python
doc = FreeCAD.getDocument("my_doc")
dims = [o for o in doc.Objects if o.TypeId == "TechDraw::DrawViewDimension"]
for d in dims:
    refs = getattr(d, "References2D", [])
    print(f"{d.Name}: type={d.Type} refs={[(v.Name, e) for v, e in refs]}")
```

---

## Step 2 -- Understand the Coordinate Mapping

`Shape2DView.Shape.Edges` stores edges in the **section's local XY plane**. The section's
`Placement.Matrix` column layout is (source: `ArchSectionPlane.py:709-714`):
```
[A11  A12  A13  A14]   column 1 = local X axis (vx)
[A21  A22  A23  A24]   column 2 = local Y axis (vy)
[A31  A32  A33  A34]   column 3 = normal / local Z (vz)
[  0    0    0    1]   column 4 = origin (translation)
```

Project a 3D point onto the section's local X and Y axes:
```python
def project_to_section(section, px, py, pz):
    """Return (local_x, local_y) -- raw projections onto section's local X and Y axes."""
    m = section.Placement.Matrix
    dx, dy, dz = px - m.A14, py - m.A24, pz - m.A34
    local_x = m.A11*dx + m.A21*dy + m.A31*dz   # dot product with column 1
    local_y = m.A12*dx + m.A22*dy + m.A32*dz   # dot product with column 2
    return local_x, local_y
```

**Shape2DView uses a Y-down convention** (SVG-compatible). For standard vertical sections this
means the vertical axis in the drawing is `-pz` (not `+pz`). Calibration handles this via offset.

### Calibration helper

The projected coordinates have an internal origin offset that must be measured from known points:

```python
def calibrate_section_offsets(section, ref_3d_point, ref_shape_X, ref_shape_Y):
    """
    Compute (C_x, C_y) so that:
        shape_X = project_to_section(...)[0] + C_x
        shape_Y = project_to_section(...)[1] + C_y

    ref_3d_point  -- (px, py, pz) of a known 3D point visible in the Shape2DView
    ref_shape_X   -- measured shape_X for that point (from edge/vertex BoundBox)
    ref_shape_Y   -- measured shape_Y for that point (from edge/vertex BoundBox)
    """
    proj_x, proj_y = project_to_section(section, *ref_3d_point)
    return ref_shape_X - proj_x, ref_shape_Y - proj_y
```

### Shortcut for vertical sections

When the section plane is vertical (normal in the world XY plane, like most architectural
sections) and the vertical in-drawing axis maps to world Z, use:

```python
# Vertical sections only:
shape_Y = -pz + C_y          # C_y = shape_Y_ref + pz_ref
shape_X = ly + C_x           # ly = m.A12*(px-m.A14) + m.A22*(py-m.A24) + m.A32*(pz-m.A34)
```

Verify this shortcut by checking two known Z values — if `shape_Y` is linear in `-pz`, the
shortcut is valid. For tilted sections, use the full `project_to_section()` above.

### Find good reference points

1. Take a 3D object at a known position visible in the section.
2. Find its edge in `sv.Shape.Edges` by scanning BoundBoxes at the expected shape coords.
3. Use the edge centroid as `(ref_shape_X, ref_shape_Y)`.

Confirm calibration with a second independent reference — if `C_x` / `C_y` are consistent,
the calibration is valid.

---

## Step 3 -- Convert 3D Position to Shape Coordinates

```python
def to_shape(section, px, py, pz, C_x, C_y):
    local_x, local_y = project_to_section(section, px, py, pz)
    return local_x + C_x, local_y + C_y   # (shape_X, shape_Y)
```

---

## Step 4 -- Find Edges or Vertices Near a Target Position

```python
def find_edges_near(sv, shape_X, shape_Y, tol=50):
    """Return list of (edge_number_1based, BoundBox) within tol of target centroid."""
    results = []
    for i, e in enumerate(sv.Shape.Edges):
        bb = e.BoundBox
        cx = (bb.XMin + bb.XMax) / 2
        cy = (bb.YMin + bb.YMax) / 2
        if abs(cx - shape_X) < tol and abs(cy - shape_Y) < tol:
            results.append((i + 1, bb))
    return results

def find_horizontal_edges_at_Z(sv, Z, C_y, tol=20):
    """Find near-horizontal edges at a specific world Z level (vertical sections only)."""
    target_Y = -Z + C_y
    return [(i+1, e.BoundBox)
            for i, e in enumerate(sv.Shape.Edges)
            if e.BoundBox.YLength < tol
            and abs((e.BoundBox.YMin + e.BoundBox.YMax)/2 - target_Y) < tol]

def find_vertical_edges_near_X(sv, shape_X, tol=20):
    """Find near-vertical edges at a specific shape_X position."""
    return [(i+1, e.BoundBox)
            for i, e in enumerate(sv.Shape.Edges)
            if e.BoundBox.XLength < tol
            and abs((e.BoundBox.XMin + e.BoundBox.XMax)/2 - shape_X) < tol]

def find_vertices_near(sv, shape_X, shape_Y, tol=10):
    """
    Find vertices near a target position.
    Prefer vertices over edges for point-to-point Distance dims -- more precise.
    """
    return [(i+1, v.Point)
            for i, v in enumerate(sv.Shape.Vertexes)
            if abs(v.Point.x - shape_X) < tol
            and abs(v.Point.y - shape_Y) < tol]
```

---

## Step 5 -- Find the DrawProjGroupItem for a Shape2DView

```python
def find_view_for_shape2dview(doc, sv_name):
    for obj in doc.Objects:
        if obj.TypeId == "TechDraw::DrawProjGroupItem":
            if any(s.Name == sv_name for s in getattr(obj, "Source", [])):
                return obj
    return None
```

---

## Naming Convention (Required)

Always use descriptive names that encode the page and what is being measured:

```
Dim<PageCode>_<WhatItMeasures>
```

Examples:
- `DimSectAA_FloorToRoof` (height from floor to roof soffit on Section A-A)
- `DimSectAA_FloorToWallTop` (floor to top of perimeter wall on Section A-A)
- `DimSectBB_WallThickness` (wall thickness on Section B-B)
- `DimPlan_BayWidth` (room or bay width on plan view)
- `DimFacadeW_TotalHeight` (total height on west facade)

**Why this matters:** After any model edit, edge numbers shift. Descriptive names let you
identify which dimensions broke and re-create them from known 3D geometry — without having
to reverse-engineer what an anonymous `Dimension007` was measuring.

---

## Step 6 -- Create a Dimension

### Method A: Edge references (References2D)

```python
import FreeCAD

page = doc.getObject("PageName")
view = find_view_for_shape2dview(doc, "Shape2DViewName")

dim = doc.addObject("TechDraw::DrawViewDimension", "DimName")
dim.Type = "DistanceY"        # see type table below
dim.MeasureType = "Projected" # "Projected" (2D, default) or "True" (3D; requires References3D)
dim.References2D = [(view, ("Edge10", "Edge25"))]
page.addView(dim)
# Dimensions are NOT auto-positioned by addView -- they land at (0,0) unless set:
# dim.X and dim.Y are VIEW-LOCAL offsets in mm from the view's center point on the page.
# Positive X = right, positive Y = up. NOT page-absolute coordinates.
dim.X = -50   # mm to the left of view center
dim.Y = 10    # mm above view center
doc.recompute()
```

### Method B: TechDraw.makeDistanceDim() -- Preferred for coordinate-driven dims

When you know the target positions in view-local coordinates (e.g. from `getVisibleEdges()`),
use `TechDraw.makeDistanceDim()`. This avoids edge-number instability entirely.

**Critical: always negate getVisibleEdges() Y before passing to makeDistanceDim or setting dim.Y.**

```
getVisibleEdges() Y convention:  Y-DOWN (SVG)  -- positive Y = lower on page
TechDraw page/dim.Y convention:  Y-UP          -- positive Y = higher on page

page_Y = -vis_Y   (always, for all section orientations)
```

```python
import FreeCAD, TechDraw

sv    = doc.getObject("Shape2DViewName")
view  = find_view_for_shape2dview(doc, "Shape2DViewName")
page  = doc.getObject("PageName")
scale = view.Scale

# Step 1: Read visible edges (vis_Y is Y-DOWN)
vis = view.getVisibleEdges()

def find_horiz_vis_edges(vis, target_vis_Y, tol=0.5, min_len_mm=5.0):
    """Find near-horizontal visible edges at a given vis_Y position (Y-down coords)."""
    results = []
    for i, e in enumerate(vis):
        bb_e = e.BoundBox
        y_mid = (bb_e.YMin + bb_e.YMax) / 2
        if bb_e.YLength < tol and abs(y_mid - target_vis_Y) < tol and bb_e.XLength > min_len_mm:
            results.append((bb_e.XLength, i, bb_e, y_mid))
    return sorted(results, reverse=True)

# Step 2: Find vis_Y for each level. Verify: lower feature = more POSITIVE vis_Y.
# Then convert to page_Y:
floor_vis_Y  = +8.85   # from getVisibleEdges scan
roof_vis_Y   = -16.95
rail_vis_Y   = -30.95

floor_page_Y = -floor_vis_Y   # = -8.85  (below center, correct: floor is at bottom)
roof_page_Y  = -roof_vis_Y    # = +16.95 (above center)
rail_page_Y  = -rail_vis_Y    # = +30.95 (higher)

# Step 3: Create dimension using page_Y coordinates
dim_x = -52.0   # view-local X offset from view center (negative = left of view)

fp = FreeCAD.Vector(dim_x, floor_page_Y, 0)   # page Y-UP coords
tp = FreeCAD.Vector(dim_x, roof_page_Y,  0)
dim = TechDraw.makeDistanceDim(view, "DistanceY", fp, tp)
dim.MeasureType = "Projected"
page.addView(dim)
dim.X = dim_x
dim.Y = (floor_page_Y + roof_page_Y) / 2   # label centered between anchors, also Y-up
doc.recompute()
# Verify: dim.getRawValue().Value == expected distance
```

**Why prefer Method B:**
- Edge numbers are unstable across recomputes; coordinate points are not
- `getVisibleEdges()` returns the actual rendered edges in the correct coordinate space
- Measure what you intend to measure — no guessing which edge index maps to which line

### Dimension Types

| Type | References2D | Notes |
|------|-------------|-------|
| `"Distance"` | one edge **or** two vertices | General length (oblique OK) |
| `"DistanceX"` | one edge **or** two vertices | Horizontal component only |
| `"DistanceY"` | one edge **or** two vertices | Vertical component only |
| `"DistanceZ"` | one edge **or** two vertices | Depth component only |
| `"Radius"` | one circular edge | Adds `R` prefix |
| `"Diameter"` | one circular edge | Adds diameter symbol |
| `"Angle"` | two edges | Acute angle between edges |
| `"Angle3Pt"` | three vertices: point, apex, point | Angle measured at middle vertex |
| `"Area"` | one face | Area measurement |

```python
# Radius on a circular edge
dim.Type = "Radius"
dim.References2D = [(view, ("Edge5",))]

# Angle between two edges
dim.Type = "Angle"
dim.References2D = [(view, ("Edge3", "Edge7"))]

# 3-point angle: angle at Vertex5, arms toward Vertex3 and Vertex9
dim.Type = "Angle3Pt"
dim.References2D = [(view, ("Vertex3", "Vertex5", "Vertex9"))]

# Point-to-point distance using vertices (more precise than two edges)
dim.Type = "DistanceY"
dim.References2D = [(view, ("Vertex2", "Vertex8"))]
```

### Optional Properties

```python
# Display format (printf-style)
# Actual FreeCAD default is "%.2w" (%w = significant-digit rounding, not decimal places).
# "%.2f" also works; "%.0f" raises a runtime error. Leave unset to keep the system default.
dim.FormatSpec = "%.2w"      # default (significant digits); "%.2f" for fixed decimals
dim.Inverted = False          # True: flip sign

# Tolerances
dim.EqualTolerance = True     # auto-set UnderTolerance = -OverTolerance
dim.OverTolerance = 0.5       # upper tolerance value (mm)
dim.UnderTolerance = -0.5     # lower tolerance (ignored when EqualTolerance=True)

# Mark as theoretical/exact (draws a box around the value)
dim.TheoreticalExact = False

# Custom arrow direction (e.g. for oblique/axonometric views)
dim.AngleOverride = True
dim.LineAngle = 45.0          # degrees (dimension line direction)
dim.ExtensionAngle = 135.0    # degrees (extension lines direction)
```

---

## Step 7 -- Worked Pattern: Height Dimension Between Two Z Levels

```python
# Given: two Z values and calibrated C_y; section is vertical
Z_floor, Z_wall_top = 3000, 5572

floor_edges    = find_horizontal_edges_at_Z(sv, Z_floor,    C_y, tol=15)
wall_top_edges = find_horizontal_edges_at_Z(sv, Z_wall_top, C_y, tol=15)

if floor_edges and wall_top_edges:
    # Pick the widest edge at each level (most likely the structural element)
    floor_e    = sorted(floor_edges,    key=lambda x: x[1].XLength, reverse=True)[0]
    wall_top_e = sorted(wall_top_edges, key=lambda x: x[1].XLength, reverse=True)[0]

    # Use the naming convention: Dim<PageCode>_<WhatItMeasures>
    dim = doc.addObject("TechDraw::DrawViewDimension", "DimSectAA_FloorToWallTop")
    dim.Type = "DistanceY"
    dim.MeasureType = "Projected"
    dim.References2D = [(view, (f"Edge{floor_e[0]}", f"Edge{wall_top_e[0]}"))]
    page.addView(dim)
    # dim.X / dim.Y are VIEW-LOCAL offsets from the view's center (mm on page)
    dim.X = -65.0   # left of center; adjust so it doesn't overlap other dims
    dim.Y = -12.0
    doc.recompute()
    print(f"Created {dim.Name}: Edge{floor_e[0]}(Z~{Z_floor}) to Edge{wall_top_e[0]}(Z~{Z_wall_top})")
    print(f"  Expected value: {Z_wall_top - Z_floor} mm")
```

---

## Common Pitfalls

| Problem | Fix |
|---------|-----|
| `DrawPage.Visibility = True` crashes FreeCAD | Never set TechDraw page Visibility to True |
| Edge numbers shift after recompute | Always recompute first, then re-read edge numbers — they are NOT stable across recomputes |
| Dimension shows `?` or stale value | Check `References2D` edges exist; bad refs fail silently — no error is raised |
| Dimension lands at (0, 0) on page | `addView` does NOT auto-position dimensions — always set `dim.X` and `dim.Y` manually |
| `dim.X`/`dim.Y` misplaced despite setting them | These are **view-local offsets from view center**, NOT page-absolute coordinates. `(0,0)` = view center, not page corner |
| Dimensions upside-down (floor at top, railing at bottom) | `getVisibleEdges()` returns Y-DOWN coords; `makeDistanceDim` and `dim.Y` expect Y-UP. Negate ALL Y values: `page_Y = -vis_Y`. Higher Z → more negative vis_Y → more positive page_Y → higher on page. |
| `"%.0f"` FormatSpec causes runtime error | `"%.0f"` raises `unsupported format string passed to Base.Quantity.__format__`. Leave FormatSpec unset or use `"%.f"` |
| `f"{dim.getRawValue():.2f}"` raises format error | `getRawValue()` returns a `Quantity` object, not a float. Use `dim.getRawValue().Value` for a plain float |
| makeDistanceDim gives value 100x too large | Input coordinates must be view-local (scaled, centered). Raw shape coords cause wrong scale. Use `getVisibleEdges()` coordinates directly |
| Duplicate dimensions after `addView` inside loop | Calling `doc.recompute()` inside a `page.addView()` loop duplicates views. Add all dims first, then call one `doc.recompute()` at the end |
| `C_x` wrong / dimension misplaced | Re-calibrate with a second independent known point |
| No edges found at expected Z | Check `Section.Objects` includes the target 3D object; also check C_y is correct |
| Wrong dimension type for direction | `"DistanceX"` = horizontal, `"DistanceY"` = vertical, `"Distance"` = oblique |
| Edge not found but vertex is | Use `find_vertices_near()` — vertices are more precise for point-to-point dims |
| `MeasureType = "True"` shows wrong value | Requires `References3D` to be set; if empty, falls back to stale/incorrect |
| `-pz + C_y` formula gives wrong coords | That shortcut is for **vertical sections only** — use `project_to_section()` for tilted sections |
| Radius / Diameter shows wrong value | Source edge must be a circular arc — check `type(Edges[i].Curve).__name__` |
| **NEVER call `page.ViewObject.doubleClicked()` from MCP code** | Triggers TechDraw rendering internals which injects phantom `CosmeticVertex` objects with massive wrong coordinates (millions of mm), making the view appear enormous and unusable. TechDraw screenshots don't work from MCP anyway (`get_view` returns "Visual preview unavailable"). There is no valid reason to open a TechDraw page programmatically. |
| Phantom CosmeticVertexes with huge coords (e.g. 2,978,200 mm) on a view | Created by TechDraw rendering side-effects. Fix: `view.removeCosmeticVertex(tag)` for each bad tag, then `doc.recompute()`. Detect: scan `view.CosmeticVertexes` for `abs(cv.Point.x) > 10000 or abs(cv.Point.y) > 10000`. |
| **NEVER call `FreeCADGui.updateGui()` without a specific reason** | Flushing the GUI event queue can trigger pending TechDraw or PartDesign operations unexpectedly, causing hard-to-diagnose side effects including phantom vertex injection. |
