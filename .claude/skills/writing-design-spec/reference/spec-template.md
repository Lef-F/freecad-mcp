# Spec: <feature-name>

**Document:** <freecad-doc-name>
**Feature slug:** <feature-slug>
**Created:** <YYYY-MM-DD>
**Status:** draft | approved | in-progress | done | abandoned

## Background

Why are we doing this? What state is the design in, what observation triggered this, what's wrong with the current state?

Two or three sentences. Quote prior conversation, screenshots, or `.designs/<doc>/objects.md` entries that motivated the work.

## Goal

One sentence: what the design will look like / do once this feature is done. Visible to a future Claude reading this cold.

## Scope

What this feature WILL change. Be specific:
- Objects: names of FreeCAD objects to create / modify / delete
- Geometry: dimensions, positions, materials, parametric relationships
- Document structure: groups, hierarchy, MCP_Role tags
- Drawings: TechDraw pages, views, dimensions
- Documentation: which `.designs/<doc>/*.md` files will be updated

## Out of scope

What this feature will NOT touch, even though it might seem related. Important to prevent reviewer noise and scope-creep.

## Acceptance criteria

Numbered, concrete, verifiable. Each one must be checkable by reading the FreeCAD document or running a script.

1. `<object-name>` exists with MCP_Role=Final and Placement <expected>.
2. `show_by_role(doc, ["Final"])` displays no orphaned helpers or intermediates.
3. Screenshot from `get_view(view_name="Isometric")` matches reference image at `journal/<feature>/reference/<image>.png` within visual tolerance.
4. `doc.save()` succeeds and the document opens cleanly.
5. `.designs/<doc>/objects.md` updated with the new objects.

## Constraints

Project invariants this feature must respect (auto-loaded from CLAUDE.md - review and tighten):
- Every new object gets `MCP_Role` set at creation (`Final` / `Intermediate` / `Alternative` / `Deprecated`).
- `execute_code` strings are ASCII-only (no special chars like degree signs, em-dashes, arrows, approx signs).
- GUI-mutating operations go through the task queue (already handled by RPC layer).
- Manual `.Visibility` toggles only after a baseline `show_by_role()` call; restore with `show_by_role()` afterwards.
- Numerical analysis goes through a Python script (`uv run python3 ...`), not mental arithmetic.

Feature-specific constraints (fill in):
- ...

## References

- Document: `.designs/<doc>/README.md`, `objects.md`, `tasks.md`
- Prior work: `journal/<other-feature>/closeout.md` if relevant
- External: Boverket / Three.js / FreeCAD source paths needed for research
- Survey data: `.designs/<doc>/...` coordinate references if applicable

## Open questions

Things the user has to decide before this can move to `plan` phase. Each one blocks planning. Use AskUserQuestion to resolve.

- [ ] Question 1: ...
- [ ] Question 2: ...

## Side-effects expected

Code changes that might emerge from this design work (new MCP tools, addon fixes, skill updates). Captured here so the closing phase can audit them.

- [ ] (likely) ...
- [ ] (possible) ...

---

## Notes for the agent reading this

- Update **Status** as the feature progresses.
- Once **approved** by the user, do not edit Background / Goal / Scope / Out-of-scope / Acceptance criteria without re-approval. Append open questions or notes below this line instead.
- The plan phase reads this file. The build phase references it by `journal/<feature>/spec.md`.
