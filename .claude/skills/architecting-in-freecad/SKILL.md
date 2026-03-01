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

Before starting, always read:

- **`reference/arch-api-reference.md`** — Arch.make* function signatures, key properties, and code patterns
- **`.claude/context/freecad-arch-guide.md`** — Practical Arch modeling patterns (levels, walls, openings, roof, sections, naming)

Read `reference/architectural-standards.md` for generic/international defaults (room sizes, door widths, stair geometry). Note: values are generic — override with BBR when designing for Sweden (see below).

### Swedish projects (BBR)

Do **not** pre-load all BBR files — they add ~40KB to context unnecessarily. Instead:

1. Read `.claude/context/bbr-reference.md` — it's a one-page index with a quick-reference table
2. When you reach a design phase where a specific regulation matters, read only that topic file:

| When you need... | Read |
|-----------------|------|
| Ceiling heights, room sizes | `.claude/context/arch-swe-room-dimensions-reference.md` |
| Ramps, door widths, accessibility | `.claude/context/arch-swe-accessibility-reference.md` |
| Fire classes, building classes (Br/Vk) | `.claude/context/arch-swe-fire-safety-reference.md` |
| Stairwells (Tr1/Tr2), evacuation | `.claude/context/arch-swe-stairs-ramps-reference.md` |
| Daylight (dagsljusfaktor), egress | `.claude/context/arch-swe-doors-windows-daylight-reference.md` |
| Structural safety classes (SK1–SK3) | `.claude/context/arch-swe-structural-reference.md` |
| Parking (HC spaces) | `.claude/context/arch-swe-parking-reference.md` |

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

## Design Knowledge Store

Before any FreeCAD work, check `.designs/<doc-name>/`:

- **Exists** → Read `README.md`, `objects.md`, `tasks.md` to restore prior context, decisions, and known object structure.
- **Doesn't exist** → Create it after Phase 1. Capture the agreed design brief in `README.md`, an initial object catalog in `objects.md`, and the build plan as Active tasks in `tasks.md`. See `.claude/context/designs-store.md` for templates.

Update `objects.md` as objects are created during the session. At session end, move completed tasks to Done, append decisions/discoveries to `README.md`, and save any useful scripts to `scripts/`.

---

## Phase 2 — Levels & Building Setup

### Define levels first

Levels are the backbone of architectural design. Define them as a Python dict at the top of every `execute_code` block. **Never hardcode a z-coordinate.** Always reference `levels["Ground"]`, `levels["First"]`, etc.

See `freecad-arch-guide.md` > "Level Definitions" for the standard pattern.

### Create the BIM hierarchy

Create Site → Building → Floor(s) using `Arch.makeSite()`, `Arch.makeBuilding()`, `Arch.makeFloor()`. Nest them: elements → floor → building → site.

See `freecad-arch-guide.md` > "BIM Hierarchy" and `reference/arch-api-reference.md` > "Hierarchy" for function signatures.

> **Checkpoint**: Show the hierarchy. Confirm levels and floor-to-floor heights before creating geometry.

---

## Phase 3 — Structural Layout

Create the structural skeleton: slabs and load-bearing walls (or columns for frame structures).

- **Slabs**: Use `Arch.makeStructure()` — see `arch-api-reference.md` > "Structures"
- **Walls**: Use `Arch.makeWall()` with or without Draft baselines — see `freecad-arch-guide.md` > "Wall Creation Patterns"

**Batch all walls for a floor in one `execute_code` block.** Name them by floor and orientation: `Wall_GF_South`, `Wall_GF_North`, `Wall_1F_East`, etc.

> **Checkpoint**: Screenshot after all walls for a floor. Verify wall positions, heights, and that they sit at the correct level.

---

## Phase 4 — Enclosure & Partitions

### Interior partitions

Interior walls are typically thinner (100-150mm). Define wall types at the top of your code:

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

Use `Arch.makeWindowPreset()` for windows and doors. The `Hosts` property creates automatic wall cuts — no manual `Part::Cut` needed.

See `freecad-arch-guide.md` > "Openings" and `arch-api-reference.md` > "Windows & Doors" for function signatures and placement rules.

**Window/door placement rule**: The position is relative to the wall's baseline.

> **Checkpoint**: Show elevation views (`get_view("Front")`, `get_view("Right")`) to verify opening positions and sizes.

---

## Phase 6 — Vertical Circulation

### Stairs

Use `Arch.makeStairs()` — see `arch-api-reference.md` > "Stairs" for parameters.

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

If stairs pass through a floor slab, create a slab opening using `Part::Box` + `Part::Cut` (there is no Arch-native slab opening tool). See `freecad-arch-guide.md` > "Boolean Operations" for the pattern.

> **Checkpoint**: Section view to verify stair connects both levels without clipping the slab.

---

## Phase 7 — Roof

- **Flat roof**: Use `Arch.makeStructure()` as a roof slab
- **Pitched roof**: Create a closed wire at roof level, then `Arch.makeRoof()` with `angles` and `overhang` parameters. Do not pre-bake overhang into wire coordinates.

See `arch-api-reference.md` > "Roofs" for the function signature.

> **Checkpoint**: Isometric view to verify roof sits correctly on walls.

---

## Phase 8 — Verification & Documentation

### Multi-view verification

Capture all standard views: `["Isometric", "Top", "Front", "Right"]` using `get_view(view_name, 400, 400)`.

| View | Check |
|------|-------|
| Top (plan) | Room layout matches program, wall thicknesses correct, openings positioned |
| Front (elevation) | Floor-to-floor heights, window sill heights, roof line |
| Right (elevation) | Building depth, stair position if visible |
| Isometric | Overall massing, nothing floating or misaligned |

### Section planes and dimensional checks

See `freecad-arch-guide.md` > "Sections" for section plane creation and `freecad-drawings.md` for TechDraw pipeline.

> **Checkpoint**: "Here's the building from four views. Does the design match your intent? Any rooms to resize, openings to adjust, or elements to add?"

---

## Phase 9 — Refinement & Wrap-Up

### Final deliverables

1. Final isometric screenshot at presentation quality
2. Object inventory with areas/volumes if relevant
3. List of deferred items (details not modeled, services not routed)
4. Ask: "Save and export, or keep refining?"

### Update `.designs/<doc-name>/`

- **`objects.md`** — reflect all objects created, renamed, or removed this session
- **`tasks.md`** — move completed tasks to Done (date-stamped); add deferred items as Active
- **`README.md`** — append design decisions (structural system, level heights, materials chosen) and open questions
- **`scripts/`** — save reusable `execute_code` snippets (e.g., batch wall creation, level verification)

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
