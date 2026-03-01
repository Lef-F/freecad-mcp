# FreeCAD Arch/BIM Python API Reference

Quick reference for creating architectural objects via `execute_code`. All functions require `import Arch` (and often `import Draft, FreeCAD`).

> **Important**: Arch objects cannot be created with `doc.addObject()`. Always use the `Arch.make*()` factory functions below via `execute_code`.

---

## Object Creation Functions

### Walls

```python
Arch.makeWall(baseobj=None, height=None, length=None, width=None,
              align=None, face=None, name=None)
```

> Note: `align=None` defaults to `"Center"` in the wall object's enum property.

| Param | Type | Notes |
|-------|------|-------|
| `baseobj` | Draft line/wire/sketch/face/solid | Wall follows this shape. If None, creates a straight wall using `length`. |
| `length` | float (mm) | Only used when no `baseobj`. |
| `width` | float (mm) | Wall thickness. |
| `height` | float (mm) | Wall height. If 0 and wall is in a Floor, inherits Floor.Height. |
| `align` | `"Center"` / `"Left"` / `"Right"` | Which side of baseline the wall grows toward. |

**Key properties**: `Height`, `Width`, `Length`, `Align`, `Offset`, `Area` (read-only), `MakeBlocks`, `Normal`.

**Behavior by baseobj type**:
- No baseobj → uses `length`, `width`, `height`
- Linear 2D (line, wire, arc) → Length is read-only; width/height/align work
- Flat face → only Height works
- Solid → uses solid shape directly; dimensions ignored

### Windows & Doors

```python
Arch.makeWindowPreset(windowtype, width, height,
                      h1, h2, h3, w1, w2, o1, o2,
                      placement=None)
```

| Param | Type | Notes |
|-------|------|-------|
| `windowtype` | str | `"Fixed"`, `"Open 1-pane"`, `"Open 2-pane"`, `"Sash 2-pane"`, `"Sliding 2-pane"`, `"Simple door"`, `"Glass door"`, `"Sliding 4-pane"`, `"Awning"`, `"Opening only"` |
| `width` | float | Total window width (mm) |
| `height` | float | Total window height (mm) |
| `h1, h2, h3` | float | Frame height divisions (mm) |
| `w1, w2` | float | Frame width divisions (mm) |
| `o1, o2` | float | Offset values (mm) |

**Attach to wall**: Set `window.Hosts = [wall_object]` — the wall gets an automatic boolean cut.

**Position**: Set `window.Placement.Base` relative to the wall's baseline origin.

```python
Arch.makeWindow(baseobj=None, width=None, height=None,
                parts=None, name="Window")
```

Use `makeWindow` with a closed Draft Wire or Sketch for custom window shapes.

### Structures (Beams, Columns, Slabs)

```python
Arch.makeStructure(baseobj=None, length=None, width=None,
                   height=None, name="Structure")
```

Auto-sets `IfcType` based on dimensions (Length vs Height only):
- `Height > Length` → `IfcType = "Column"`
- `Length > Height` → `IfcType = "Beam"`
- No baseobj and no dimensions → `IfcType = "Building Element Proxy"`

**Slab is not auto-detected.** Set `IfcType` explicitly for slabs and to override auto-detection:

```python
structure.IfcType = "Slab"    # or "Column", "Beam"
```

### Floors / Levels

```python
Arch.makeFloor(objectslist=None, baseobj=None, name=None)
```

Creates a `BuildingPart` container with `IfcType = "Building Storey"`. Set `floor.Height` for the storey height (walls inside with `height=0` inherit this). Set `floor.Placement.Base.z` to position the level. Add objects with `floor.addObject(obj)` or `floor.Group = [obj1, obj2, ...]`.

### Buildings

```python
Arch.makeBuilding(objectslist=None, baseobj=None, name=None)
```

Creates a `BuildingPart` container with `IfcType = "Building"`. Top-level container for floors. Set `building.Group = [floor1, floor2, ...]`.

### Sites

```python
Arch.makeSite(objectslist=None, baseobj=None, name="Site")
```

Top-level container for buildings. Set `site.Group = [building]`.

### Stairs

```python
Arch.makeStairs(baseobj=None, length=None, width=None,
                height=None, steps=None, name="Stairs")
```

| Param | Type | Notes |
|-------|------|-------|
| `height` | float | Total rise (mm) — typically floor-to-floor |
| `width` | float | Stair width (mm) |
| `steps` | int | Number of steps |
| `length` | float | Total run/going (mm) |

**Properties**: `NumberOfSteps`, `TreadDepth`, `RiserHeight`, `Width`, `Height`, `Landings`, `Winders`.

### Roofs

```python
Arch.makeRoof(baseobj=None, facenr=0,
              angles=[45.], run=[250.],
              idrel=[-1], thickness=[50.],
              overhang=[100.], name="Roof")
```

Requires a closed wire (Draft Wire or Sketch) following the **wall footprint** at roof level. The `overhang` parameter adds the eave projection beyond the wire. Each list parameter corresponds to one segment of the wire — lists are auto-extended to match segment count.

| Param | Type | Notes |
|-------|------|-------|
| `angles` | list[float] | Pitch angle per segment (degrees). 90° = vertical gable end. |
| `run` | list[float] | Horizontal run per segment (mm). Default 250mm. |
| `idrel` | list[int] | Relative index for ridge calculation. Default -1 (auto). |
| `thickness` | list[float] | Roof thickness per segment (mm). Default 50mm. |
| `overhang` | list[float] | Eave overhang per segment (mm). Default 100mm. Use 0 for gable ends. |

### Other Objects

```python
Arch.makeSectionPlane()              # Section cutting plane
Arch.makeSpace(objects=None)         # Room/space volume (pass a solid or list of face refs)
Arch.makeMaterial(name="Material")   # Material definition
Arch.makeMultiMaterial(name="Multi") # Multi-layer material
Arch.makePipe(baseobj=None, diameter=0, length=0)
Arch.makeEquipment(baseobj=None)     # Furniture/fixtures
Arch.makePanel(baseobj=None, length=0, width=0, thickness=0)
Arch.makeBuildingPart(objectslist)    # Group elements
```

---

## BIM Hierarchy Pattern

```
Site
 └── Building
      ├── Ground Floor (Arch::Floor, z=0, Height=3000)
      │    ├── Wall_GF_South
      │    ├── Wall_GF_North
      │    ├── Wall_GF_East
      │    ├── Wall_GF_West
      │    ├── Window_GF_01
      │    ├── Door_GF_Entry
      │    └── Slab_Ground (Arch::Structure)
      └── First Floor (Arch::Floor, z=3000, Height=3000)
           ├── Wall_1F_South
           ├── ...
           └── Slab_First (Arch::Structure)
```

Add objects to floors: `floor.addObject(wall)` or set `floor.Group = [wall1, wall2, ...]`.

---

## Draft Functions for Baselines

Architectural objects often need Draft geometry as their base:

```python
import Draft

# Line (for straight walls)
line = Draft.make_line(FreeCAD.Vector(0,0,0), FreeCAD.Vector(5000,0,0))

# Wire (for walls following a path, or roof profiles)
wire = Draft.make_wire([
    FreeCAD.Vector(0, 0, 0),
    FreeCAD.Vector(5000, 0, 0),
    FreeCAD.Vector(5000, 4000, 0),
    FreeCAD.Vector(0, 4000, 0),
], closed=True)

# Rectangle (for floor plans)
rect = Draft.make_rectangle(5000, 4000)
```

---

## IFC Type Mapping

| Arch Object | Default IFC Type |
|-------------|-----------------|
| Wall | Wall |
| Window | Window |
| Structure (column) | Column |
| Structure (beam) | Beam |
| Structure (slab) | Slab |
| Floor | Building Storey |
| Building | Building |
| Site | Site |
| Space | Space |
| Roof | Roof |
| Stairs | Stair Flight |
| Equipment | Furnishing Element |

Override with `obj.IfcType = "Custom Type"`.

---

## Materials

```python
# Single material
mat = Arch.makeMaterial("Concrete")
mat.Color = (0.7, 0.7, 0.7, 1.0)
wall.Material = mat

# Multi-material (layered walls)
mm = Arch.makeMultiMaterial("Cavity Wall")
# Define layers: [name, material_object, thickness]
mm.Materials = [mat_brick, mat_insulation, mat_plaster]
mm.Thicknesses = [100, 80, 20]
mm.Names = ["Brick", "Insulation", "Plaster"]
wall.Material = mm
```

---

## FreeCAD Source Locations

For looking up detailed implementations:

| Module | Path in `vendor/FreeCAD/` |
|--------|--------------------------|
| Arch objects | `src/Mod/BIM/Arch*.py` |
| BIM commands | `src/Mod/BIM/bimcommands/` |
| IFC support | `src/Mod/BIM/importers/importIFC*.py` |
| Arch component base | `src/Mod/BIM/ArchComponent.py` |
| Draft module | `src/Mod/Draft/draftmake/` |
