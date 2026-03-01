# FreeCAD Object Grouping

How to organize objects in a FreeCAD document. Applies to any design type (architectural, mechanical, etc.).

---

## Grouping Mechanisms

| Mechanism | TypeId | Side effects | Best for |
|-----------|--------|--------------|----------|
| `App::DocumentObjectGroup` | Folder | None — purely visual/organizational | Organizing any objects; always safe |
| `App::Part` | Part container | Objects share a Placement; moving the Part moves all children together | Sub-assemblies that must be positioned as a unit |
| `PartDesign::Body` | Feature body | Single solid output; features are sequential and dependent | Individual parametric solids built from sketches |
| `Part::Compound` | Shape merge | Shapes become one combined shape (no material union) | Grouping shapes for boolean or export purposes |
| `Part::MultiFuse` | Shape fusion | Shapes are permanently fused into one solid | Merging geometry that should become one body |
| Assembly workbench | Full assembly | Joint constraints, degrees of freedom | Mechanical assemblies with motion |

---

## Golden Approach

**Use `App::DocumentObjectGroup` as the primary organizational tool.**

- Zero geometric risk — objects keep their own placements and parametric dependencies
- Safe to reorganize at any time without breaking references
- Can contain any mix of object types
- Already the convention in new FreeCAD documents (the default "Group" objects)

**Use `App::Part` only when** objects genuinely need to be repositioned together as a sub-assembly — for example, a roof consisting of slab + parapet fences that should move as one unit. `App::Part` can be added to Section.Objects and TechDraw views just like individual objects; all its children are automatically included.

**Never use `Part::MultiFuse` or `Part::Compound` for pure organization** — they permanently alter the geometry and are difficult to undo.

---

## Working with Groups in Python

### Create a folder (App::DocumentObjectGroup)

```python
doc = FreeCAD.ActiveDocument
grp = doc.addObject("App::DocumentObjectGroup", "TerrainSite")
grp.Label = "Terrain & Site"
grp.addObject(doc.getObject("Body020"))   # Terrain
grp.addObject(doc.getObject("Loft003"))   # Terrain under street
grp.addObject(doc.getObject("Extrude"))   # Street
doc.recompute()
```

### Create a sub-assembly (App::Part)

```python
part = doc.addObject("App::Part", "RoofAssembly")
part.Label = "Roof"
part.addObject(doc.getObject("RoofSlab"))
part.addObject(doc.getObject("RoofFenceSouth"))
part.addObject(doc.getObject("RoofFenceEast"))
part.addObject(doc.getObject("RoofFenceWest"))
doc.recompute()
```

### Move an object between groups

```python
# Remove from old group first, then add to new
old_grp = doc.getObject("OldGroup")
new_grp = doc.getObject("NewGroup")
obj = doc.getObject("MyObject")

old_contents = list(old_grp.Group)
old_contents.remove(obj)
old_grp.Group = old_contents

new_grp.addObject(obj)
doc.recompute()
```

### Check which group an object belongs to

```python
obj = doc.getObject("MyObject")
for parent in obj.InList:
    if parent.TypeId in ("App::DocumentObjectGroup", "App::Part"):
        print(f"{obj.Label} is in {parent.Label}")
```

---

## Using Groups with TechDraw / Section Views

`App::Part` and `App::DocumentObjectGroup` objects can both be added to a `Section` plane's `Objects` list. When a group is in the list, all its children are automatically included in the cross-section cut and the resulting TechDraw view.

```python
# Add a group/part to a section so all children appear in the drawing
section = doc.getObject("Section001")
current = list(section.Objects)
roof_part = doc.getObject("RoofAssembly")
if roof_part not in current:
    section.Objects = current + [roof_part]
doc.recompute()
```

This is much cleaner than listing individual objects — add the group once and all future children are automatically included.

---

## Reorganization Safety Rules

Moving objects into groups is generally safe, but there are edge cases to watch for:

1. **TechDraw views reference objects by path/name** — if a view directly references `RoofSlab` and you move it into a Part, the reference may break. Always verify drawings after each move.
2. **PartDesign::Body children must stay in their Body** — never move Pads, Pockets, Binders, or Sketches that are internal PartDesign features into a top-level group.
3. **App::Part placement affects children** — if you move an `App::Part`, all objects inside move with it. Verify nothing shifts position unexpectedly.
4. **Always call `doc.recompute()` after any group change** — some objects won't update their dependency graph until recompute.

---

## Suggested Top-Level Folder Structure

For a construction/architecture design:

```
📁 Terrain & Site
    Terrain body, terrain-under-street, street extrusion
📁 Parking Structure
    Ground slab, stairs, walls, beams (source + arrays), wood covers
📁 Roof            ← App::Part if roof elements move together
    Roof slab, roof fences
📁 Retaining & Soil
    Soil fill bodies, retaining walls
📁 Drainage & Utilities
    Drainage channel, pipes
📁 Fencing / Temp
    Temporary construction fence
📁 Ramp
    Vehicle ramp body
📁 [Hidden] Terrain Inputs
    Intermediate lofts, shell, scale, fusion objects feeding the Terrain body
📁 [Hidden] Base Sketches   ← already Group001 in parking_lot_v6
📁 [Hidden] Section Objects ← already Group002
📁 [Hidden] Contours        ← already Group004
📁 Drawings                 ← TechDraw pages
📁 Measurements
```

Hidden folders should have their visibility off; move intermediate/construction objects there to keep the viewport clean.
