---
name: closing-design-feature
description: Aggregates a feature's spec, plan, build artefacts, and reviews into closeout.md, surfaces side-effect code changes for commit decisions, and updates the design's tasks.md and objects.md. Fifth and final phase of spec-driven-design.
---

# Closing a Design Feature

## When to Use

- The build phase is complete.
- The review phase produced an `integration.md` and all must-fix items are resolved (or explicitly deferred).
- About to mark the feature done and move on.

Do NOT use for:
- A feature still actively in build or review (premature closure loses follow-up signals).
- A feature being abandoned (instead: write `closeout.md` with `Final status: abandoned` and note why).

## Prerequisites

1. `journal/<feature-slug>/spec.md` (approved).
2. `journal/<feature-slug>/plan.md` (executed; task statuses annotated).
3. `journal/<feature-slug>/build/` with per-task artefacts.
4. `journal/<feature-slug>/reviews/integration.md` (must-fix resolved).
5. FreeCAD document is in its final state for this feature.

## Steps

### 1. Verify acceptance criteria

Open `spec.md`. For each numbered Acceptance criterion:
- Read the relevant build artefacts and confirm Met / Not met / Cannot verify.
- For FreeCAD-geometry criteria: run a verification `execute_code` if needed (e.g., check Placement, MCP_Role, isValid).
- For document-state criteria: run `show_by_role(doc, ["Final"])` and capture a screenshot.

If any criterion is NOT met, do NOT close. Loop back to build or escalate.

### 2. Audit side-effects

Read the side-effect tracker in `plan.md` plus any side-effect notes in build artefacts. For each code change that emerged:
- Decide with the user: commit as standalone PR / keep local / discard.
- If commit: draft a conventional commit message. Per global rules: no Claude co-author lines, no em-dashes.
- If keep local: note in closeout.md that it's local-only and why.
- If discard: revert the change before closing.

### 3. Update document state files

- **`.designs/<doc-name>/objects.md`**: add / update rows for objects created or modified.
- **`.designs/<doc-name>/tasks.md`**: mark the feature row done; add follow-up rows for any deferred work.
- **`.designs/<doc-name>/README.md`**: update if the feature changed the design's overall structure (rare; usually no edit needed).

### 4. Save the FreeCAD document

```python
# via execute_code
doc = FreeCAD.ActiveDocument
doc.save()
```

The auto-save hook also fires on every mutation, but this is the explicit final save.

### 5. Write closeout.md from the template

Copy `reference/closeout-template.md` to `journal/<feature-slug>/closeout.md` and fill:
- **Summary** (2-3 sentences, user-facing).
- **Spec vs result** (acceptance criteria table).
- **Objects changed** (table from objects.md).
- **Side-effect code changes** (decisions per file).
- **Reviews** (counts + resolution status).
- **Verification** (checklist).
- **Lessons learned** (generalisable insights - these become candidates for `.claude/context/` updates or Obsidian notes).
- **Open issues** (deferred follow-ups with tasks.md row references).

### 6. Promote generalisable lessons

Lessons in step 5 that apply broadly (not project-specific) should be added to:
- `.claude/context/freecad-*.md` if it's a FreeCAD pattern / gotcha.
- `~/Documents/Obsidian/Lef/` if it's a workflow / tooling insight (per global instructions).
- **The relevant skill / template / hook file itself if the lesson is about the spec-driven-design flow misbehaving** (a phase skill, an archetype template, a reviewer brief, or a hook). Process lessons about the workflow tooling belong WITH the tooling, filed as an improvement against that file -- not buried in one project's closeout where they will be lost. If you cannot fix it in this session, at minimum record it as a follow-up that names the specific skill/template/hook to change.

Lessons that are document-specific stay in `closeout.md` only.

### 7. Final verification

Show the user:
- The closeout file path.
- The must-fix count from integration review (should be 0 after resolution).
- The acceptance status (should be all Met or explicitly deferred).
- Any side-effect commits drafted but not yet pushed.

Wait for user confirmation. Then set `Final status: done` in the closeout's front matter.

## Verification

- [ ] `closeout.md` exists with all sections filled.
- [ ] All Acceptance criteria from spec.md are accounted for (Met / Deferred).
- [ ] `objects.md` reflects the new document state.
- [ ] `tasks.md` is up to date.
- [ ] Side-effect code decisions are made (committed / local / discarded).
- [ ] FreeCAD document is saved.
- [ ] User has confirmed closure.

## Anti-patterns

- Closing with unmet acceptance criteria and no explicit defer note.
- Skipping the objects.md update (breaks future sessions' context).
- Committing side-effect code without conventional commit message.
- Bundling unrelated side-effect changes into one commit (split them).
- Writing closeout.md from memory instead of by reading the actual build artefacts (re-introduces the hallucination risk this whole flow exists to prevent).

## Key references
- `reference/closeout-template.md`
- `.designs/<doc-name>/objects.md`
- `.designs/<doc-name>/tasks.md`

## What happens after closure

- The journal entry becomes a durable record of what was done. Future sessions on this document grep it for prior decisions.
- Lessons learned that were generalised flow into the next feature.
- Side-effect commits go through whatever the project's normal PR flow is.
- The orchestrator marks the feature as done and the user can start a new one.
