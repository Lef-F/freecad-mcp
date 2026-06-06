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

- **Hidden views export blank — silently.** A page renders/exports only the view objects whose `ViewObject.Visibility` is `True`. If a `DrawViewPart`/`DrawProjGroupItem`/etc. is hidden, it is dropped from `TechDrawGui.exportPageAsPdf`/`exportPageAsSvg` and from the scene-grab render — the page comes out as a bare template (title block only). There is **no error**: `view.getVisibleEdges()` still returns the projected edges and `view.State` still reads `Up-to-date`. The usual cause is a "hide all noise" visibility sweep or an old `show_by_role` that hid TechDraw view objects (see `freecad-visibility.md`). To diagnose/fix: `for o in doc.Objects: o.Visibility = True if (o.TypeId.startswith("TechDraw") and o.TypeId!="TechDraw::DrawPage") else o.Visibility`, recompute, re-export. Symptom check on an export: a blank-area page PDF has only template paths (e.g. ~40) vs. hundreds when geometry is present.
- **Regenerating exports**: `TechDrawGui.exportPageAsPdf(page, path)` / `exportPageAsSvg(page, path)` is the reliable way to refresh page deliverables after model edits (more robust than the QGraphicsScene grab, which can miss view geometry). Recompute first so the Section/Shape2DView projections are current.
- **`DrawProjectSplit::scrubEdges - OCC fuse raised warning(s): BOPAlgo_AlertSelfInterferingShape / BadPositioning / TooSmallEdge` is cosmetic.** Source-confirmed (`DrawProjectSplit.cpp` ~L449-494): `scrubEdges` runs a general-fuse on the **2D projected edges** (not 3D solids) with a loose fuzzy tolerance; only OCC *errors* abort (return empty) — *warnings* are logged and the view is produced with all geometry preserved. `SelfInterferingShape` here does **not** mean a solid is self-intersecting (it's overlapping projected edges); `TooSmallEdge` traces to sub-0.1mm sliver edges in the source solids. None of these drop drawing geometry. To reduce the noise (optional), clean slivers in the source solids (`removeSplitter()` / refit) — but it's purely log hygiene.
- **`App::FeaturePython: Link(s) ... go out of the allowed scope` on Sections** means a section references an object that lives inside an `App::Part` (App::Part enforces scope isolation; a plain `DocumentObjectGroup` does not). Harmless, but to silence it move the referenced objects out of the App::Part into a plain group (safe only if the Part has identity placement), or keep them all in the same Part as the section.
- **Direct TechDraw projections from 3D bodies** without Section planes work, but require manual updates and don't follow the same live-update pipeline.
- **Arch::SectionPlane** (the BIM workbench variant) is different from the `App::FeaturePython` section used in Part workbench workflows. Don't mix them.
- **Hardcoding object names in TechDraw views** — if an object is renamed, the view reference may break. Use groups where possible to reduce the number of individual references.

---

## Rendering a TechDraw Page to PNG (for programmatic inspection)

`get_view` does NOT work on TechDraw pages (active view is a `TechDrawGui::MDIViewPage` which has no `saveImage`). And the C++ `MDIViewPage::saveSVG/savePDF/saveDXF` methods are NOT exposed in the Python `MDIViewPagePy` binding (only `getPage()` is). So the only viable approach from Python is to **navigate down to the underlying `QGraphicsScene` via Qt and render it manually**.

### Recipe (verified end-to-end on FreeCAD 1.1.1)

```python
import FreeCAD, FreeCADGui
from PySide import QtWidgets, QtCore, QtGui

def render_techdraw_page(page_obj, out_path, target_width_px=1500, source_rect=None):
    """Render a TechDraw::DrawPage to a PNG file.

    Activates the page MDI view via doubleClicked() (the only Python-accessible way
    to instantiate an MDIViewPage), then walks ONLY the active subwindow's widget tree
    (NOT the whole MainWindow — see Gotcha #1) to find the QGVPage, grabs its scene,
    and renders it with QPainter.

    Args:
        page_obj: A TechDraw::DrawPage object from doc.getObject(...).
        out_path: Absolute path for the PNG output.
        target_width_px: Output width in pixels. Output height is auto-computed
            from the aspect ratio of source_rect. Recommended:
            - 1500 px for overview (default). Title block legible, dimensions readable.
              Typical size: 70-150 KB for A1 templates.
            - 2000-2500 px for detail review.
        source_rect: Optional QtCore.QRectF in scene coords for zoom-cropping a
            specific region. If None, uses scene.itemsBoundingRect() (whole page).
            Effective zoom factor = scene.itemsBoundingRect().width() / source_rect.width().
            Combined with target_width_px, this gives arbitrary detail resolution
            (TechDraw is vector — no upper resolution limit, just pixel size of output).

    Side effect: switches active MDI to the TechDraw page. Caller should invoke
    switch_to_3d_view() afterward if subsequent 3D operations are needed.

    Returns:
        (target_width_px, output_height_px) tuple.
    """
    page_obj.ViewObject.doubleClicked()

    mw = FreeCADGui.getMainWindow()
    mdi_area = mw.findChild(QtWidgets.QMdiArea)
    active_sub = mdi_area.activeSubWindow()
    if not active_sub:
        raise RuntimeError("No active MDI subwindow after doubleClicked()")

    # CRUCIAL: scope findChildren to the active subwindow's widget, NOT the MainWindow.
    # Each open TechDraw page has its own QGraphicsView and they all live as siblings
    # under the MainWindow — searching globally returns whichever is first, not the
    # one you just activated.
    gvs = active_sub.widget().findChildren(QtWidgets.QGraphicsView)
    target_gv = None
    for gv in gvs:
        s = gv.scene()
        if s and s.itemsBoundingRect().width() > 0:
            target_gv = gv; break
    if target_gv is None:
        raise RuntimeError(f"No populated scene in {active_sub.windowTitle()!r}")

    scene = target_gv.scene()
    src = source_rect if source_rect is not None else scene.itemsBoundingRect()
    h = int(target_width_px * src.height() / src.width())

    scene.clearSelection()
    img = QtGui.QImage(target_width_px, h, QtGui.QImage.Format_ARGB32)
    img.fill(QtCore.Qt.white)
    painter = QtGui.QPainter(img)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
    scene.render(painter, QtCore.QRectF(img.rect()), src)
    painter.end()
    img.save(out_path, "PNG")
    return target_width_px, h

def switch_to_3d_view():
    """Switch active MDI back to the document's 3D view. Required so subsequent
    get_view() calls work."""
    FreeCADGui.activateView("Gui::View3DInventor", False)
```

### Zoom-crop usage (verified)

To inspect a detail at high resolution, pass `source_rect` to crop the scene before rendering. Effective zoom = `full_scene_width / source_rect.width()` × (`target_width_px` / unzoomed output width).

```python
from PySide import QtCore

# Step 1: render full page to identify the area of interest
render_techdraw_page(page, "/tmp/overview.png", target_width_px=1500)

# Step 2: figure out the ROI in scene coords. Either:
#   (a) eyeball from the overview (positions in scene are absolute mm-ish)
#   (b) inspect specific objects' positions (e.g. dimension text scene coords)
#   (c) sample a fraction of the page BB — e.g. bottom-right 35% × 17% is the title block
page.ViewObject.doubleClicked()
import FreeCADGui
mw = FreeCADGui.getMainWindow()
sub = mw.findChild(QtWidgets.QMdiArea).activeSubWindow()
gv = next(g for g in sub.widget().findChildren(QtWidgets.QGraphicsView)
          if g.scene() and g.scene().itemsBoundingRect().width() > 0)
bb = gv.scene().itemsBoundingRect()

# Title block ROI (bottom-right 35% × 17%)
roi = QtCore.QRectF(
    bb.x() + bb.width() * 0.65,
    bb.y() + bb.height() * 0.83,
    bb.width() * 0.35,
    bb.height() * 0.17,
)

# Step 3: zoom render
render_techdraw_page(page, "/tmp/titleblock_zoom.png",
                    target_width_px=1500, source_rect=roi)
# At 1500 px wide for 35% of original width, effective zoom is ~2.9x;
# combined with same target width, every pixel in source maps to ~2.9 pixels in output.
```

Verified example from `parking_lot_v9` Sektion B-B page: full scene bbox is 2972 × 2101 (in TechDraw scene units, roughly mm-scaled-by-template-scale). Title block ROI of 1040 × 357 rendered at 1500 px wide yielded crisp anti-aliased text — every character legible.

### Gotchas (each one was hit during development — don't repeat)

1. **`mw.findChildren(QGraphicsView)` returns ALL QGraphicsViews across the whole MainWindow.** When multiple TechDraw pages are open, each has its own QGraphicsView, and the first non-empty one found is NOT necessarily the page you just activated. Result: byte-identical renders for every page. FIX: scope to `mdi_area.activeSubWindow().widget().findChildren(...)`.

2. **The 3D view's MDI subwindow ALSO has a QGraphicsView child** (overlay/HUD). So even on the MainWindow level, you can't filter by "has QGraphicsView" — you'd hit the 3D view first. Scoping to active subwindow side-steps this.

3. **`MDIViewPagePy` only exposes `getPage()` to Python.** Do NOT try `mdi.saveSVG(...)`, `savePDF`, or `saveDXF` — those C++ methods exist in `MDIViewPage.cpp` but are not in the Python binding. The QGraphicsScene render workaround above is the only path.

4. **Filtering MDI subwindows by `type(sub.widget()).__name__`** doesn't work — all subwindow widgets report as `QMainWindow` to Python (PySide doesn't know FreeCAD's C++ subclass names). Identify by title pattern (`'parking lot v9 : 1[*]'` is the 3D view; TechDraw pages have their label) or, better, use `FreeCADGui.activateView('Gui::View3DInventor', False)`.

5. **`FreeCADGui.activateView` requires TWO arguments**: `activateView(typeName, create_bool)`. Missing the second arg yields `TypeError: function takes exactly 2 arguments (1 given)`.

6. **`doubleClicked()` is safe** — does not inject CosmeticVertex objects. `ViewProviderPage::doubleClicked()` (`vendor/FreeCAD/src/Mod/TechDraw/Gui/ViewProviderPage.cpp:268-276`) only calls `Preferences::switchOnClick()` + `show()` + `showMDIViewPage()`. In `vendor/FreeCAD/src/Mod/TechDraw/Gui/`, `addCosmeticVertex` is called only from `CommandExtensionPack.cpp` (explicit user-invoked toolbar commands).

7. **The rendered scene shows whatever the page CURRENTLY has.** Section / Shape2DView dependencies that point to deleted objects produce empty / partial geometry, not errors. That's how you spot "stale" drawings after editing the 3D model.

### Verification recipe

To verify the render is actually capturing distinct content (not a stale cached scene):
```bash
md5 /tmp/td_pageA.png /tmp/td_pageB.png  # MUST produce different hashes
```
If identical, the QGraphicsView lookup is wrong — likely scoped too broadly.
