# FreeCAD Modeling Guide

Practical lessons from building CAD models via the MCP server. Complements `freecad-patterns.md` (API reference) with workflow and modeling knowledge.

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

# 3. Hide source objects (they are consumed by the Cut)
doc.getObject("SecondFloor").ViewObject.Visibility = False
hole.ViewObject.Visibility = False
```

The `Part::Cut` result (`FloorWithOpening`) is the visible object. The originals remain in the document but are hidden.

---

## Visibility Control for Exploration

Hide walls on the "open" sides of a building to see the interior:

```python
for name in ["WallSouth", "WallEast", "Wall2South", "Wall2East"]:
    doc.getObject(name).ViewObject.Visibility = False
```

To restore:
```python
doc.getObject("WallSouth").ViewObject.Visibility = True
```

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

def place(obj, x, y, z):
    obj.Placement = App.Placement(App.Vector(x, y, z), App.Rotation(App.Vector(0,0,1), 0))

for i in range(n):
    obj = doc.addObject("Part::Box", f"Item{i:02d}")
    obj.Length = ...
    obj.Width  = ...
    obj.Height = ...
    place(obj, x0 + i * step, y0, z0)

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

## Pitfalls

- **Overlap for booleans**: cutting tool must protrude slightly beyond both faces of the target solid (use ±5 mm) to avoid zero-thickness faces that FreeCAD may fail to process
- **Recompute required**: objects don't update until `doc.recompute()` is called; boolean results may show stale geometry without it
- **Source objects in booleans**: do not delete `Base` or `Tool` objects used by `Part::Cut`/`Part::Fuse` — they remain parametrically linked; hide them instead
- **Staircase top step**: with `(i+1) * rise` cumulative height and `n` steps where `n = H / rise`, the top surface of the last step lands exactly at `z = sz + H` (the underside of the upper floor slab) — verify this aligns before cutting the opening
- **get_objects on large documents**: can time out or exceed token limits; use `execute_code` + targeted queries instead
