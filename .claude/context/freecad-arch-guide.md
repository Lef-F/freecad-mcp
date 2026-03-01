# FreeCAD Arch/BIM Modeling Guide

Practical patterns for building architectural models via MCP. Complements `freecad-modeling-guide.md` (generic CAD) with architecture-specific workflow and domain knowledge.

---

## Why Arch Objects, Not Part::Box

The `modeling-in-freecad` skill uses `Part::Box` for walls and slabs. This works for rough massing but lacks architectural semantics. Use Arch objects instead when:

- You need IFC-compliant export
- Walls should auto-join at corners
- Windows/doors should auto-cut their host wall
- Multi-layer wall construction is needed
- You want a proper BIM hierarchy (Site > Building > Floor)

**Trade-off**: Arch objects require `execute_code` (the `create_object` tool can't create them). This means slightly more code but dramatically better architectural models.

---

## execute_code Is Your Primary Tool

All Arch operations go through `execute_code`. Standard pattern:

```python
import FreeCAD, Draft, Arch

doc = FreeCAD.getDocument("MyDoc")  # or FreeCAD.newDocument("MyDoc")

# ... create objects ...

doc.recompute()
print("Done")
```

Always end with `doc.recompute()` and `print("Done")`.

---

## Level Definition Pattern

**Every architectural project starts with levels.** Define them once, reference everywhere:

```python
# Level definitions — the backbone of the building
levels = {
    "Foundation":  -200,
    "Ground":         0,
    "First":       3000,
    "Second":      6000,
    "Roof":        9000,
}

# Derived constants
floor_to_floor = 3000
slab_t = 200
wall_h = floor_to_floor - slab_t  # 2800mm clear height

# Wall type definitions
ext_w = 200   # exterior wall thickness
int_w = 150   # interior partition thickness
```

**Never hardcode z-coordinates.** Always write `levels["Ground"]`, not `0`. Always write `levels["First"]`, not `3000`. The expression documents intent and survives parameter changes.

---

## Wall Creation Patterns

### Pattern 1: Walls from Draft baselines (most control)

```python
# Draw the building perimeter as Draft lines
p = [
    FreeCAD.Vector(0, 0, 0),
    FreeCAD.Vector(8000, 0, 0),
    FreeCAD.Vector(8000, 6000, 0),
    FreeCAD.Vector(0, 6000, 0),
]

lines = []
for i in range(len(p)):
    line = Draft.make_line(p[i], p[(i+1) % len(p)])
    lines.append(line)

# Create walls from baselines
labels = ["South", "East", "North", "West"]
walls = []
for line, label in zip(lines, labels):
    wall = Arch.makeWall(line, width=ext_w, height=wall_h)
    wall.Label = f"Wall_GF_{label}"
    wall.Align = "Right"  # wall grows inward
    walls.append(wall)
```

**Align options**: `"Center"` (default), `"Left"`, `"Right"`. Controls which side of the baseline the wall material grows toward.

### Pattern 2: Walls without baselines (simpler)

```python
wall = Arch.makeWall(length=5000, width=ext_w, height=wall_h)
wall.Label = "Wall_GF_South"
wall.Placement.Base = FreeCAD.Vector(0, 0, levels["Ground"])
```

Less flexible but good for quick placement. The wall grows along the X axis from its Placement.

### Pattern 3: Interior partitions

```python
partition = Arch.makeWall(length=3000, width=int_w, height=wall_h)
partition.Label = "Partition_GF_Kitchen"
partition.Placement.Base = FreeCAD.Vector(4000, 0, levels["Ground"])
# Rotate 90° to run along Y axis
partition.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 90)
```

---

## Window & Door Insertion

### Using presets (recommended)

```python
# Window preset types:
# "Fixed", "Open 1-pane", "Open 2-pane", "Sash 2-pane",
# "Sliding 2-pane", "Simple door", "Glass door", "Sliding 4-pane"

win = Arch.makeWindowPreset(
    "Fixed",          # type
    1200, 1400,       # width, height
    100, 100, 100,    # h1, h2, h3 (frame dims)
    100, 100,         # w1, w2 (frame dims)
    0, 0              # o1, o2 (offsets)
)
win.Label = "Win_GF_S_01"
win.Placement.Base = FreeCAD.Vector(1500, 0, levels["Ground"] + 800)

# Attach to host wall — creates automatic boolean cut
win.Hosts = [wall_south]
```

### Doors

```python
door = Arch.makeWindowPreset(
    "Simple door",    # or "Glass door"
    900, 2100,
    100, 100, 100,
    100, 100,
    0, 0
)
door.Label = "Door_GF_Entry"
door.Placement.Base = FreeCAD.Vector(3000, 0, levels["Ground"])
door.Hosts = [wall_south]
```

### Using addComponents (alternative attachment method)

```python
Arch.addComponents(win, wall_south)
```

This is equivalent to setting `win.Hosts`.

### Standard sill heights

| Type | Sill Height | Notes |
|------|-------------|-------|
| Living room window | 800–900mm | Standard residential |
| Kitchen window | 900–1000mm | Above counter |
| Bedroom window | 800–900mm | Egress: max 1120mm sill |
| Bathroom window | 1400–1600mm | Privacy |
| Floor-to-ceiling | 0mm | Full height glazing |
| Door | 0mm | Sits on floor |

---

## Building Hierarchy

Always create the full BIM hierarchy for IFC compatibility:

```python
# 1. Create containers (top-down)
site = Arch.makeSite()
site.Label = "Site"

building = Arch.makeBuilding()
building.Label = "Building"

gf = Arch.makeFloor()
gf.Label = "Ground Floor"
gf.Height = floor_to_floor

ff = Arch.makeFloor()
ff.Label = "First Floor"
ff.Height = floor_to_floor
ff.Placement.Base.z = levels["First"]

# 2. Add objects to floors
gf.addObject(wall_gf_south)
gf.addObject(wall_gf_north)
# ... all ground floor objects

# 3. Nest hierarchy
building.Group = [gf, ff]
site.Group = [building]
```

**Floor.Height** property: If a wall inside this floor has Height=0, it inherits the floor's Height value.

---

## Structural Elements

### Floor slabs

```python
slab = Arch.makeStructure(length=L, width=W, height=slab_t)
slab.Label = "Slab_Ground"
slab.IfcType = "Slab"
slab.Placement.Base = FreeCAD.Vector(0, 0, levels["Ground"] - slab_t)
```

### Columns

```python
col = Arch.makeStructure(length=300, width=300, height=wall_h)
col.Label = "Col_GF_01"
col.IfcType = "Column"
col.Placement.Base = FreeCAD.Vector(4000, 3000, levels["Ground"])
```

### Beams

```python
beam = Arch.makeStructure(length=6000, width=200, height=400)
beam.Label = "Beam_GF_01"
beam.IfcType = "Beam"
beam.Placement.Base = FreeCAD.Vector(0, 3000, levels["First"] - 400)
```

---

## Roof Patterns

### Flat roof

Use `Arch.makeStructure()` as a slab at the roof level.

### Pitched roof (from closed wire)

```python
# The wire follows the building wall footprint (not including overhang).
# The overhang parameter adds the eave projection.
pts = [
    FreeCAD.Vector(0, 0, levels["Roof"]),
    FreeCAD.Vector(L, 0, levels["Roof"]),
    FreeCAD.Vector(L, W, levels["Roof"]),
    FreeCAD.Vector(0, W, levels["Roof"]),
]
wire = Draft.make_wire(pts, closed=True)

# Gable roof (two pitched sides, two vertical gable ends)
# angles: pitch per edge; 90° = vertical gable end (no pitch)
# overhang: eave projection in mm (applied by makeRoof, not in wire coords)
roof = Arch.makeRoof(wire, angles=[35, 90, 35, 90], overhang=[500, 0, 500, 0])
roof.Label = "Roof"
```

**Angle = 90°** means a vertical gable end (no pitch on that edge).
**overhang** is the horizontal projection of the eave beyond the wire — pass `0` for gable ends.

---

## Stair Verification Pattern

Before creating stairs, always verify the geometry locally:

```bash
python3 -c "
h = 3000      # floor-to-floor
n = 16        # number of steps
rise = h / n
run = 280     # tread depth
comfort = 2 * rise + run
print(f'Rise: {rise:.1f}mm (max 190mm residential)')
print(f'Comfort: {comfort:.0f}mm (target 600-650)')
print(f'Footprint: {n * run}mm = {n * run / 1000:.1f}m')
print(f'Total height check: {n} x {rise:.1f} = {n * rise:.1f}mm')
"
```

Then create:

```python
stairs = Arch.makeStairs(height=floor_to_floor, width=1200, steps=16)
stairs.Label = "Stairs_GF_to_FF"
stairs.Placement.Base = FreeCAD.Vector(stair_x, stair_y, levels["Ground"])
gf.addObject(stairs)
```

---

## Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Exterior wall | `Wall_{level}_{direction}` | `Wall_GF_South` |
| Interior partition | `Partition_{level}_{room}` | `Partition_GF_Kitchen` |
| Window | `Win_{level}_{wall}_{nn}` | `Win_GF_S_01` |
| Door | `Door_{level}_{name}` | `Door_GF_Entry` |
| Slab | `Slab_{level}` | `Slab_Ground` |
| Column | `Col_{level}_{nn}` | `Col_GF_01` |
| Beam | `Beam_{level}_{nn}` | `Beam_GF_01` |
| Stairs | `Stairs_{from}_to_{to}` | `Stairs_GF_to_FF` |
| Floor container | Full name | `Ground Floor` |

Level abbreviations: `GF` = Ground Floor, `FF` = First Floor, `SF` = Second Floor, `RF` = Roof.

---

## Multi-View Verification

After completing a floor or major building phase, capture these views:

```
get_view("Top", 400, 400)         # Plan view — room layout, wall alignment
get_view("Front", 400, 400)       # South elevation — openings, floor lines
get_view("Right", 400, 400)       # East elevation — building depth
get_view("Isometric", 400, 400)   # 3D overview — massing, proportions
```

**What to check per view**:

| View | Verify |
|------|--------|
| Top | Room sizes match brief, walls continuous, partitions placed |
| Front | Window/door positions, sill heights, floor-to-floor |
| Right | Building depth, stair opening if visible |
| Isometric | Overall massing, roof shape, nothing floating |

---

## Visibility for Interior Views

Hide exterior walls on open sides to see interior:

```python
# Hide south and east walls for isometric interior view
for label in ["Wall_GF_South", "Wall_GF_East", "Wall_FF_South", "Wall_FF_East"]:
    obj = doc.getObjectsByLabel(label)
    if obj:
        obj[0].ViewObject.Visibility = False
```

Restore with `Visibility = True`.

---

## Common Pitfalls

1. **Walls not joining**: Walls auto-join only when they have the same Width, Height, and Align properties. Verify these match for walls that should connect at corners.

2. **Window in wrong position**: Window Placement is relative to the wall's local coordinate system. Verify visually with an elevation view.

3. **Floor hierarchy broken**: Objects not added to their Floor group don't show in the correct IFC storey. Always call `floor.addObject(wall)`.

4. **Levels don't match placement**: If `levels["First"] = 3000` but a wall is at z=3200, something's wrong. Always derive z from the levels dict.

5. **Recompute ordering**: Complex Arch objects (especially roofs and stairs) may need multiple recomputes. If geometry looks wrong, try `doc.recompute()` twice.

6. **Draft baselines visible**: Hide Draft lines after creating walls from them: `line.ViewObject.Visibility = False`.
