# Plan: <feature-name>

**Spec:** `journal/<feature-slug>/spec.md`
**Created:** <YYYY-MM-DD>
**Status:** draft | approved | executing | done

## Strategy

Two or three sentences on the high-level approach. What order matters? What can be parallel? What are the risk points?

## Tasks

Each task has:
- **ID**: `T<N>` (T1, T2, ...). IDs never reused once assigned.
- **Title**: imperative, one line.
- **Archetype**: one of `RPC-Exec`, `Apply-Patch`, `Explore`, `Research`, `Review`.
- **Depends on**: list of prior task IDs (empty for first tasks).
- **Inputs**: files / state the dispatched subagent needs.
- **Expected output**: where the artefact lands. ALWAYS a file path under `journal/<feature>/build/<task-id>.md` or similar.
- **Acceptance**: how the parent knows this task succeeded.

### T1: <title>
- Archetype: `Explore`
- Depends on: -
- Inputs:
  - `journal/<feature>/spec.md`
  - `.designs/<doc>/objects.md`
- Expected output: `journal/<feature>/research/<topic>.md`
- Acceptance: file exists, contains numbered findings matching the spec's open questions.

### T2: <title>
- Archetype: `RPC-Exec`
- Depends on: T1
- Inputs:
  - findings from T1
- Expected output: `journal/<feature>/build/T2.md` (includes printed FreeCAD output + screenshot reference)
- Acceptance: `<object-name>` exists with expected Placement and MCP_Role.

### T3: <title>
- Archetype: `Apply-Patch`
- Depends on: T2
- Inputs:
  - `src/freecad_mcp/server.py` (specific lines)
- Expected output: edited file + read-back quote in `journal/<feature>/build/T3.md`
- Acceptance: ruff + mypy pass, file edit verified.

...

## Visualisation milestones

After which tasks should we capture a screenshot via `analyze_view` or `get_view`? List the views and what they verify.

- After T2: Isometric - confirm the new object exists at expected Placement.
- After T5: Top - confirm no Z-collision with existing geometry.

## Side-effect tracker

Code changes likely or possible from each task. Updated as build progresses.

| Task | Type | File | Reason |
|------|------|------|--------|
| T3 | Apply-Patch | `src/freecad_mcp/server.py` | Add screenshot tolerance param (emerged during build). |

## Out of scope (reaffirmed)

Restate the spec's Out-of-scope items here so the build phase has them locally. The Scope-creep reviewer (v2) will use this list.

- ...

---

## Notes for the agent reading this

- Tasks execute in order respecting `Depends on`. Tasks with no shared deps may be dispatched in parallel.
- Each task's dispatched subagent must include the magic comment `# expected_output: <path>` in its prompt so the SubagentStop hook can verify.
- If a task's acceptance fails, do NOT mark it complete. Either retry, refine the spec, or escalate to the user.
- Mark task status inline (`### T3: <title> ✅` or `### T3: <title> ❌ retry`) so the orchestrator can resume.
