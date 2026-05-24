# FreeCAD Modeling Guide

Practical lessons from building CAD models via the MCP server. Complements `freecad-patterns.md` (API reference) with workflow and modeling knowledge.

---

## Viewport Management

### Always be in the 3D view before capturing screenshots

`get_view` and `analyze_view` capture **whatever MDI window is currently active** — this can be a TechDraw drawing page, not the 3D model. Always switch to the 3D view explicitly:

```python
import FreeCADGui as Gui
mdiArea = None
for widget in Gui.getMainWindow().children():
    if hasattr(widget, 'subWindowList'):
        mdiArea = widget
        break
if mdiArea:
    for w in mdiArea.subWindowList():
        if w.windowTitle().startswith("my_doc_name"):   # match document name
            mdiArea.setActiveSubWindow(w)
            break
Gui.SendMsgToActiveView("ViewFit")
Gui.SendMsgToActiveView("ViewIsometric")
```

### Visibility management — use `MCP_Role` tagging

For documents with `MCP_Role` tagging (see `mcp-role-tagging.md`), use `show_by_role()` for all visibility management:

```python
# Before any screenshot — show only Final objects
show_by_role(doc, ["Final"])

# To also see alternative designs
show_by_role(doc, ["Final", "Alternative"])
```

This replaces manual noise-hiding loops and named container lists. The function handles containers, Body Tips, cascade cleanup, and TechDraw safety automatically.

**For untagged documents**, fall back to the type-based noise filter from `freecad-visibility.md`:
```python
noise = {"App::Origin", "App::Line", "App::Plane", "App::OriginFeature"}
for obj in doc.Objects:
    if hasattr(obj, "ViewObject") and obj.TypeId in noise:
        obj.ViewObject.Visibility = False
```

### Never do blanket visibility restore

Setting all objects visible floods the viewport — a document with 30 Part/Body containers has 210+ origin objects. **Use `show_by_role(doc, ["Final"])` to restore a clean view.** See `mcp-role-tagging.md` for the full convention and `freecad-visibility.md` for the underlying mechanics.

---

## Local Coordinate Systems (App::Origin and rotated App::Part)

Every `App::Part` and `PartDesign::Body` automatically gets an `App::Origin` with 6 child features (3 axes + 3 planes). Access via `container.Origin.OriginFeatures[i]` — index order: [0] X_Axis, [1] Y_Axis, [2] Z_Axis, [3] XY_Plane, [4] XZ_Plane, [5] YZ_Plane.

**Key pattern**: To model a rotated structure, create an `App::Part` with the rotation in its Placement, then model children in axis-aligned local coordinates. `world_pos = parent.Placement × child.Placement`.

For full details, source references, and code examples: see `freecad-origins.md`.

---

## Always Use Python for Calculations

**Never compute numbers mentally.** Always derive coordinates and dimensions in Python — even for arithmetic that looks simple.

CAD models involve chains of dependent values (floor height → stair rise → step count → opening position). A single mental arithmetic mistake silently misaligns everything built on top of it. Millimeter precision makes small errors visible.

**Run pure calculations locally** using the Bash tool — not via `execute_code` in FreeCAD:
```bash
python3 -c "
H, t, n = 2500, 200, 13
rise = H / n
print(f'rise={rise:.3f}  check={n*rise:.3f}  floor2_z={t+H}')
"
```
Use `execute_code` only when the code actually creates or modifies FreeCAD objects. Calculations that are part of an object-creation block are fine to keep inline.

**Pattern: declare all parameters at the top, derive everything else**

```python
L, W, H = 5000, 4000, 2500   # room envelope
t = 200                        # wall/slab thickness
n = 13                         # number of steps

floor2_z = t + H               # never write 2700
rise     = H / n               # 192.307... — not 192
run      = 250
stair_footprint = n * run      # 3250 — not hand-calculated
```

**When values don't divide evenly**, compute locally and surface the result to the user before building:
> "13 steps × 192.3 mm = 2499.9 mm — 0.1 mm short of 2500. Acceptable rounding, or adjust step count?"

**For boolean operations**, verify overlap locally before cutting:
```bash
python3 -c "
slab_z, slab_t, hole_z, hole_h = 2700, 200, 2695, 210
print('ok' if hole_z < slab_z and hole_z+hole_h > slab_z+slab_t else 'FAIL: cutter misses slab')
"
```

---

## Units and Coordinate System

- FreeCAD uses **millimeters** by default for Part objects
- Axes: X = length/depth, Y = width, Z = height (up)
- `Placement.Base` sets the **minimum corner** of a box (origin point), not its center
- Think of buildings: floor at z=0, walls sitting on top, stacked upward in Z

---

## Part::Box — the workhorse

```python
obj = doc.addObject("Part::Box", "MyBox")
obj.Length = 5000   # X dimension
obj.Width  = 4000   # Y dimension
obj.Height = 200    # Z dimension
obj.Placement = App.Placement(
    App.Vector(x, y, z),                        # origin corner
    App.Rotation(App.Vector(0, 0, 1), 0)        # no rotation
)
```

Always call `doc.recompute()` after all objects are created/modified.

---

## Architectural Modeling Conventions

### Room shell (box-in-box approach)

Use separate `Part::Box` objects for each wall and slab — easier to manage than boolean differences:

| Object | Length | Width | Height | Position (x, y, z) |
|--------|--------|-------|--------|---------------------|
| Floor  | L      | W     | t      | (0, 0, 0)           |
| WallSouth | L   | t     | H      | (0, 0, t)           |
| WallNorth | L   | t     | H      | (0, W-t, t)         |
| WallWest  | t   | W     | H      | (0, 0, t)           |
| WallEast  | t   | W     | H      | (L-t, 0, t)         |
| Ceiling/SecondFloor | L | W | t | (0, 0, t+H)       |

Where `L` = room length, `W` = room width, `H` = wall height, `t` = wall/slab thickness.

### Stacking floors

- Floor 1 slab: z=0 to z=t
- Walls 1: z=t to z=t+H
- Floor 2 slab: z=t+H to z=t+H+t  → `floor2_z = t + H`
- Walls 2: z=t+H+t to z=t+H+t+H  → `z2 = floor2_z + t`

---

## Staircases — Stringer Pattern

For a staircase rising height `H` over `n` steps:

```python
rise = H / n          # height per step (e.g. 2500/13 ≈ 192 mm)
run  = 250            # tread depth (mm) — typical 250 mm
sw   = 1200           # stair width (mm)
sx, sy, sz = 200, 200, t   # start position (inside the walls, on top of floor)

for i in range(n):
    step = doc.addObject("Part::Box", f"Step{i+1:02d}")
    step.Length = run
    step.Width  = sw
    step.Height = (i + 1) * rise    # cumulative height = stringer profile
    step.Placement = App.Placement(
        App.Vector(sx + i * run, sy, sz),
        App.Rotation(App.Vector(0, 0, 1), 0)
    )
```

Key insight: giving each step a **cumulative** height (`(i+1) * rise`) creates the stringer cross-section — each step fills the full volume from floor level up to its tread surface. This is simpler than individual step risers.

Total footprint: `n * run` in X, `sw` in Y.
Top step surface reaches z = `sz + H` (top of walls / bottom of upper floor slab).

---

## Boolean Operations for Openings

To cut a stair opening through a floor slab, use `Part::Cut`:

```python
# 1. Create a cutting box slightly oversized (5 mm overlap on each face)
hole = doc.addObject("Part::Box", "StairHole")
hole.Length = stair_run           # match stair footprint
hole.Width  = stair_width
hole.Height = slab_thickness + 10  # ±5 mm overlap for clean cut
hole.Placement = App.Placement(
    App.Vector(stair_x, stair_y, slab_z - 5),
    App.Rotation(App.Vector(0, 0, 1), 0)
)

# 2. Boolean cut
cut = doc.addObject("Part::Cut", "FloorWithOpening")
cut.Base = doc.getObject("SecondFloor")   # the solid to cut from
cut.Tool = hole                            # the shape to subtract

# 3. Tag and hide source objects (they are consumed by the Cut)
doc.getObject("SecondFloor").ViewObject.Visibility = False
doc.getObject("SecondFloor").MCP_Role = "Intermediate"
hole.ViewObject.Visibility = False
hole.MCP_Role = "Intermediate"

# 4. Tag the result as Final
cut.MCP_Role = "Final"
```

The `Part::Cut` result (`FloorWithOpening`) is the visible object. The originals remain in the document but are hidden and tagged `Intermediate`.

---

## Visibility Control for Exploration

For tagged documents, use `show_by_role()` as the baseline, then temporarily hide specific objects for interior views:

```python
# Start from clean state
show_by_role(doc, ["Final"])

# Temporarily hide walls on open sides to see interior
for name in ["WallSouth", "WallEast"]:
    doc.getObject(name).ViewObject.Visibility = False
```

To restore after exploration, re-run `show_by_role(doc, ["Final"])` — never manually toggle objects back on.

From an isometric view, hiding the south and east walls exposes the interior while keeping north and west walls for spatial reference.

---

## Helper Function Pattern

Always define a `place()` helper to keep placement code concise:

```python
def place(obj, x, y, z):
    obj.Placement = App.Placement(
        App.Vector(x, y, z),
        App.Rotation(App.Vector(0, 0, 1), 0)
    )
```

---

## Object Naming Conventions

- Use descriptive names with consistent casing: `WallSouth`, `SecondFloor`, `Step01`
- For numbered series, zero-pad: `Step01`…`Step13` (sorts correctly in the model tree)
- For boolean result objects, name them after what they represent: `SecondFloorCut` not `Cut001`
- Source objects consumed by booleans: keep them, hide them (don't delete — FreeCAD needs them for the parametric relationship)

---

## Common execute_code Patterns

### Create multiple objects in a loop

```python
import FreeCAD as App
doc = App.getDocument("MyDoc")

ENUM_VALUES = ["Final", "Intermediate", "Alternative", "Deprecated"]

def place(obj, x, y, z):
    obj.Placement = App.Placement(App.Vector(x, y, z), App.Rotation(App.Vector(0,0,1), 0))

def tag(obj, role="Final"):
    """Tag object with MCP_Role — MANDATORY for every new object."""
    if not hasattr(obj, "MCP_Role"):
        obj.addProperty("App::PropertyEnumeration", "MCP_Role", "MCP",
            "Object role: Final, Intermediate, Alternative, Deprecated")
        obj.MCP_Role = ENUM_VALUES
    obj.MCP_Role = role

for i in range(n):
    obj = doc.addObject("Part::Box", f"Item{i:02d}")
    obj.Length = ...
    obj.Width  = ...
    obj.Height = ...
    place(obj, x0 + i * step, y0, z0)
    tag(obj, "Final")

doc.recompute()
print("Done")
```

### Always end with `doc.recompute()` and `print("Done")`

The `print` output is returned in the tool response — confirm success.

---

## Typical Building Dimensions (starting points)

| Element | Typical value |
|---------|---------------|
| Room size | 4000–6000 mm × 3000–5000 mm |
| Wall/slab thickness | 200 mm |
| Floor-to-floor height | 2700–3000 mm (wall height + slab) |
| Wall height (clear) | 2500 mm |
| Stair rise | 150–200 mm |
| Stair run (tread) | 250–300 mm |
| Stair width | 900–1200 mm |
| Number of steps | floor-to-floor / rise (round to integer) |

---

## Parametric Assemblies: Part::Feature + Group beats monolithic PartDesign Body

PartDesign Bodies are great for human modeling in the GUI but painful to introspect or edit via Python — sketches, pads, patterns, and datum references are deeply nested and order-dependent. Repairing or tweaking a parameter usually means rebuilding the whole feature tree. They also hide the real geometry behind the App::Part Placement (see `freecad-origins.md`), so reading `Shape.BoundBox` returns local coords that look wrong.

**Pattern**: For Claude-maintained models, assemble related components as independent `Part::Feature` objects wrapped in a `App::DocumentObjectGroup`. Hoist every parameter (dimensions, counts, offsets, slope endpoints) into named constants at the top of the build script so the script itself is the source of truth. Each component is independently selectable, hideable, and replaceable. Re-running the build script with a different parameter value reproduces the design cleanly.

```python
# Parameters at top — single source of truth, easy to tweak
RAIL_HEIGHT = 80
PICKET_W, PICKET_GAP = 45, 30
CAP_RAIL_Z_TOP = 6100

def build_components(rail_h, pw, pg, cap_z):
    # ... returns list of (Part.Solid, name) tuples
    ...

group = doc.addObject("App::DocumentObjectGroup", "Assembly")
for shape, name in build_components(RAIL_HEIGHT, PICKET_W, PICKET_GAP, CAP_RAIL_Z_TOP):
    feat = doc.addObject("Part::Feature", name)
    feat.Shape = shape
    feat.MCP_Role = "Final"  # tag per .claude/context/mcp-role-tagging.md
    group.addObject(feat)
```

**When to use**: any structure assembled from multiple parts that share a coordinate system (fence panels, rail+picket+cap assemblies, modular wall systems, repeated colonnades). When the user later asks "make the cap rail 50mm taller", you edit one constant and re-run, instead of digging through a feature tree.

---

## Shared Profile Function for Co-located Objects

When several objects sit on a common surface (a sloped wall top, the ground, a ramp), each object computing its own surface elevation independently — one linearly interpolated between endpoints, another piecewise-linear — guarantees visible drift between them. The mismatch only shows up after assembly, not in any single component's screenshot.

**Pattern**: Define a single parametric `surface_z(t)` (or `surface_z(x, y)`) function and have every object that touches that surface call it. The function is the single source of truth for the surface; changing it updates all dependents consistently. Particularly important when one object uses `t_start..t_end` endpoints (effectively linear interpolation) while another iterates samples and queries the function piecewise — both MUST use the same function or they will silently disagree in the interior of the range.

```python
# Single source of truth for a piecewise-linear surface profile along a local edge.
# Replace constants with your actual breakpoints for the surface you're modelling.
T_PLATEAU_END = ...   # local-axis parameter where flat top transitions to slope
T_SLOPE_END   = ...   # local-axis parameter at the far end of the slope
Z_PLATEAU     = ...   # surface Z while on the flat top
Z_END         = ...   # surface Z at the far end of the slope

def surface_z(t):
    if t <= T_PLATEAU_END: return Z_PLATEAU
    if t >= T_SLOPE_END:   return Z_END
    return Z_PLATEAU - (t - T_PLATEAU_END) / (T_SLOPE_END - T_PLATEAU_END) * (Z_PLATEAU - Z_END)

# Every object that rides this surface calls the same function:
rail_solid    = build_rail(t_start, t_end, surface_z(t_start), surface_z(t_end))
for i in range(n_pickets):
    t = i * pitch + offset
    pickets.append(build_picket(t, z_bottom=surface_z(t), z_top=CAP_Z))
```

**Diagnostic**: if rail and pickets visibly drift apart in the middle of their range, suspect that the rail is using linear endpoint-to-endpoint interpolation while the pickets use a piecewise-linear function with a different breakpoint. Reconcile by funneling both through one shared function.

---

## Boolean Operations and Cutter Selection

### OCCT Booleans return `TopoDS_Compound`, not `Solid`

`shape.cut(...)`, `shape.common(...)`, and `shape.fuse(...)` all return a `Compound` even when the result contains exactly one solid. Assigning that compound directly to `Part::Feature.Shape` produces `Shape.ShapeType == "Compound"`, which surprises callers that expect `"Solid"` and breaks any acceptance check or downstream Boolean that requires a Solid input.

**Fix**: always extract the contained Solid(s) before assigning.

```python
result = prism.common(cutter.Shape)
if result.Volume <= 0:
    raise RuntimeError(f"Empty Boolean result (vol={result.Volume})")

if len(result.Solids) == 1:
    feature.Shape = result.Solids[0]                     # ShapeType == "Solid"
elif len(result.Solids) > 1:
    feature.Shape = Part.Compound(result.Solids)         # multi-solid compound
else:
    raise RuntimeError("Boolean result has no Solids")
```

### Never feed a 3D curved face as a PartDesign Pocket Profile

`PartDesign::Pocket`'s `Profile` is meant to be a 2D sketch. If you set Profile to a `SubShapeBinder` of a curved 3D face (e.g., a face from a terrain shell, a `Part::Scale` of a loft, or any `BSplineSurface`), PartDesign attempts to extrude that face along its own normal direction. Because the face isn't planar, the extrusion sweeps a twisted `Part::SurfaceOfExtrusion` cutter that doesn't cleanly bound the body, leaving a stray `SurfaceOfExtrusion` face on the body's Tip that visually looks like a phantom slanted plane.

**Symptom**: a body that's "almost right" but has one suspicious slanted face inheriting through to its Tip (`SurfaceOfExtrusion` in the face's `Surface` type). Downstream features that use the Tip carry the artifact forward.

**Diagnostic**:
```python
import collections
hist = collections.Counter(type(f.Surface).__name__ for f in body.Tip.Shape.Faces)
print(hist)
# {'Plane': 14, 'BSplineSurface': 8, 'SurfaceOfExtrusion': 1}  ← the 1 is the phantom
```

**Fix**: drop the PartDesign chain and use Part workbench Boolean ops (`Part.cut`, `Part.common`) against valid solids instead. They handle 3D-vs-3D cleanly and never produce SurfaceOfExtrusion artifacts. If you need to follow a curved surface from above, build a closed solid that brackets the surface (extrude a face from below to above the surface) and Boolean against that.

### When a body has accumulated pockets, the upstream `Part::MultiFuse` is often the right cutter

If you want to Boolean against "the original terrain envelope" (or any base shape that has had pockets carved into it for unrelated features), `body.Shape` may be unusable: `prism.common(body.Shape)` can return `Volume = 0` if your prism falls entirely inside the carved voids.

Find the upstream un-pocketed source (typically a `Part::MultiFuse` or `Part::Fusion` that the body chain consumes) and Boolean against that instead. Then subtract the current body to remove parts that are still genuinely solid:

```python
# Goal: fill the void that exists between the original (pre-pocket) envelope and the current body.
# Find the upstream un-pocketed source -- often a Part::MultiFuse / Part::Fusion in the document --
# and Boolean against that instead of the carved body's final Shape.
envelope_obj = doc.getObject("<your_upstream_multifuse>")   # the un-pocketed base
carved_obj   = doc.getObject("<your_carved_body>")           # the body whose voids you must respect

bounded = my_prism.common(envelope_obj.Shape)   # capped by original envelope, not the carved body
void    = bounded.cut(carved_obj.Shape)          # subtract the still-solid parts
```

**When this matters**: terrain-following gravel fills, soil-fill volumes around walls, anything where the body's voids define the space you want to occupy rather than the space you want to exclude.

### Closed wire with figure-8 / even-odd winding → annular Face

A single closed wire that walks the outer corners in one order, jumps to the inner ring, walks the inner corners in the same rotational order, and closes back to the first outer corner produces a single planar face that fills the **band/annulus** between the two rings (even/odd fill rule). No need to build separate outer and inner wires and subtract.

```python
verts = [outer_NW, outer_NE, outer_SE, outer_SW, inner_SW, inner_SE, inner_NE, inner_NW]
wire = Part.makePolygon(verts + [verts[0]])   # closed
band_face = Part.Face(wire)
# band_face.Area == outer_polygon_area - inner_polygon_area
```

Useful for perimeter footprints (drainage trenches, ring foundations, racetrack moats). The wire is also easy to edit later: change one vertex and the band shape updates.

---

## FreeCAD Python API gotchas

### `Vector.multiply(scalar)` mutates in place

`FreeCAD.Vector.multiply(s)` scales the vector **in place** and returns `self` (it does NOT return a new vector). Reusing a direction/normal vector after calling `.multiply()` on it silently corrupts every later use.

```python
along = V(dx/L, dy/L, 0)            # unit direction
p_start = c0 - along.multiply(EXT)  # BUG: along is now EXT-times longer!
p_end   = c0 + along.multiply(EXT)  # uses the already-corrupted along
```

The symptom is spectacular: geometry built afterward lands at absurd coordinates (bounding boxes in the 1e+100 range, parts scattered to "infinity").

**Fix**: use the `*` operator, which returns a new vector and leaves the operand untouched:

```python
p_start = c0 - along * EXT          # along stays a unit vector
p_end   = c0 + along * EXT
```

Rule of thumb: never call `.multiply()` / `.add()` / `.sub()` on a vector you intend to reuse; prefer the `*`, `+`, `-` operators, which are non-mutating.

### `Mesh::Feature.Mesh.Topology` / `.BoundBox` return GLOBAL coords

For a `Mesh::Feature`, `obj.Mesh.Topology` (and `obj.Mesh.BoundBox`) return points with the object's `Placement` **already applied** (i.e. global/world coordinates). This is the opposite of `Part` geometry inside an `App::Part`, where `Shape.BoundBox` is local (see `freecad-origins.md`).

Consequences:
- Setting `obj.Placement` and then reading `obj.Mesh.BoundBox` shows the **moved** position (placement baked in), not the local mesh extent.
- Code that builds a shape from `obj.Mesh.Topology` and then *also* assigns `obj.Placement` to the result will **double-apply** the placement. To move a mesh reliably for export, bake the offset into the mesh geometry (`mesh.translate(dx,dy,dz)`) and keep `Placement` at identity, OR build from Topology and leave the derived object's placement at identity.

---

## Pitfalls

- **Overlap for booleans**: cutting tool must protrude slightly beyond both faces of the target solid (use ±5 mm) to avoid zero-thickness faces that FreeCAD may fail to process
- **Recompute required**: objects don't update until `doc.recompute()` is called; boolean results may show stale geometry without it
- **Source objects in booleans**: do not delete `Base` or `Tool` objects used by `Part::Cut`/`Part::Fuse` — they remain parametrically linked; hide them instead
- **Staircase top step**: with `(i+1) * rise` cumulative height and `n` steps where `n = H / rise`, the top surface of the last step lands exactly at `z = sz + H` (the underside of the upper floor slab) — verify this aligns before cutting the opening
- **get_objects on large documents**: can time out or exceed token limits; use `execute_code` + targeted queries instead
- **`Shape.BoundBox` and `.Vertexes` apply the object's OWN Placement, not the parents'.** For a top-level object (or one whose `App::Part` ancestors have identity Placement), `Shape.BoundBox.XMin` is the actual world position. For an object nested inside an App::Part with a non-trivial Placement, `Shape.BoundBox` returns coords in that App::Part's local frame — NOT world. To get true world coords, walk up parents accumulating Placements (only App::Part counts; DocumentObjectGroup has no Placement). See `freecad-origins.md` § "Gotcha: `Body.Shape.BoundBox` returns LOCAL coordinates inside an App::Part" for the helper.
- **Rotated / non-axis-aligned geometry**: `Shape.BoundBox` is the world-axis-aligned bounding box of the (possibly rotated) shape — its X/Y/Z ranges are world projections, NOT the shape's local edge extents. Do not derive parameters along a local edge from world-axis BB ranges; project sample points onto the local axis instead. See `freecad-origins.md` § "Gotcha: rotated-shape world BoundBox vs local edge parameters". For modeling new rotated solids, use `Part.makePolygon` + `Part.Face` + `face.extrude()` to align with actual edges.
- **Multi-object assembly coverage**: never compare an individual object's BoundBox against the overall perimeter in isolation — multiple objects may jointly cover a boundary. See `designs-store.md` for the full anti-pattern.
- **Terrain surface detection**: `solid.common(box).BoundBox.ZMax` can return false highs when sampling inside a hillside. See `designs-store.md` for details.
- **Visibility pitfalls**: see `mcp-role-tagging.md` for the `MCP_Role` convention (`show_by_role()`) and `freecad-visibility.md` for the underlying mechanics (TechDraw crash, Body Tip, cascade propagation).
