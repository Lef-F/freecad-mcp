---
name: reorganizing-freecad-document
description: Analyses an open FreeCAD document's object structure using spatial clustering, proposes a logical group and label reorganisation, executes it system-by-system, and updates .designs/ documentation. Handles orphaned objects, generic auto-names, hidden nested groups, and inconsistent label conventions.
---

# Reorganizing a FreeCAD Document

## When to Use

- User asks to clean up, reorganise, or refactor a FreeCAD document's tree
- The model tree has generic auto-names (Group, Group001, Section001…), orphaned objects not in any group, or hidden nested groups not reachable from the tree
- A design session has grown organically and the structure no longer reflects the actual geometry systems

## Steps

### 1. Extract object spatial data from FreeCAD

Run via `execute_code` (capture_screenshot=False). Collects bounding box centres, types, labels, and group membership for every object with valid geometry. Skip objects without a Shape or with an invalid BoundBox.

Save the JSON output immediately to `.designs/<doc-name>/objects_spatial.json` so it can be recovered without re-querying FreeCAD.

```python
import FreeCAD, json
doc = FreeCAD.getDocument("<doc-name>")

NOISE = {"App::Origin","App::Line","App::Plane","TechDraw::DrawPage",
         "TechDraw::DrawSVGTemplate","TechDraw::DrawViewDimension",
         "TechDraw::DrawProjGroupItem","TechDraw::DrawProjGroup",
         "TechDraw::DrawViewPart","TechDraw::DrawViewSection",
         "Image::ImagePlane","Sketcher::SketchObject",
         "Part::Part2DObjectPython","App::FeaturePython"}

records = []
for obj in doc.Objects:
    if obj.TypeId in NOISE:
        continue
    try:
        bb = obj.Shape.BoundBox
        if not bb.isValid():
            continue
        records.append({
            "name": obj.Name, "label": obj.Label, "type": obj.TypeId,
            "cx": (bb.XMin+bb.XMax)/2, "cy": (bb.YMin+bb.YMax)/2,
            "cz": (bb.ZMin+bb.ZMax)/2,
            "xmin": bb.XMin, "xmax": bb.XMax,
            "ymin": bb.YMin, "ymax": bb.YMax,
            "zmin": bb.ZMin, "zmax": bb.ZMax,
            "in_group": [o.Label for o in obj.InList
                         if o.TypeId in {"App::DocumentObjectGroup","App::Part"}],
        })
    except Exception:
        pass

print(json.dumps(records))
```

Parse the stdout from the tool result and write to `.designs/<doc-name>/objects_spatial.json`.

### 2. Run spatial clustering

Use the inline-dependency script at `scripts/cluster_spatial.py` (see scripts/ folder). Run with:

```
uv run .claude/skills/reorganizing-freecad-document/scripts/cluster_spatial.py \
    .designs/<doc-name>/objects_spatial.json
```

This prints clusters at three eps levels (1500, 2500, 4000mm XY). Use eps=1500 for fine-grained functional analysis on building-scale models; increase eps for site-scale models where everything is farther apart.

**Reading cluster output**: Z range within each XY cluster reveals vertical sub-systems (e.g., ground floor at low Z, roof level at high Z). Combine spatial proximity with object labels and TypeIds to identify functional systems.

### 3. Audit the current group structure

Run via `execute_code`:
- **Root objects**: `[obj for obj in doc.Objects if not obj.InList]` — filter NOISE types
- **Ungrouped geometry**: objects with no InList entry that is a `DocumentObjectGroup` or `App::Part`
- **Hidden nested groups**: `App::DocumentObjectGroup` objects whose InList contains only `App::FeaturePython` (sections), not a visible parent group — these are "floating" and invisible in the tree
- **Empty groups**: groups where `len(grp.Group) == 0`
- **Section↔Drawing mapping**: for each Section, follow `Shape2DView.Base → Section`, then check `InListRecursive` for `TechDraw::DrawPage` labels

### 4. Propose a reorganisation plan

Present to the user before touching anything. Typical structure for a building/site model:

```
📁 Base Sketches          — source sketches (keep hidden)
📁 <Primary Structure>    — main built elements
📁 Site & Terrain         — terrain body + construction chain
📁 Fill & Backfill        — soil fills, retaining wall fills, backfill
📁 Roof Level             — roof structure + fencing as sub-group
   └ 📦 Roof (App::Part)
   └ 📁 Fence System
📁 Street & Approach      — street geometry, contour curves
📁 Section Objects        — section planes + Shape2DViews
📁 Drawings               — TechDraw pages
📁 Scale Bar              — scale bar primitives
```

Also identify label renames:
- Generic auto-names: `Section001` → descriptive name matching its drawing
- CamelCase object names: `WallPanelEast` → "Wall panel east" (sentence case, spaces)
- Generic sketch numbers: `Sketch069` → descriptive name based on its users and dependents

### 5. Execute — system by system

Get user approval on the plan, then execute one logical system at a time, saving after each. Order of operations:

1. **Label renames** (safest — no structural change)
   - Sections/Shape2DViews: rename to match their TechDraw page
   - Miscellaneous CamelCase → sentence case
   - Generic auto-named groups (e.g. FreeCAD auto-names like `Group008`, tool-generated names like `SKALA001`)

2. **Cleanup** — delete empty groups; merge orphaned sketch groups into Base Sketches

3. **New groups** — create with `doc.addObject("App::DocumentObjectGroup", "InternalName")`; set `.Label` separately

4. **Move objects** — use `grp.removeObject(obj)` then `target_grp.addObject(obj)` for DocumentObjectGroup moves. For App::Part, use `part.addObject(obj)` — note this changes the object's coordinate frame if the Part has a non-identity Placement.

5. **Surface hidden groups** — groups that appear in sections' InList but have no visible parent group should be added to an appropriate top-level group

6. After each system: `doc.recompute(); doc.save()`

Key rules:
- **Never move objects into an App::Part** unless you are certain the Part has identity Placement, or the object's geometry is already expressed in that coordinate frame
- **Never touch TechDraw objects** — moving DrawPage or DrawViewPart breaks view paths; reorganise only the 3D source objects
- Check `obj.InList` after each move to confirm the object now has exactly one group parent

### 6. Verify

After all changes:

```python
# All root non-noise objects should be groups or App::Part containers
roots = [obj for obj in doc.Objects
         if not obj.InList and obj.TypeId not in NOISE]
ungrouped = [obj for obj in roots
             if obj.TypeId not in {"App::DocumentObjectGroup","App::Part"}]
print(f"Ungrouped roots: {[o.Label for o in ungrouped]}")  # should be []
```

Also check drawings still render: open each TechDraw page and confirm no red/broken view markers.

### 7. Update .designs/ documentation

Update all four canonical files in `.designs/<doc-name>/`:

| File | What to update |
|------|----------------|
| `README.md` | Add status entry; update Phase object tables with new group paths |
| `objects.md` | Rewrite Groups & Containers table; update Section Views table with label↔drawing mapping; add any new sketches |
| `refactoring.md` | Replace proposed grouping with implemented structure (ASCII tree); add one change-log row per action |
| `tasks.md` | Close resolved carry-over tasks; add Done entry for the reorganisation |

## Verification

- `ungrouped_roots` is empty (all geometry in a named group)
- No hidden floating groups (every `App::DocumentObjectGroup` has at least one InList entry that is a `DocumentObjectGroup` or `App::Part`, or is itself a visible root)
- Section Objects labels match their TechDraw page labels
- `doc.save()` succeeds without errors
- All TechDraw pages open without broken view markers
- `.designs/<doc-name>/objects_spatial.json` saved for future re-runs
- All four `.designs/` markdown files updated
