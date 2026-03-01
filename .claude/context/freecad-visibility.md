# FreeCAD Viewport Visibility Hygiene

Which objects should be hidden by default and why. Applies to any FreeCAD document.

---

## ⚠️ CRITICAL — TechDraw Pages CRASH FreeCAD if made visible in a loop

**Never set `obj.ViewObject.Visibility = True` on a `TechDraw::DrawPage` object.** Doing so activates the page as the active MDI window, switching the view away from the 3D viewport. Cycling through multiple TechDraw pages in a visibility loop causes rapid MDI window switching that **crashes FreeCAD**.

The same applies to all TechDraw view objects — only the DrawPage is dangerous enough to crash, but the others corrupt the active-view state.

**Safe rule: never call `.Visibility = True` on any object unless you have positively identified it as a 3D geometry object.** Always check TypeId first. The safe way to restore visibility is to track which objects were visible *before* your changes and restore only those by name.

---

## Always-Hidden Object Types

These types exist in every FreeCAD document but should never be visible in the 3D viewport unless explicitly needed for editing. Their presence in the visible list is almost always an accident.

| TypeId | Examples | Why hidden |
|--------|----------|------------|
| `App::Origin` | `Origin`, `Origin001`, … | Container auto-created for every App::Part and PartDesign::Body. Holds 6 child feature objects. |
| `App::Line` | `X_Axis`, `Y_Axis001`, `Z_Axis012`, … | The 3 axis lines inside each App::Origin (one per container, 3 axes each). |
| `App::Plane` | `XY_Plane`, `XZ_Plane003`, `YZ_Plane012`, … | The 3 planes inside each App::Origin (one per container, 3 planes each). |
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
| `TechDraw::DrawPage` | `Situationsplan base`, `Planritning`, … | **⚠️ CRASHES FREECAD if .Visibility toggled in a loop** — activates page as MDI window |
| `TechDraw::DrawViewPart` | `View`, `View001`, … | 2D projection views on TechDraw pages |
| `TechDraw::DrawViewSection` | `Section`, `SectionB`, … | Section views on TechDraw pages |
| `TechDraw::DrawViewDetail` | `Detail`, … | Detail views on TechDraw pages |
| `TechDraw::DrawHatch` | `Hatch`, … | Hatching on TechDraw pages |
| `TechDraw::DrawViewDimension` | `Dimension`, `Dimension002`, … | Dimension annotations — belong to TechDraw pages only |
| `TechDraw::DrawSVGTemplate` | `Template`, `Template001`, … | Page templates — belong to TechDraw pages only |
| `TechDraw::DrawLeaderLine` | `LeaderLine`, … | Leader lines on TechDraw pages |
| `TechDraw::DrawRichAnno` | `RichAnno`, … | Rich text annotations on TechDraw pages |

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
    "App::Origin", "App::Line", "App::Plane", "App::OriginFeature",
    "TechDraw::DrawPage",   # ⚠️ CRASH RISK — do not set Visibility on these
    "TechDraw::DrawViewPart", "TechDraw::DrawViewSection", "TechDraw::DrawViewDetail",
    "TechDraw::DrawHatch", "TechDraw::DrawViewDimension", "TechDraw::DrawSVGTemplate",
    "TechDraw::DrawLeaderLine", "TechDraw::DrawRichAnno",
    "PartDesign::SubShapeBinder",
    "PartDesign::Pad", "PartDesign::Pocket",
    "PartDesign::LinearPattern", "PartDesign::AdditiveLoft",
    "Sketcher::SketchObject",
    "Part::Part2DObjectPython", "App::FeaturePython",
    "Image::ImagePlane",
}

# Add project-specific labels for intermediate construction objects:
always_hidden_labels = set()

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
    # Origins (MUST hide — 100+ in large docs)
    "App::Origin", "App::Line", "App::Plane", "App::OriginFeature",
    # TechDraw — DrawPage CRASHES FreeCAD if set visible in a loop; hide entire family
    "TechDraw::DrawPage",
    "TechDraw::DrawViewPart", "TechDraw::DrawViewSection", "TechDraw::DrawViewDetail",
    "TechDraw::DrawHatch", "TechDraw::DrawViewDimension", "TechDraw::DrawSVGTemplate",
    "TechDraw::DrawLeaderLine", "TechDraw::DrawRichAnno",
    # PartDesign internals
    "PartDesign::SubShapeBinder",
    "PartDesign::Pad", "PartDesign::Pocket",
    "PartDesign::LinearPattern", "PartDesign::AdditiveLoft",
    # Sketches & 2D helpers
    "Sketcher::SketchObject",
    "Part::Part2DObjectPython",
    "App::FeaturePython",
    # Images
    "Image::ImagePlane",
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

---

## Tree Hierarchy: Manage Containers, Not Leaves

**The single most important visibility principle**: FreeCAD's visibility system is hierarchical. Hiding a parent container hides every descendant automatically — no need to enumerate or iterate children.

This means:
- To hide an `App::Part` and everything it contains → hide the Part (1 operation)
- To hide a `PartDesign::Body` and all its features → hide the Body (1 operation)
- To show the full assembly → show the top-level `App::Part` (1 operation)

**Never iterate over leaf objects.** If you find yourself writing a loop to hide individual Pad/Pocket/Binder objects, stop — hide their parent Body or Part instead.

### The Container Hierarchy

```
Document
  └── App::Part  (e.g. "ParkingLot")           ← manage visibility HERE
        ├── App::Origin                          ← always hidden (auto-managed by parent)
        ├── PartDesign::Body  (e.g. "Wall")      ← or HERE if you need a single body
        │     ├── App::Origin                    ← auto-hidden with body
        │     ├── Sketcher::SketchObject         ← auto-hidden with body
        │     ├── PartDesign::Pad                ← auto-hidden with body
        │     ├── PartDesign::Pocket             ← auto-hidden with body
        │     └── PartDesign::Fillet  ← Tip      ← auto-hidden with body
        ├── Part::Feature  (e.g. "RoofSlab")    ← standalone geometry; manage directly
        └── App::Part  (nested sub-assembly)    ← manage HERE, not its children
```

**Rule**: Identify the highest container that covers what you want to show/hide. Toggle that one object. Done.

### Visibility Propagation Mechanism (source-verified)

**Source**: `Gui/ViewProviderGroupExtension.cpp`, `extensionHide()` / `extensionShow()`

When `App::Part.ViewObject.Visibility = False`, FreeCAD uses **explicit iteration** — NOT the scenegraph. The `ViewProviderGroupExtension::extensionHide()` method loops through `group->Group.getValues()` and calls `obj->Visibility.setValue(false)` on every child that is currently visible. Critically:

- Hiding a parent **does change** children's `Visibility` to `false` in the data model
- Only currently-visible children are affected (hidden children are untouched)
- `extensionShow()` mirrors this — it restores children to visible
- **Exception 1**: During file load (`isRestoring()`), visibility is NOT cascaded — each object's saved state is respected
- **Exception 2**: Changes marked with `Property::User1` (internal temporary visibility) do NOT propagate to children

**Practical consequence**: hiding a Part and then re-showing it will restore the children that were visible at the time of hiding. Children that were already hidden before the parent was hidden stay hidden. This is safe and the intended workflow.

**Still the correct rule**: to show/hide everything inside a Part, toggle the Part — don't enumerate children. One operation, correct result.

---

## PartDesign::Body — The Tip and Feature Stack

A `PartDesign::Body` is a linear feature stack: each feature (Pad, Pocket, Fillet…) is built on top of the previous. Only the **last feature in the stack (the Tip)** represents the final shape.

```
Body (PartDesign::Body)
  Tip → Fillet003           ← the "result" of this body — only this should be visible
  │
  └── feature stack:
        BaseFeature           ← starting shape (usually first Pad or imported solid)
        Pad001                ← hidden (intermediate)
        Pocket002             ← hidden (intermediate)
        LinearPattern003      ← hidden (intermediate)
        Fillet003             ← Tip — this is the visible final result
```

**Rules for Body visibility (source-verified):**

1. **Show/hide the Body itself** to show/hide the entire thing (including its Tip result)
2. **Never individually show intermediate features** unless deliberately debugging the construction history
3. `body.Tip` is an `App::PropertyLink` — FreeCAD **auto-advances** it to the newest solid feature every time `body.addObject(feature)` is called. It also **auto-adjusts** when features are deleted (falls back to the previous solid). Source: `Mod/PartDesign/App/Body.cpp`.
4. If the Tip is wrong, fix it: `body.Tip = body.Group[-1]`; then `doc.recompute()`

### DisplayModeBody — the key to showing only the Tip result

A `PartDesign::Body` has a `ViewObject.DisplayModeBody` property with two values (source: `Gui/ViewProviderBody.cpp`):

| Value | Mode | What is visible |
|-------|------|-----------------|
| `0` | **"Through"** | All features in the Body (active editing mode) |
| `1` | **"Tip"** | Only the Tip feature's shape (normal display mode) |

When a Body is not being actively edited, it should be in `"Tip"` mode. Switching to `"Through"` mode shows the full construction history — useful for debugging but confusing in a full-model view.

```python
body = doc.getObject("Body022")

# Normal display — only the final result (Tip shape)
body.ViewObject.DisplayModeBody = "Tip"

# Debug mode — see all construction features
body.ViewObject.DisplayModeBody = "Through"

# Show/hide the body
body.ViewObject.Visibility = True    # shows Tip result (if in Tip mode)
body.ViewObject.Visibility = False   # hides everything inside

# Check what the Tip is
print(body.Tip.Name if body.Tip else "No Tip set")

# Fix an incorrect Tip (force to last solid)
body.Tip = body.Group[-1]
doc.recompute()
```

### Why intermediate features appear visible

When `Body::addObject()` adds a new solid feature, it automatically sets `Visibility=False` on all other visible solid features in the Body (source: `Body.cpp` lines 236-268). So in a well-managed Body, only the Tip is ever visible.

However if `DisplayModeBody` is `"Through"`, or if features were individually made visible by accident, intermediate steps appear. Fix:

```python
body = doc.getObject("Body")
body.ViewObject.DisplayModeBody = "Tip"   # hide all non-Tip features
body.ViewObject.Visibility = True
doc.recompute()
```

---

### Visibility Gotchas (source-verified)

| Gotcha | What happens | Fix |
|--------|-------------|-----|
| Hiding a Part modifies children's Visibility | `extensionHide()` iterates children and sets `Visibility=false` on visible ones. If you hide a Part that contains a Body, the Body's Visibility is set to false. Re-showing the Part calls `extensionShow()` which restores them. | Use the parent toggle pattern — it handles restore automatically. |
| `DisplayModeBody="Through"` leaks intermediate features | All construction steps become visible at the Body level | Always ensure inactive Bodies are in `"Tip"` mode |
| Tip auto-advance may not fire on `obj.Shape = ...` | If you set a shape directly on a Part::Feature inside a Body rather than using PartDesign operations, Tip does not auto-advance | Set `body.Tip = feature` manually after direct shape assignment |
| Tip can be None | If a Body has no solid features yet | Check `body.Tip` before accessing `.Name` |
| File restore does NOT cascade visibility | On load, each object's saved Visibility is used — parent's state does not override | No action needed (intended behavior) |
| `User1` flag blocks cascade | Programmatic visibility changes marked internally as temporary | Rare in practice; only affects FreeCAD-internal operations |
| **Selected objects appear light blue** | FreeCAD highlights selected objects with a blue overlay in the 3D viewport. Screenshots capture this highlight, making it look like ShapeColor is wrong | Call `FreeCADGui.Selection.clearSelection()` before screenshots, or recognize blue = selected (color is fine underneath) |
| `Part.fuse()` crashes on complex lofts | Fusing many complex lofted B-rep shapes can freeze or crash FreeCAD (OCC kernel) | Use `Part.makeCompound()` for display grouping, or individual `Part::Feature` objects in a group |

---

## Practical: Restoring a Clean View in a Complex Document

The correct approach for a document with many bodies and parts:

```python
import FreeCAD as App
doc = App.getDocument("my_doc")

# ── Step 1: Identify the top-level containers you want visible ──
# These are App::Part or PartDesign::Body objects that are NOT inside another Part
# (i.e., they appear at the document root level, not nested)
top_level_show = {"MainAssembly", "Terrain", "Building"}  # adjust to your document
top_level_hide = {"TempConstruction", "DebugBody"}  # adjust to your document

# ── Step 2: Toggle only the top-level containers ──
for name in top_level_show:
    obj = doc.getObject(name)
    if obj and hasattr(obj, "ViewObject"):
        obj.ViewObject.Visibility = True

for name in top_level_hide:
    obj = doc.getObject(name)
    if obj and hasattr(obj, "ViewObject"):
        obj.ViewObject.Visibility = False

# ── Step 3: Clean up any noise types that might have leaked ──
noise = {"App::Origin", "App::Line", "App::Plane",
         "TechDraw::DrawPage",    # ⚠️ NEVER set these True
         "TechDraw::DrawViewPart", "TechDraw::DrawViewSection",
         "Sketcher::SketchObject", "Image::ImagePlane"}
for obj in doc.Objects:
    if hasattr(obj, "ViewObject") and obj.TypeId in noise:
        obj.ViewObject.Visibility = False

doc.recompute()
```

**Never mix "show all then filter" with this document.** The only safe approach on a document with TechDraw pages is to name the containers you want visible and show exactly those.

---

## Debugging: When You Need to See Inside a Body

Sometimes you need to inspect an intermediate feature — e.g., to understand why a loft failed.

```python
import FreeCAD as App
doc = App.getDocument("my_doc")

body = doc.getObject("Body022")   # the body to inspect

# 1. Hide the body (so the Tip doesn't obscure intermediate steps)
body.ViewObject.Visibility = False

# 2. Show just the feature you want to inspect
feature = doc.getObject("AdditiveLoft")
feature.ViewObject.Visibility = True

# 3. After inspection, restore:
feature.ViewObject.Visibility = False
body.ViewObject.Visibility = True
doc.recompute()
```

To inspect the full construction history of a body step by step:

```python
body = doc.getObject("Body022")
body.ViewObject.Visibility = False

# Show features one at a time
for i, feat in enumerate(body.Group):
    if hasattr(feat, "ViewObject"):
        feat.ViewObject.Visibility = True
        doc.recompute()
        print(f"Step {i}: {feat.Name} ({feat.TypeId}) — review, then press Enter")
        input()
        feat.ViewObject.Visibility = False

body.ViewObject.Visibility = True
doc.recompute()
```
