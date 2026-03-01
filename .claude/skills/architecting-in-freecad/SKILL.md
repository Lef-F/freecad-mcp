---
name: architecting-in-freecad
description: Guides Claude through expert-level architectural design sessions in FreeCAD — from design brief through BIM hierarchy, wall systems, openings, circulation, and construction documentation using the Arch/BIM workbench.
---

# Architecting in FreeCAD

## When to Use

- The user asks to design a building, house, room layout, or architectural structure
- The user wants to create walls, windows, doors, roofs, stairs, or floors as architectural elements
- The user mentions BIM, IFC, or architectural design workflows
- A design session needs architectural domain expertise (not just generic shape-making)

**Not this skill**: For mechanical parts, brackets, assemblies, or non-building geometry, use `modeling-in-freecad` instead.

---

## Principles

This skill extends `modeling-in-freecad` with architectural domain expertise. All base principles (turn-based collaboration, Python for calculations, human checkpoints, autonomous verification) still apply. Read `modeling-in-freecad` if you haven't.

**What makes architecture different from generic modeling:**

1. **Semantic objects, not shapes** — A wall is not a `Part::Box`. Use `Arch.makeWall()` to get parametric height, width, alignment, IFC type, and multi-material support.
2. **Hierarchy matters** — Buildings have levels. Objects belong to floors. Floors belong to buildings. This hierarchy drives IFC export, schedules, and section generation.
3. **Design intent drives geometry** — Architects think in rooms, circulation, and spatial relationships, not coordinates. Translate intent into geometry, not the reverse.
4. **Levels are the backbone** — Every z-coordinate derives from a named level. Never hardcode z-values.
5. **Openings are first-class** — Windows and doors are not boolean cuts. They are `Arch.makeWindow()` objects that automatically cut their host wall.

**Use `execute_code` for all Arch operations.** The `create_object` MCP tool uses `doc.addObject()` which doesn't work for Arch objects. Arch objects require factory functions (`Arch.makeWall()`, `Arch.makeWindow()`, etc.) that are only available through `execute_code`.

---

## Reference Files

Before starting, review these reference files in this skill's `reference/` directory:

- **`arch-api-reference.md`** — Arch.make* function signatures, key properties, and code patterns
- **`architectural-standards.md`** — Standard dimensions, structural rules of thumb, accessibility requirements

Also review `.claude/context/freecad-arch-guide.md` for practical Arch modeling patterns.

---

## Phase 1 — Design Brief

Before touching FreeCAD, establish the architectural program.

**Capture from the user:**

1. **Building type** — Residential, commercial, mixed-use, educational, etc.
2. **Program** — What rooms/spaces are needed? Approximate areas?
3. **Number of levels** — How many stories? Below grade?
4. **Key dimensions** — Site footprint, floor-to-floor height, or let Claude propose defaults
5. **Level of detail** — Massing study, schematic design, or detailed with openings?
6. **Style/constraints** — Flat roof vs pitched? Load-bearing walls vs frame? Any code requirements?

**Propose a design strategy** before proceeding:

> "I'll create a 2-story residential building:
> - Ground floor: living room (5×4m), kitchen (4×3m), entry hall, staircase
> - Upper floor: 2 bedrooms (4×3.5m each), bathroom (2.5×2m), landing
> - 200mm exterior walls, 150mm interior partitions, 200mm slabs
> - Floor-to-floor: 3000mm (2800mm clear + 200mm slab)
> - Flat roof with parapet
>
> Shall I proceed with this program?"

---

## Phase 2 — Levels & Building Setup

### Define levels first

Levels are the backbone of architectural design. Define them as a Python dict at the top of every `execute_code` block:

```python
levels = {
    "Foundation":  -200,
    "Ground":         0,
    "First Floor": 3000,
    "Roof":        6000,
}
floor_to_floor = 3000
slab_t = 200
wall_h = floor_to_floor - slab_t  # 2800mm clear
```

**Never hardcode a z-coordinate.** Always reference `levels["Ground"]`, `levels["First Floor"]`, etc.

### Create the BIM hierarchy

```python
import FreeCAD, Arch

doc = FreeCAD.newDocument("MyBuilding")

# Create organizational hierarchy
site = Arch.makeSite()
site.Label = "Site"

building = Arch.makeBuilding()
building.Label = "Building"

ground_floor = Arch.makeFloor()
ground_floor.Label = "Ground Floor"
ground_floor.Height = floor_to_floor

first_floor = Arch.makeFloor()
first_floor.Label = "First Floor"
first_floor.Height = floor_to_floor
first_floor.Placement.Base.z = levels["First Floor"]

# Nest: elements → floor → building → site
building.Group = [ground_floor, first_floor]
site.Group = [building]

doc.recompute()
print("BIM hierarchy created")
```

> **Checkpoint**: Show the hierarchy. Confirm levels and floor-to-floor heights before creating geometry.

---

## Phase 3 — Structural Layout

Create the structural skeleton: slabs and load-bearing walls (or columns for frame structures).

### Floor slabs

Use `Arch.makeStructure()` for slabs:

```python
# Ground floor slab
slab_gf = Arch.makeStructure(length=L, width=W, height=slab_t)
slab_gf.Label = "Slab_Ground"
slab_gf.Placement.Base = FreeCAD.Vector(0, 0, levels["Ground"] - slab_t)
ground_floor.addObject(slab_gf)
```

### Load-bearing walls with baselines

For precise wall placement, draw Draft baselines first:

```python
import Draft

# South wall baseline
p1 = FreeCAD.Vector(0, 0, levels["Ground"])
p2 = FreeCAD.Vector(L, 0, levels["Ground"])
baseline_south = Draft.make_line(p1, p2)

wall_south = Arch.makeWall(baseline_south, height=wall_h, width=200)
wall_south.Label = "Wall_GF_South"
wall_south.Align = "Right"  # wall grows inward from baseline
ground_floor.addObject(wall_south)
```

### Or walls without baselines (simpler)

```python
wall = Arch.makeWall(length=5000, width=200, height=wall_h)
wall.Label = "Wall_GF_South"
wall.Placement.Base = FreeCAD.Vector(0, 0, levels["Ground"])
ground_floor.addObject(wall)
```

**Batch all walls for a floor in one `execute_code` block.** Name them by floor and orientation: `Wall_GF_South`, `Wall_GF_North`, `Wall_1F_East`, etc.

> **Checkpoint**: Screenshot after all walls for a floor. Verify wall positions, heights, and that they sit at the correct level.

---

## Phase 4 — Enclosure & Partitions

### Exterior walls

Already created in Phase 3 if load-bearing. For frame structures, add non-structural exterior walls now.

### Interior partitions

Interior walls are typically thinner (100-150mm):

```python
partition = Arch.makeWall(length=3000, width=150, height=wall_h)
partition.Label = "Partition_GF_Kitchen"
partition.Placement.Base = FreeCAD.Vector(5000, 0, levels["Ground"])
partition.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 90)
ground_floor.addObject(partition)
```

### Wall types convention

Define wall types at the top of your code:

```python
wall_types = {
    "exterior":  {"width": 200, "label_prefix": "ExtWall"},
    "interior":  {"width": 150, "label_prefix": "IntWall"},
    "partition": {"width": 100, "label_prefix": "Partition"},
}
```

> **Checkpoint**: Plan view screenshot (`get_view("Top", 400, 400)`) to verify room layout matches the program.

---

## Phase 5 — Openings

### Windows

`Arch.makeWindow()` with a preset type is the simplest approach:

```python
# Create a window and insert it into a wall
window = Arch.makeWindowPreset(
    "Fixed",           # type: Fixed, Open 1-pane, Open 2-pane, Simple door, Glass door, etc.
    width=1200,
    height=1400,
    h1=100, h2=100, h3=100,   # frame dimensions
    w1=100, w2=100,
    o1=0, o2=0
)
window.Label = "Window_GF_South_01"

# Position the window on the wall
window.Placement.Base = FreeCAD.Vector(1000, 0, levels["Ground"] + 800)

# Attach to host wall (automatic boolean cut)
window.Hosts = [wall_south]
```

### Doors

Doors use the same `makeWindowPreset` with door types:

```python
door = Arch.makeWindowPreset(
    "Simple door",
    width=900, height=2100,
    h1=100, h2=100, h3=100,
    w1=100, w2=100,
    o1=0, o2=0
)
door.Label = "Door_GF_Entry"
door.Placement.Base = FreeCAD.Vector(2000, 0, levels["Ground"])
door.Hosts = [wall_south]
```

**Window/door placement rule**: The position is relative to the wall's baseline. The `Hosts` property creates the automatic cut — no manual `Part::Cut` needed.

> **Checkpoint**: Show elevation views (`get_view("Front")`, `get_view("Right")`) to verify opening positions and sizes.

---

## Phase 6 — Vertical Circulation

### Stairs

```python
stairs = Arch.makeStairs(height=floor_to_floor, width=1200, steps=16)
stairs.Label = "Stairs_GF_to_1F"
stairs.Placement.Base = FreeCAD.Vector(stair_x, stair_y, levels["Ground"])
ground_floor.addObject(stairs)
```

Verify the stair geometry:
- **Rise**: `floor_to_floor / steps` — should be 150-200mm
- **Going (run)**: typically 250-300mm
- **Rule of thumb**: `2 × rise + going = 600-650mm` (comfort formula)

Before creating stairs, verify locally:
```bash
python3 -c "
h, n = 3000, 16
rise = h / n
run = 280
print(f'rise={rise:.1f}mm  2*rise+run={2*rise+run:.0f}mm')
print(f'footprint={n*run:.0f}mm x 1200mm')
"
```

### Slab openings for stairs

If stairs pass through a floor slab, create a slab opening. This uses `Part::Box` + `Part::Cut` (there is no Arch-native slab opening tool):

```python
# Cut the opening in the upper floor slab
hole = doc.addObject("Part::Box", "StairOpening_1F")
hole.Length = stair_footprint + 100  # 50mm clearance each side
hole.Width = 1200 + 100
hole.Height = slab_t + 10
hole.Placement.Base = FreeCAD.Vector(
    stair_x - 50, stair_y - 50,
    levels["First Floor"] - 5
)
cut = doc.addObject("Part::Cut", "Slab_1F_Cut")
cut.Base = slab_1f
cut.Tool = hole
hole.ViewObject.Visibility = False
slab_1f.ViewObject.Visibility = False
```

> **Checkpoint**: Section view to verify stair connects both levels without clipping the slab.

---

## Phase 7 — Roof

### Flat roof

```python
roof_slab = Arch.makeStructure(length=L, width=W, height=slab_t)
roof_slab.Label = "Slab_Roof"
roof_slab.Placement.Base = FreeCAD.Vector(0, 0, levels["Roof"])
building.addObject(roof_slab)  # or top floor
```

### Pitched roof

Create a closed wire profile, then use `Arch.makeRoof()`:

```python
# Roof profile (closed wire following building perimeter)
pts = [
    FreeCAD.Vector(0, 0, levels["Roof"]),
    FreeCAD.Vector(L, 0, levels["Roof"]),
    FreeCAD.Vector(L, W, levels["Roof"]),
    FreeCAD.Vector(0, W, levels["Roof"]),
]
wire = Draft.make_wire(pts, closed=True)

roof = Arch.makeRoof(wire, angles=[35, 35, 35, 35])
roof.Label = "Roof"
building.addObject(roof)
```

> **Checkpoint**: Isometric view to verify roof sits correctly on walls.

---

## Phase 8 — Verification & Documentation

### Multi-view verification

Capture all standard views to check the design:

```python
# Run this check sequence
views = ["Isometric", "Top", "Front", "Right"]
```

For each view, use `get_view(view_name, 400, 400)`.

**What to verify:**

| View | Check |
|------|-------|
| Top (plan) | Room layout matches program, wall thicknesses correct, openings positioned |
| Front (elevation) | Floor-to-floor heights, window sill heights, roof line |
| Right (elevation) | Building depth, stair position if visible |
| Isometric | Overall massing, nothing floating or misaligned |

### Section planes (advanced)

For construction-quality sections:

```python
section = Arch.makeSectionPlane()
section.Label = "Section_A"
section.Placement.Base = FreeCAD.Vector(L/2, 0, 0)
section.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 90)
```

### Dimensional checks

Run a programmatic verification against the brief:

```python
# Verify all rooms meet minimum area requirements
for obj in doc.Objects:
    if hasattr(obj, "IfcType") and obj.IfcType == "Space":
        area = obj.Shape.Area / 1e6  # mm² to m²
        print(f"{obj.Label}: {area:.1f} m²")
```

> **Checkpoint**: "Here's the building from four views. Does the design match your intent? Any rooms to resize, openings to adjust, or elements to add?"

---

## Phase 9 — Refinement & Wrap-Up

### Materials (optional)

```python
concrete = Arch.makeMaterial("Concrete")
concrete.Color = (0.7, 0.7, 0.7, 1.0)

brick = Arch.makeMaterial("Brick")
brick.Color = (0.8, 0.4, 0.2, 1.0)

# Assign to walls
wall_south.Material = brick
slab_gf.Material = concrete
```

### Visibility for presentation

```python
# Hide south and east walls for interior view
for name in ["Wall_GF_South", "Wall_GF_East"]:
    obj = doc.getObject(name)
    if obj:
        obj.ViewObject.Visibility = False
```

### Final deliverables

1. Final isometric screenshot at presentation quality
2. Object inventory with areas/volumes if relevant
3. List of deferred items (details not modeled, services not routed)
4. Ask: "Save and export, or keep refining?"

---

## Architectural Checkpoints (beyond base modeling)

Stop and ask the user when:

- **Room sizes** haven't been confirmed against the program
- **Window sill height** matters (800mm residential vs 900mm commercial vs floor-to-ceiling)
- **Stair geometry** involves a design choice (straight run vs L-shaped vs U-shaped)
- **Structural system** isn't clear (load-bearing walls vs frame + infill)
- **Roof type** hasn't been decided (flat, gable, hip, shed)
- **Floor plan** has multiple valid arrangements (propose 2 options with plan sketches)
- **Code requirements** may apply (egress width, accessibility, fire separation)

---

## Common Architectural Mistakes

- **Walls at wrong level** — Every wall's z must derive from `levels[...]`, not a hardcoded number
- **Forgetting slab thickness in stacking** — Floor-to-floor includes slab; clear height = floor-to-floor - slab_t
- **Window too close to corner** — Minimum 200-300mm from wall corner to window edge (structural)
- **Stair doesn't fit** — Calculate footprint (`steps × run`) before placing; verify it fits the allocated space
- **Interior doors hitting walls** — Door swing radius (= door width) needs clear floor space
- **Missing floor hierarchy** — Objects not added to their Floor group won't appear in IFC export correctly
- **Orientation confusion** — Establish north direction early; label walls by compass direction

---

## Verification (end of session)

- [ ] BIM hierarchy exists: Site → Building → Floor(s)
- [ ] All objects assigned to correct Floor groups
- [ ] Levels dict matches actual object z-positions
- [ ] Room areas meet program requirements (spot-check 2-3 rooms)
- [ ] Window/door positions checked in elevation views
- [ ] Stair rise verified: 150-200mm, comfort formula satisfied
- [ ] `doc.recompute()` called after last change
- [ ] User confirmed the design matches their intent
