# FreeCAD Technical Drawings — Section → Shape2DView → TechDraw

How technical drawings work in FreeCAD for construction-style documentation.
Covers the workflow confirmed to work well in practice (not experimental approaches).

---

## The Pipeline

```
Section plane          Shape2DView              TechDraw page
(App::FeaturePython)  (Draft::Shape2DView)     (TechDraw::DrawPage)
        │                     │                        │
        │  Objects list        │  feeds                 │  views list
        │  (what to cut)       │                        │
        ▼                      ▼                        ▼
   defines cut plane    live 2D projection       printable drawing
   + which 3D objects   of section result        with title block
   are sectioned
```

Each step feeds the next. Changes to the 3D model propagate automatically through all three stages when `doc.recompute()` is called.

---

## Step 1: Section Plane

The `Section` object (TypeId: `App::FeaturePython`) defines:
- **Where** the cut plane is (Placement — position and orientation)
- **What** gets cut (the `Objects` property — a list of 3D objects/groups)

### Key properties

| Property | Type | Notes |
|----------|------|-------|
| `Objects` | list | 3D objects included in this section cut |
| `Placement` | Placement | Position and orientation of the cut plane |

### Normal orientation convention

The section plane cuts perpendicular to its local Z-axis:
- **Vertical section** (wall cut, elevation): plane normal is horizontal (X or Y direction)
- **Plan section** (floor plan): plane normal is vertical (Z direction)

### Adding objects to a section

```python
doc = FreeCAD.ActiveDocument
section = doc.getObject("Section001")

# Add a single object
current = list(section.Objects)
obj = doc.getObject("Body020")
if obj not in current:
    section.Objects = current + [obj]

# Add a group — all children are automatically included
grp = doc.getObject("RoofAssembly")
if grp not in current:
    section.Objects = current + [grp]

doc.recompute()
```

**Important**: Adding an `App::Part` or `App::DocumentObjectGroup` to a section's Objects list automatically includes all its children. This is the efficient way to keep drawings up to date as the design grows — add the group once.

### Querying section contents

```python
section = doc.getObject("Section001")
print(f"Objects in {section.Label}:")
for obj in section.Objects:
    type_note = f"[{obj.TypeId.split('::')[-1]}]"
    print(f"  {obj.Name} ({obj.Label}) {type_note}")
    # If it's a group/part, list children too
    if hasattr(obj, "Group"):
        for child in obj.Group:
            print(f"    └─ {child.Name} ({child.Label})")
```

---

## Step 2: Shape2DView

The `Shape2DView` object (TypeId: `Part::Part2DObjectPython`) is a live 2D projection of the section result. It:
- References the Section plane
- Automatically updates when the section or 3D geometry changes
- Is always hidden in 3D (it's 2D output, not 3D geometry)
- Gets placed on a TechDraw page

---

## Step 3: TechDraw Page

The TechDraw page collects one or more Shape2DViews (and other view types) into a printable drawing sheet with a title block.

### Query what's on each page

```python
for obj in doc.Objects:
    if obj.TypeId == "TechDraw::DrawPage":
        print(f"\nPage: {obj.Label}")
        for view in obj.Views:
            print(f"  View: {view.Label} ({view.TypeId})")
```

---

## Common Patterns

### Check which sections include an object

```python
obj_to_find = doc.getObject("Body020")
for obj in doc.Objects:
    if obj.TypeId == "App::FeaturePython" and hasattr(obj, "Objects"):
        if obj_to_find in obj.Objects:
            print(f"  Found in: {obj.Name} ({obj.Label})")
        # Also check indirect containment via groups
        for container in obj.Objects:
            if hasattr(container, "Group") and obj_to_find in container.Group:
                print(f"  Found indirectly via {container.Label} in: {obj.Name} ({obj.Label})")
```

### Ensure a new 3D object appears in all existing sections

When adding a new 3D object that should appear in all drawings:
1. If the new object belongs to an existing group that is already in the Section's Objects list → no action needed; it's automatically included.
2. If it's standalone or in a new group → add it (or its group) to each Section's Objects list.

```python
new_obj = doc.getObject("Body022")  # new object to add to drawings

for obj in doc.Objects:
    if obj.TypeId == "App::FeaturePython" and hasattr(obj, "Objects"):
        current = list(obj.Objects)
        if new_obj not in current:
            obj.Objects = current + [new_obj]
            print(f"Added to {obj.Label}")

doc.recompute()
```

---

## Object Types Involved

| TypeId | Role | Always hidden? |
|--------|------|---------------|
| `App::FeaturePython` (Section) | Cut plane definition + object list | Yes — 3D plane helper |
| `Part::Part2DObjectPython` (Shape2DView) | Live 2D projection | Yes — feeds TechDraw only |
| `TechDraw::DrawPage` | Drawing sheet | Not applicable (it's a document, not 3D) |
| `TechDraw::DrawViewPart` | A 3D-projection view on a page | Not applicable |
| `TechDraw::DrawViewDimension` | Dimension annotation on a page | Yes in 3D — belongs to TechDraw only |
| `TechDraw::DrawSVGTemplate` | Title block template | Yes in 3D |

---

## What Doesn't Work Well

- **Direct TechDraw projections from 3D bodies** without Section planes work, but require manual updates and don't follow the same live-update pipeline.
- **Arch::SectionPlane** (the BIM workbench variant) is different from the `App::FeaturePython` section used in Part workbench workflows. Don't mix them.
- **Hardcoding object names in TechDraw views** — if an object is renamed, the view reference may break. Use groups where possible to reduce the number of individual references.
