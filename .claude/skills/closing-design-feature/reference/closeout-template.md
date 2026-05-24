# Closeout: <feature-name>

**Document:** <freecad-doc-name>
**Feature slug:** <feature-slug>
**Created:** <YYYY-MM-DD>
**Closed:** <YYYY-MM-DD>
**Final status:** done | abandoned | partial

## Summary

Two or three sentences describing what got built, the user-facing change in the FreeCAD document, and the closing state.

## Spec vs. result

| Spec acceptance criterion | Status | Evidence |
|---|---|---|
| 1. `<criterion>` | Met | `journal/<feature>/build/T3.md` line 12 |
| 2. `<criterion>` | Not met | Deferred - see "Open issues" |
| 3. `<criterion>` | Met | screenshot at `journal/<feature>/screens/iso-final.png` |
| ... | | |

Spec scope drift: list any deviations from the original spec scope. Each one should already have a user-approved note in `spec.md` or `plan.md`.

## Objects changed

Pull from `.designs/<doc>/objects.md` (after this feature's edits). Format:

| Object name | TypeId | MCP_Role | Created / Modified / Deleted |
|---|---|---|---|
| `<name>` | `Part::Feature` | Final | Created |
| `<name>` | `App::Part` | Intermediate | Modified (Placement) |

Confirm `.designs/<doc>/objects.md` reflects these.

## Side-effect code changes

Code edits that emerged during this design work (often Apply-Patch tasks). The parent and user should decide which of these to commit as standalone PRs vs. keep local.

| File | Change | Decision |
|---|---|---|
| `addon/FreeCADMCP/rpc_server/rpc_server.py` | Added `get_section_edges()` RPC method | Commit (useful for future TechDraw work) |
| `src/freecad_mcp/server.py` | Bumped screenshot max dim from 1600 to 2000 | Keep local (project-specific) |
| `.claude/context/freecad-visibility.md` | Added new gotcha about TechDraw crash | Commit |

## Reviews

| Reviewer | File | Findings (bug / improvement / nitpick) | Resolved? |
|---|---|---|---|
| Correctness | `journal/<feature>/reviews/correctness.md` | 2 / 1 / 0 | All resolved in T7, T8 |
| Conventions | `journal/<feature>/reviews/conventions.md` | 0 / 2 / 1 | Improvements applied; nitpick ignored (style preference) |
| Integration | `journal/<feature>/reviews/integration.md` | 1 contradiction surfaced | Resolved with user input on T5 |

## Verification

- [ ] `show_by_role(doc, ["Final"])` shows the expected scene.
- [ ] `doc.save()` succeeded.
- [ ] Screenshot from `get_view(view_name="Isometric")` matches reference (attach in journal).
- [ ] If side-effect code: `uv run ruff check src/` + `uv run mypy src/` pass.
- [ ] `.designs/<doc>/objects.md` updated.
- [ ] `.designs/<doc>/tasks.md` marked done (if applicable).

## Lessons learned

Things to capture for future Claude sessions on this document or similar features.

- (Pattern) ...
- (Gotcha) ...
- (Tool friction) ...
- (Convention gap) ...

Promote any generalisable lesson into the user's `~/Documents/Obsidian/Lef/` notes per global instructions.

## Open issues

Anything not done that wasn't worth blocking close on. Each gets a tasks.md entry.

- [ ] T<N>: <description> - see `.designs/<doc>/tasks.md` row added 2026-XX-XX

---

## Journal manifest

For easy navigation later. Lists every artefact this feature produced.

```
.designs/<doc>/journal/<feature-slug>/
  spec.md
  plan.md
  research/
    <topic-1>.md
    <topic-2>.md
  build/
    T1.md
    T2.md
    ...
  reviews/
    correctness.md
    conventions.md
    integration.md
  closeout.md           # this file
```
