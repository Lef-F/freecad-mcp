# FreeCAD Viewport Visibility Hygiene

Which objects should be hidden by default and why. Applies to any FreeCAD document.

---

## Always-Hidden Object Types

These types exist in every FreeCAD document but should never be visible in the 3D viewport unless explicitly needed for editing. Their presence in the visible list is almost always an accident.

| TypeId | Examples | Why hidden |
|--------|----------|------------|
| `App::Origin` | `X_Axis001`, `XY_Plane012`, … | Auto-created for every PartDesign::Body and App::Part (50+ in a large doc) |
| `PartDesign::SubShapeBinder` | `Binder`, `Binder004`, `Binder016`, … | Shape reference inputs to PartDesign operations — internal plumbing |
| `PartDesign::Pad` | `Pad011`, `Pad029`, … | Intermediate PartDesign steps inside a Body |
| `PartDesign::Pocket` | `Pocket009`, `Pocket036`, … | Intermediate PartDesign steps |
| `PartDesign::LinearPattern` | `LinearPattern004`, … | Intermediate PartDesign steps |
| `PartDesign::AdditiveLoft` | `AdditiveLoft`, … | Intermediate PartDesign steps |
| `Sketcher::SketchObject` | `Sketch022`, `Sketch052`, … | Construction profiles and master sketches |
| `App::FeaturePython` (section) | `Section`, `Section001`, … | Cross-section planes for TechDraw — 3D plane objects |
| `Part::Part2DObjectPython` (shape view) | `Shape2DView`, … | 2D projection objects feeding TechDraw pages |
| `Part::Part2DObjectPython` (curves) | `BSpline`, `Line001`, … | Guide curves, contour lines — not final geometry |
| Terrain construction intermediaries | `Shell`, `Scale`, `Fusion`, `Loft001`, `Loft002`, `Extrude001` | Hidden construction chain feeding final terrain body |
| `TechDraw::DrawViewDimension` | `Dimension`, `Dimension002`, … | Dimension annotations — belong to TechDraw pages only |
| `TechDraw::DrawSVGTemplate` | `Template`, `Template001`, … | Page templates — belong to TechDraw pages only |

---

## Situationally Visible

These may be visible during active editing but should be re-hidden after:

| Type | When to show | When to hide |
|------|-------------|--------------|
| `Sketcher::SketchObject` | While editing the sketch | After closing the sketch editor |
| `PartDesign::SubShapeBinder` | When debugging a Body's reference geometry | After fixing the issue |
| Section planes | When setting up a new TechDraw view | After the view is created |
| Terrain construction chain | When debugging the terrain surface | After confirming the output looks correct |
| Source beams (before Array) | When editing the source geometry | After editing — the Array multiplies them and that's what's visible |

---

## How to Identify Accidentally Visible Objects

Run this query to find visible objects whose TypeId should be hidden:

```python
doc = FreeCAD.ActiveDocument

always_hidden_types = {
    "App::Origin",
    "PartDesign::SubShapeBinder",
    "PartDesign::Pad",
    "PartDesign::Pocket",
    "PartDesign::LinearPattern",
    "PartDesign::AdditiveLoft",
    "Sketcher::SketchObject",
    "TechDraw::DrawViewDimension",
    "TechDraw::DrawSVGTemplate",
}

always_hidden_labels = {"Terrain shell", "Terrain scale", "Terrain base"}

leaks = []
for obj in doc.Objects:
    if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
        continue
    if not obj.ViewObject.Visibility:
        continue
    if obj.TypeId in always_hidden_types:
        leaks.append(f"{obj.Name} ({obj.Label}) — {obj.TypeId}")
    elif obj.Label in always_hidden_labels:
        leaks.append(f"{obj.Name} ({obj.Label}) — hidden construction object")

print(f"Found {len(leaks)} accidentally visible objects:")
for l in leaks:
    print(" ", l)
```

---

## Bulk Visibility Cleanup

To hide all accidentally-visible internal objects:

```python
doc = FreeCAD.ActiveDocument

always_hidden_types = {
    "App::Origin",
    "PartDesign::SubShapeBinder",
    "PartDesign::Pad",
    "PartDesign::Pocket",
    "PartDesign::LinearPattern",
    "PartDesign::AdditiveLoft",
    "Sketcher::SketchObject",
    "TechDraw::DrawViewDimension",
    "TechDraw::DrawSVGTemplate",
}

hidden = []
for obj in doc.Objects:
    if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
        continue
    if obj.ViewObject.Visibility and obj.TypeId in always_hidden_types:
        obj.ViewObject.Visibility = False
        hidden.append(f"{obj.Name} ({obj.Label})")

print(f"Hidden {len(hidden)} objects:")
for h in hidden:
    print(" ", h)
doc.recompute()
```

---

## Query: Count Visible vs Hidden by Type

Useful at the start of a session to understand the document's visibility state:

```python
doc = FreeCAD.ActiveDocument
from collections import Counter

vis_types = Counter()
hid_types = Counter()
for obj in doc.Objects:
    if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
        continue
    type_short = obj.TypeId.split("::")[-1]
    if obj.ViewObject.Visibility:
        vis_types[type_short] += 1
    else:
        hid_types[type_short] += 1

print("VISIBLE types:")
for t, n in vis_types.most_common(20):
    print(f"  {n:3d}  {t}")
print("\nHIDDEN types:")
for t, n in hid_types.most_common(20):
    print(f"  {n:3d}  {t}")
```

---

## The "Final Objects" Principle

A well-maintained document has a clear two-tier structure:

**Tier 1 — Final/published objects** (visible): The finished 3D geometry that represents the design. These are typically `PartDesign::Body`, `App::Part`, `Part::Feature`, `Part::FeaturePython` (arrays), and `Part::Extrusion` objects with meaningful labels.

**Tier 2 — Supporting objects** (hidden): Everything else — sketches, binders, pads/pockets, construction chains, section planes, dimensions. These exist to build the Tier 1 objects but are not "the design."

When a user says "show me only the finished design", they mean Tier 1 only. When exploring spatial relationships or debugging geometry, you may need to temporarily show Tier 2 objects — but always restore their visibility afterward.
