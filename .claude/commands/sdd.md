---
description: Enter or resume a spec-driven design feature on the active FreeCAD document.
---

# /sdd

Invoke the `spec-driven-design` skill via the Skill tool. The skill will:

1. Identify the active FreeCAD document and the feature slug (ask if missing).
2. Detect the current journal state (`.designs/<doc>/journal/<feature-slug>/`).
3. Route to the right phase: `writing-design-spec` -> `planning-design-feature` -> `dispatching-design-subagents` -> `reviewing-design-feature` -> `closing-design-feature`.
4. Show a 3-line status before each phase handoff.

Arguments (optional):
- `feature-slug` — kebab-case slug to identify the feature. If omitted, the skill asks.

Examples:
- `/sdd` -> ask for slug, then route.
- `/sdd wood-fence-z-placement` -> resume / start that feature.

If the feature is already closed (`closeout.md` Status: done), the orchestrator will say so and ask what's next.
