# TechDraw Object Lineage Reference

Complete bidirectional traversal map for the chain from 3D objects to TechDraw pages.

---

## Full Chain (top-down)

```
3D objects (Arch::Wall, Part::Box, etc.)
  │  Section.Objects (PropertyLinkList) -- empty = whole document
  ▼
Section (App::FeaturePython, Proxy.Type = "SectionPlane")
  │  Shape2DView.Base (PropertyLink)
  ▼
Shape2DView (Part::Part2DObjectPython)   ← Draft module, NOT a TechDraw type
  │  DrawProjGroupItem.Source (PropertyLinkList, inherited from DrawViewPart)
  ▼
DrawProjGroupItem (TechDraw::DrawProjGroupItem)
  │  DrawProjGroup.Views (PropertyLinkList, from DrawViewCollection)
  ▼
DrawProjGroup (TechDraw::DrawProjGroup)
  │  DrawPage.Views (PropertyLinkList)
  ▼
DrawPage (TechDraw::DrawPage)
```

Also possible without Section/Shape2DView:
```
3D objects ──(Source)──► DrawViewPart (TechDraw::DrawViewPart)
                              │
                  (BaseView) ▼
                        DrawViewSection (TechDraw::DrawViewSection)
```

And dimension annotations:
```
DrawViewPart / DrawProjGroupItem ──(References2D)──► DrawViewDimension
```

---

## TypeIds and Key Properties

| Object | TypeId | Key Forward Property | Key Backward Property |
|--------|--------|---------------------|-----------------------|
| 3D object | varies | — | `obj.InList` → Sections containing it |
| Section | `App::FeaturePython` (Proxy.Type="SectionPlane") | `Section.Objects` → 3D objs | `Section.InList` → Shape2DViews |
| Shape2DView | `Part::Part2DObjectPython` | `sv.Base` → Section or 3D obj | `sv.InList` → DrawViewParts/DPGIs |
| DrawProjGroup | `TechDraw::DrawProjGroup` | `dpg.Source` → 3D objs (shared); `dpg.Views` → child items | `dpg.InList` → DrawPages |
| DrawProjGroupItem | `TechDraw::DrawProjGroupItem` | `dpgi.Source` (inherited = parent's); `dpgi.Type` = "Front"/"Top"/... | `dpgi.InList` → dims, sections |
| DrawViewPart | `TechDraw::DrawViewPart` | `dvp.Source` → 3D objs; `dvp.Direction` → projection vector | `dvp.getDimensions()`, `dvp.getSectionRefs()` |
| DrawViewSection | `TechDraw::DrawViewSection` | `dvs.BaseView` (PropertyLink, singular) → DrawViewPart; `dvs.SectionNormal`, `dvs.SectionOrigin` | `dvs.InList` |
| DrawViewDimension | `TechDraw::DrawViewDimension` | `dim.References2D` → (view, "EdgeN") tuples | — |
| DrawPage | `TechDraw::DrawPage` | `page.Views` → all views | — |

---

## Shape2DView Properties

| Property | Type | Values / Notes |
|----------|------|----------------|
| `Base` | PropertyLink | Section, BuildingPart, Group, or any 3D shape object |
| `Projection` | PropertyVector | Projection direction (overridden by Section placement when Base is SectionPlane) |
| `ProjectionMode` | PropertyEnumeration | `"Solid"`, `"Individual Faces"`, `"Cutlines"`, `"Cutfaces"`, `"Solid faces"` |
| `FaceNumbers` | PropertyIntegerList | Used with `"Individual Faces"` mode |
| `HiddenLines` | PropertyBool | Include hidden edges |

**When `Base` is a SectionPlane**, projection direction is computed from:
```python
proj = obj.Base.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
```
The `Projection` property value is ignored.

---

## Shape2DView vs DrawViewSection — Critical Distinction

These are entirely different architectures that serve similar purposes:

| | Shape2DView (Draft) | DrawViewSection (TechDraw) |
|-|--------------------|-----------------------------|
| Source | `Base` → SectionPlane; cuts SectionPlane.Objects | `BaseView` → DrawViewPart; cuts the already-projected view |
| Result | Standalone Part object with 2D shape | TechDraw view on a page |
| Used by | Feeds into DrawProjGroupItem.Source | Lives directly in DrawPage.Views |
| Cut method | Boolean intersect in 3D, then project | HLR projection of Base with section plane |

Our workflow (Arch sections) uses **Shape2DView → DrawProjGroupItem**, not DrawViewSection.

---

## DrawProjGroup Source Sharing

`DrawProjGroup.Source` is **shared across all child DrawProjGroupItems**. When Source changes,
`updateChildrenSource()` propagates it to every item. Do NOT set Source on individual items —
set it on the parent group:

```python
group = doc.getObject("DrawProjGroup")
group.Source = [shape2dview]   # Propagates to all DrawProjGroupItem children
```

---

## Forward Traversal: Page → 3D Objects

```python
def find_3d_objects_on_page(page):
    """Collect all 3D source objects shown on a DrawPage."""
    sources = []
    for view in page.Views:
        tid = view.TypeId
        if tid == "TechDraw::DrawProjGroup":
            sources.extend(view.Source)
        elif "TechDraw::DrawViewPart" in tid or tid == "TechDraw::DrawProjGroupItem":
            sources.extend(view.Source)
        elif tid == "TechDraw::DrawViewSection":
            base = view.BaseView
            if base:
                sources.extend(base.Source)
    return list(set(sources))  # deduplicate
```

---

## Forward Traversal: Page → Shape2DViews

```python
def find_shape2dviews_on_page(page):
    """Find all Shape2DView objects feeding any view on a DrawPage."""
    svs = []
    for view in page.Views:
        for src in getattr(view, "Source", []):
            if src.TypeId == "Part::Part2DObjectPython":
                svs.append(src)
        for item in getattr(view, "Views", []):   # DrawProjGroup children
            for src in getattr(item, "Source", []):
                if src.TypeId == "Part::Part2DObjectPython":
                    svs.append(src)
    return list(set(svs))
```

---

## Forward Traversal: Shape2DView → Section → 3D Objects

```python
sv = doc.getObject("Shape2DView004")
section = sv.Base          # Section (App::FeaturePython)
objects_cut = section.Objects   # 3D objects in the section (empty = whole doc)
```

---

## Reverse Traversal: 3D Object → Pages

```python
def find_pages_showing(obj_3d, doc):
    """Find all DrawPages that include a given 3D object (direct or via Section)."""
    pages = []
    for page in doc.Objects:
        if page.TypeId != "TechDraw::DrawPage":
            continue
        objs = find_3d_objects_on_page(page)
        if obj_3d in objs:
            pages.append(page)
    return pages
```

---

## Reverse Traversal: DrawViewPart → Dimensions / Sections / Details

C++ bindings accessible from Python (from `DrawViewPart.h/cpp`):

```python
view = doc.getObject("DrawProjGroupItem")

dims    = view.getDimensions()    # -> list[DrawViewDimension]
sects   = view.getSectionRefs()   # -> list[DrawViewSection] with BaseView=view
details = view.getDetailRefs()    # -> list[DrawViewDetail] with BaseView=view
hatches = view.getHatches()       # -> list[DrawHatch]
balloons = view.getBalloons()     # -> list[DrawViewBalloon]
```

---

## Reverse Traversal: Section → Shape2DViews

```python
section = doc.getObject("SectionNNN")  # the section's Name
shape2dviews = [o for o in section.InList
                if o.TypeId == "Part::Part2DObjectPython"]
```

---

## Reverse Traversal: Shape2DView → DrawProjGroupItem

```python
sv = doc.getObject("Shape2DView004")
consumers = [o for o in sv.InList
             if o.TypeId == "TechDraw::DrawProjGroupItem"]
# or standalone views:
consumers += [o for o in sv.InList
              if o.TypeId == "TechDraw::DrawViewPart"]
```

---

## Gotchas

- **`InList` may contain duplicates** — use `set()` or deduplicate after filtering
- **`DrawProjGroupItem.Source` is inherited** from parent `DrawProjGroup`; reads reflect parent's value
- **`Section.Objects` empty = whole document** — not the same as "no objects"
- **`DrawViewSection.BaseView` is singular** (PropertyLink, not List) — one base view only
- **Shape2DView and DrawViewSection are unrelated** — same concept, completely different architecture
- **Section TypeId is generic**: `App::FeaturePython` — distinguish via `hasattr(obj, "Proxy") and getattr(obj.Proxy, "Type", "") == "SectionPlane"`
