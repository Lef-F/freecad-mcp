# .designs/ — Local Design Knowledge Store

A gitignored folder at the repo root that stores per-document design knowledge across sessions.
Defined here so the convention is git-tracked and shared with every Claude instance that clones this repo.

## Why it exists

FreeCAD documents accumulate structure, decisions, and context that would otherwise be lost between sessions.
The `.designs/` folder is Claude's persistent memory for a specific FreeCAD document — object maps, tasks, discoveries, and reusable scripts.

## Structure

```
.designs/                          # gitignored — local only
  <document-name>/
    README.md                      # Overview, current status, key decisions, open questions
    objects.md                     # Living catalog of all objects organized by category
    tasks.md                       # Active tasks and done log (date-stamped)
    scripts/                       # Reusable Python snippets for execute_code
      *.py
```

One folder per FreeCAD document, named exactly as the FreeCAD document name.

## Rules

- **Always update, never recreate.** Edit existing files as the model evolves. Never delete and rewrite.
- `objects.md` is the canonical object map. Update it whenever objects are added, removed, or renamed.
- `tasks.md` moves tasks from Active → Done (with date). Never deletes them.
- `README.md` accumulates decisions and discoveries. Append new findings; don't overwrite.
- `scripts/` stores any Python snippet that proved useful, with a one-line comment describing what it does.

## When to create

Create `.designs/<doc-name>/` at the start of any design session for a document that doesn't have one yet.
Always check whether it exists first (`Glob` or `Read`) before creating.

## Mandatory session lifecycle

### Session start
1. `list_documents` — confirm which document is open
2. Check if `.designs/<doc-name>/` exists
   - **If yes**: read `README.md`, `objects.md`, `tasks.md` to restore context
   - **If no**: create the folder + all files using content from `get_objects` and the user's stated intent

### During the session
- Update `objects.md` incrementally as objects are created, renamed, or removed
- Note unexpected discoveries or design decisions in `README.md` → Open Questions or Design Decisions

### Session end
- Move completed tasks to Done in `tasks.md` (with date)
- Add any new deferred items as Active tasks
- Append new decisions or discoveries to `README.md`
- Save any reusable script snippets to `scripts/`

## Analysis Pitfalls to Avoid

### Multi-object assembly coverage
When analyzing whether a set of objects covers a boundary (e.g., fence perimeter), always check the COMBINED coverage of all objects together — never compare each object's BoundBox against the overall boundary in isolation. Two overlapping objects at a corner may fully cover the boundary even if neither individually does.

**Anti-pattern**: "Object A's X-extent starts at -500 but the assembly east edge is at -1200 — there's a 700mm gap." (Wrong: Object B covers that range at the corner.)

**Correct approach**: For each gap candidate, check whether any other object fills it before declaring a gap.

### Terrain surface Z detection
`terrain.Shape.common(box).BoundBox.ZMax` returns the top of the terrain SOLID at a given XY location. This works well for surface detection but can return false highs (e.g., Z_max=6500) when:
- The sample XY is inside the terrain body interior (e.g., mid-slope on a hillside)
- The terrain body has pockets that re-open at that XY

Always verify terrain-Z readings visually or cross-check with known survey points.

### tasks.md cleanup
Exploration tasks that get answered during the session should be moved to Done immediately — don't leave them as Active once resolved. An Active task that has been implicitly resolved during the session misleads the next session into re-investigating something already known.

## File templates

### README.md
```markdown
# <document-name>

Brief description of the project.

## Current Status

- **YYYY-MM-DD** — What was done this session.

## Key Facts

- FreeCAD document name: `<doc-name>`
- [dimensions, language, scope, etc.]

## Design Decisions & Discoveries

- [append findings here]

## Open Questions

- [append open items here]
```

### objects.md
```markdown
# Object Catalog — <document-name>

Last updated: YYYY-MM-DD. Total: N objects.
Update this file whenever objects are added, removed, or renamed.

## <Category>

| Name | Label | Type | Notes |
|------|-------|------|-------|
| ... | ... | ... | ... |
```

### tasks.md
```markdown
# Tasks — <document-name>

## Active

- [ ] Task description

## Done

- [x] YYYY-MM-DD — What was completed
```
