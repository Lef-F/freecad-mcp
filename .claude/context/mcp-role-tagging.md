# MCP_Role — Object Role Tagging Convention

## Overview

Every object in a FreeCAD document gets an `App::PropertyEnumeration` called `MCP_Role` in the `"MCP"` property group. This enables reliable, one-command visibility management.

---

## Enum Values

| Value | Meaning | When to use |
|-------|---------|-------------|
| `Final` | Visible output geometry | The finished 3D shape the user sees in the model |
| `Intermediate` | Construction / internal | Body internals (Pad, Pocket, Binder, Sketch), terrain construction chain, section planes, origins, noise |
| `Alternative` | Inactive design option | Objects in a toggled-off design variant (e.g., fence Option B while Option A is active) |
| `Deprecated` | Kept but unused | Objects the user doesn't want to delete but are no longer part of the design |

---

## What Gets Tagged

**Every object.** No exceptions. If an object exists in `doc.Objects`, it has `MCP_Role`.

| Object kind | Default role | Notes |
|-------------|-------------|-------|
| PartDesign::Body (the Body itself) | `Final` or per user | The Body is the taggable unit — not its children |
| Body internals (Pad, Pocket, Binder, Sketch inside a Body) | `Intermediate` | Always. These are never Final. |
| Standalone Part::Feature, Part::Extrusion, Part::Loft | `Final` or per user | Leaf geometry |
| Part::FeaturePython (Array, Pipe) | `Final` or per user | Display objects |
| App::DocumentObjectGroup | Matches dominant child role | Informational — visibility is derived, not driven by tag |
| App::Part | Matches dominant child role | Same as groups |
| App::Origin, App::Line, App::Plane | `Intermediate` | Always. Noise. |
| Sketcher::SketchObject (root-level) | `Intermediate` | Construction geometry |
| TechDraw::* | `Intermediate` | Never touch visibility on these |
| Image::ImagePlane | `Intermediate` | Reference images |
| Section / Shape2DView | `Intermediate` | TechDraw input objects |

---

## Container Visibility Rule

**Containers (Groups, App::Part) do NOT drive visibility.** Their visibility is *derived*:
- A container is shown if and only if it has at least one descendant in the SHOW_SET.
- The tag on a container is informational (for querying), not for visibility logic.

---

## The `show_by_role()` Script

Copy-paste this into `execute_code` to control visibility. It is self-contained — no imports beyond FreeCAD/FreeCADGui.

```python
def show_by_role(doc, roles=None):
    """Show objects by MCP_Role tag. Handles containers, Body Tips, cascade cleanup.

    Args:
        doc: FreeCAD document
        roles: list of role strings, e.g. ["Final"] or ["Final", "Alternative"]
               Default: ["Final"]
    Returns:
        Number of tagged objects shown.
    """
    import FreeCADGui
    if roles is None:
        roles = ["Final"]
    roles_set = set(roles)

    # --- Build parent map ---
    parent_of = {}
    for obj in doc.Objects:
        if hasattr(obj, 'Group'):
            for c in obj.Group:
                parent_of[c.Name] = obj.Name

    # --- Compute SHOW_SET: tagged objects matching roles ---
    tagged_show = set()
    for obj in doc.Objects:
        if hasattr(obj, "MCP_Role") and obj.MCP_Role in roles_set:
            tagged_show.add(obj.Name)

    # --- Compute CONTAINER_SET: ancestors of shown objects ---
    containers = set()
    for name in tagged_show:
        current = name
        while current in parent_of:
            containers.add(parent_of[current])
            current = parent_of[current]

    # --- Compute TIP_SET: Tips of shown Bodies ---
    tips = set()
    for name in tagged_show:
        obj = doc.getObject(name)
        if obj and obj.TypeId == "PartDesign::Body" and obj.Tip:
            tips.add(obj.Tip.Name)

    # --- The full set of things that should be visible ---
    show_set = tagged_show | containers | tips

    # --- Pass 1: Hide everything (skip TechDraw — crash risk) ---
    for obj in doc.Objects:
        if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
            continue
        if obj.TypeId.startswith("TechDraw"):
            continue
        try:
            obj.ViewObject.Visibility = False
        except Exception:
            pass

    # --- Pass 2: Show the SHOW_SET ---
    for obj in doc.Objects:
        if obj.Name in show_set:
            if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
                continue
            if obj.TypeId.startswith("TechDraw"):
                continue
            try:
                obj.ViewObject.Visibility = True
            except Exception:
                pass

    # --- Pass 3: Cleanup cascade pollution ---
    # Showing containers may have cascaded to children not in show_set.
    # Re-hide anything that's visible but shouldn't be.
    for obj in doc.Objects:
        if obj.Name not in show_set:
            if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
                continue
            if obj.TypeId.startswith("TechDraw"):
                continue
            if obj.ViewObject.Visibility:
                try:
                    obj.ViewObject.Visibility = False
                except Exception:
                    pass

    # --- Activate 3D view ---
    try:
        mw = FreeCADGui.getMainWindow()
        mdi = mw.centralWidget()
        doc_title = doc.Name.replace("_", " ")
        for sub in mdi.subWindowList():
            title = sub.windowTitle().lower()
            if doc_title in title and "techdraw" not in title:
                mdi.setActiveSubWindow(sub)
                break
    except Exception:
        pass

    FreeCADGui.Selection.clearSelection()
    doc.recompute()
    return len(tagged_show)
```

### Usage

```python
# Show only Final objects (the standard "show me the model" command)
show_by_role(doc, ["Final"])

# Show Final + Alternative (compare design options)
show_by_role(doc, ["Final", "Alternative"])

# Show everything except Deprecated
show_by_role(doc, ["Final", "Intermediate", "Alternative"])

# Show only Alternative (isolate the inactive design option)
show_by_role(doc, ["Alternative"])
```

---

## The `tag_all_objects()` Script

Run once on a new or untagged document to tag every object. Then adjust roles manually or via script.

```python
def tag_all_objects(doc, default_role="Intermediate"):
    """Add MCP_Role to every object in the document that lacks it.

    - Objects already tagged are left unchanged.
    - New objects get default_role (usually "Intermediate").
    - Call this at the start of every session to catch untagged objects.

    Returns:
        Number of newly tagged objects.
    """
    ENUM_VALUES = ["Final", "Intermediate", "Alternative", "Deprecated"]

    tagged = 0
    for obj in doc.Objects:
        if not hasattr(obj, "MCP_Role"):
            try:
                obj.addProperty("App::PropertyEnumeration", "MCP_Role", "MCP",
                    "Object role: Final, Intermediate, Alternative, Deprecated")
                obj.MCP_Role = ENUM_VALUES
                obj.MCP_Role = default_role
                tagged += 1
            except Exception:
                pass  # Some objects may not support dynamic properties

    if tagged > 0:
        doc.recompute()
    return tagged
```

### Usage

```python
# Tag all untagged objects as Intermediate
n = tag_all_objects(doc)
print(f"Tagged {n} new objects")

# Then manually promote specific objects to Final:
for name in ["RoofSlab", "Body020", "GardenSoil"]:
    doc.getObject(name).MCP_Role = "Final"
```

---

## Session Workflow

### Start of session
```python
doc = FreeCAD.getDocument("my_doc")
n = tag_all_objects(doc)  # catch any untagged objects
if n > 0:
    print(f"Warning: {n} untagged objects found and set to Intermediate")
show_by_role(doc, ["Final"])  # restore clean view
```

### Creating new objects
Every `execute_code` block that creates objects MUST set `MCP_Role` immediately:
```python
obj = doc.addObject("Part::Feature", "WallNorth")
obj.Shape = solid
obj.addProperty("App::PropertyEnumeration", "MCP_Role", "MCP",
    "Object role: Final, Intermediate, Alternative, Deprecated")
obj.MCP_Role = ["Final", "Intermediate", "Alternative", "Deprecated"]
obj.MCP_Role = "Final"
```

### Claude's rules
1. **Every new object gets MCP_Role** — set at creation time, same block. Never skip.
2. **Baseline visibility = `show_by_role(doc, ["Final"])`** — always establish this before screenshots or user verification.
3. **Manual `.Visibility` toggles are allowed** for targeted adjustments (hiding a wall for interior views, isolating an object for inspection) — but only after a `show_by_role()` baseline, and always restore with `show_by_role()` afterward.
4. **Changing roles**: `obj.MCP_Role = "Alternative"` — then re-run `show_by_role`.
5. **Start of session**: always run `tag_all_objects()` to catch strays.
6. **When unsure about a role**: ask the user — never guess between Final and Intermediate.

---

## Property Details

- **Type**: `App::PropertyEnumeration`
- **Name**: `MCP_Role`
- **Group**: `MCP`
- **Persisted**: Yes — survives save/load in .FCStd file
- **Visible in UI**: Yes — appears as dropdown in FreeCAD Property Editor
- **Enum values**: `["Final", "Intermediate", "Alternative", "Deprecated"]`
