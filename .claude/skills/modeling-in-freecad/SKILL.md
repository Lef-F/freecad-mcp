---
name: modeling-in-freecad
description: Guides Claude through collaborative, turn-based CAD modeling sessions in FreeCAD — from capturing design intent to iterative build, visual verification, and human checkpoints.
---

# Modeling in FreeCAD

## When to Use

- The user asks to build, design, or model something in FreeCAD
- The user wants to add to or modify an existing model
- A modeling session is in progress and needs structure or recovery

---

## Principles

This is a **turn-based collaboration**. Claude drives the CAD work; the user drives intent and decisions. Neither can succeed without the other.

**Claude's autonomous responsibilities:**
- Inspect the current document state before acting
- Execute batches of related objects together
- Verify results with screenshots after each batch
- Catch geometric mistakes (misaligned objects, wrong dimensions, missing recompute)
- Propose the next step before taking it
- **Always use Python for every calculation** — never compute numbers mentally (see below)

**Human checkpoints — always stop and ask:**
- Design intent isn't fully clear
- A dimension or material choice matters and hasn't been specified
- A screenshot looks wrong and Claude isn't sure why
- About to do something hard to undo (boolean operations, hiding source objects, deleting objects)
- The user should select something in the FreeCAD viewport (faces, edges, objects)
- A structural decision has multiple valid approaches

---

## Use Python for All Calculations

**Never compute numbers mentally.** CAD geometry involves chains of derived values — floor heights, step rises, wall offsets, boolean overlap positions — where a small mental arithmetic error silently misaligns every object built on top of it.

**Where to run calculations:**
- **Pure math** (deriving parameters, checking rounding, verifying overlaps) → run **locally** using the Bash tool: `python3 -c "..."`. No FreeCAD connection needed, no RPC round-trip.
- **Calculations inside `execute_code` blocks** → fine and expected, since parameters naturally live alongside the object-creation code that uses them.
- **Never** send code to FreeCAD via `execute_code` purely to do arithmetic.

**Local calculation example** — before writing any FreeCAD code, verify the numbers:
```bash
python3 -c "
H, t, n = 2500, 200, 13
rise = H / n
print(f'rise = {rise:.3f} mm')
print(f'check: {n} × {rise:.3f} = {n * rise:.3f} mm')
print(f'floor2_z = {t + H}')
"
```
Show the output to the user if any value involves rounding or a non-obvious result.

**Inside `execute_code` blocks**, always declare parameters at the top and derive everything:
```python
L, W, H = 5000, 4000, 2500
t = 200
n = 13
rise = H / n       # never write 192.307 as a literal
floor2_z = t + H   # never write 2700 as a literal
```

**Specific rules:**
- Never write a hardcoded coordinate like `2692` when it should be `t + H - 8` — the expression documents intent and stays correct if parameters change
- When the user gives dimensions that require rounding (e.g., `2500 / 13`), compute it locally first and surface the result: "rise = 192.3 mm (13 × 192.3 = 2499.9 mm, 0.1 mm short — acceptable, or adjust to 12 steps?)"
- Before any boolean operation, verify locally that the cutting tool spans both faces: `assert hole_z < slab_z and hole_z + hole_h > slab_z + slab_t`
- When stacking geometry (floors, walls, stairs), derive every Z value from the previous layer's variable, not a recomputed literal

---

## Phase 1 — Understand the Intent

Before touching FreeCAD, establish what we're building.

Ask the user (adapt to what's already known):

1. **What are we building?** (a room, a bracket, a staircase, a multi-floor building...)
2. **Key dimensions** — overall envelope if known; fill in typical values for unknowns, but confirm them
3. **Document** — create a new one, or work in an existing one? If existing, what's its name?
4. **Level of detail** — rough massing, or precise geometry with openings/details?

Propose a brief **build plan** (bullet list of structural elements in build order) and get a thumbs-up before proceeding.

---

## Phase 2 — Document Setup

If creating a new document:
```python
# via create_document tool
doc_name = "ProjectName"
```

If working in an existing document, call `list_documents` to confirm it's open, then `get_objects` to understand what's already there.

> **Checkpoint**: Show the user what exists. Confirm the starting point before adding anything.

---

## Phase 3 — Iterative Build Loop

Repeat this loop for each structural group (e.g., floor slab → walls → ceiling → stairs → openings):

### 3a. Plan the batch

State what you're about to create — object names, types, key dimensions. One sentence per object is enough. This gives the user a chance to correct before any code runs.

> Example: "I'll create the ground floor slab (5000×4000×200 mm at z=0), then four walls (200 mm thick, 2500 mm tall) sitting on top of it."

### 3b. Execute

Use `execute_code` for batches of related objects. Always:
- Define a `place(obj, x, y, z)` helper at the top
- Name objects descriptively (`WallSouth`, `Step01`, not `Box001`)
- Zero-pad numbered series (`Step01`…`Step13`)
- End every block with `doc.recompute()` and `print("Done")`

### 3c. Verify autonomously

After execution, take a screenshot:
```
get_view("Isometric", width=400, height=400)
```

Check:
- Are all expected objects visible?
- Do proportions look correct?
- Is anything floating, misaligned, or missing?

If something looks wrong, diagnose before asking the user using the tiered query pattern:
1. `get_objects` — confirm the object exists and its TypeId/Placement
2. `get_object` — inspect full properties if you don't know the property name yet
3. `execute_code(capture_screenshot=False)` — targeted read once you know what to check (e.g. `print(doc.getObject("WallSouth").Height)`)

Fix silently if the cause is clear.

### 3d. Human verification checkpoint

Show the screenshot and summarize what was built. Ask:

> "Does this look right? Anything to adjust before I continue?"

Do not proceed to the next batch until the user approves or gives corrections.

---

## Phase 4 — Openings and Booleans

Boolean operations are one-way: once you hide source objects and recompute, recovery is manual. Always checkpoint before proceeding.

> "I'm about to cut the stair opening through the second-floor slab using Part::Cut. This will hide the original slab and the cutting box. Shall I proceed?"

After the cut, verify:
- The `Part::Cut` result is visible and correctly shaped
- Source objects are hidden (not deleted)
- `doc.recompute()` was called and the cut resolved cleanly

Use ±5 mm overlap on the cutting tool on all faces to avoid zero-thickness geometry failures.

---

## Phase 5 — Exploration and Review

Once major geometry is in place, help the user see the model clearly:

1. **Interior view**: hide "open side" walls (south + east by convention for isometric)
2. **Section views**: use `get_view("Front")`, `get_view("Right")` to check alignment
3. **Annotate anomalies**: if a staircase top step doesn't align with the upper floor, flag it with exact numbers before fixing

> Checkpoint: "Here's the current state from three views. What would you like to refine or add next?"

---

## Phase 6 — Wrap-Up

When the modeling session reaches a natural end:

1. Take a final isometric screenshot at a meaningful size
2. List all objects created in this session
3. Note any deferred items (details not yet modeled, openings not cut, etc.)
4. Ask: "Would you like to save the document, or keep working?"

---

## Requesting User Actions in FreeCAD

When a task genuinely requires the user to interact with the FreeCAD viewport:

**Be explicit and specific:**
> "Please click on the top face of `SecondFloor` in the FreeCAD viewport to select it, then tell me the face name (it will appear in the status bar as `Face1`, `Face2`, etc.)."

**Common requests:**
- Selecting a face for a sketch attachment point → ask for face name
- Choosing between two design options → show screenshots of both, ask which
- Verifying visual alignment → ask user to orbit the view and confirm
- Confirming a dimension feels right at scale → ask user to check the ruler/scale bar

---

## Quick Reference — Key Numbers

| Element | Typical value |
|---------|---------------|
| Wall/slab thickness | 200 mm |
| Clear wall height | 2500 mm |
| Floor-to-floor | 2700 mm (wall + slab) |
| Stair rise | ~192 mm (2500 / 13 steps) |
| Stair run (tread) | 250–300 mm |
| Stair width | 900–1200 mm |
| Boolean overlap | ±5 mm on each face |

All dimensions in **millimeters**. Z is up. `Placement.Base` is the minimum corner of a box, not its center.

---

## Common Mistakes to Catch

- Object placed at z=0 when it should sit on top of a slab → check z = slab thickness
- Staircase top step doesn't reach the upper floor → verify `n * rise == floor_height`
- Boolean cut fails → check the tool overlaps both faces of the target by at least 5 mm
- Objects updated in code but geometry stale in view → `doc.recompute()` was missing
- `get_objects` on a large doc → use targeted `execute_code` queries instead to avoid timeouts

---

## Verification (end of session)

- All intended objects exist in the document (`list_documents` + `get_objects`)
- No floating or misaligned geometry (isometric + front + side screenshots)
- Boolean source objects are hidden but not deleted
- `doc.recompute()` was called after the last change
- The user has confirmed the result matches their intent
