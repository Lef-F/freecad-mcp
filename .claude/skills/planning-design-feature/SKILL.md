---
name: planning-design-feature
description: Reads an approved design spec and produces an ordered task plan with archetype-tagged subagent dispatches. Second phase of spec-driven-design.
---

# Planning a Design Feature

## When to Use

- A spec exists at `.designs/<doc-name>/journal/<feature-slug>/spec.md` with `Status: approved`.
- The user (or orchestrator) requests the plan phase.

Do NOT use if:
- Spec is `draft` (run `writing-design-spec` to approve first).
- A `plan.md` already exists with `Status: approved` (re-planning needs explicit user confirmation; usually you should iterate the existing plan instead).

## Prerequisites

1. Read the spec fully.
2. Read `.designs/<doc-name>/objects.md` and `tasks.md` for context.
3. Read any referenced `.claude/context/*.md` files cited in the spec's References section.
4. Confirm the active FreeCAD document matches the spec's document.

## Steps

### 1. Map acceptance criteria to required work

For each numbered Acceptance criterion in the spec, identify:
- What FreeCAD geometry needs to be created / modified.
- What investigations are needed first (positions, intersections, materials, references).
- What side-effect code might be needed (new MCP tool? addon fix? skill update?).

This is in-thread reasoning, not a subagent dispatch. Use AskUserQuestion only if the spec is ambiguous about an acceptance criterion (which should be rare since the spec was just approved).

**Verify live-model identifiers before any mutation task depends on them.** Any identifier the plan relies on that describes live application/document state (a property name, type id, object/field name, API signature) MUST be either (a) verified this session via a read-only discovery query, or (b) explicitly marked "assumed -- a preceding discovery/Explore task verifies it". Never let a mutation (RPC-Exec / Apply-Patch) task be the first thing to touch an unverified identifier: a wrong assumed identifier propagates verbatim into the dispatch prompt and either fails loudly or, worse, mutates the wrong thing silently. If in doubt, order an Explore task first.

### 2. Decompose into tasks

Each task has a single archetype from: `Explore`, `Research`, `RPC-Exec`, `Apply-Patch`, `Review`.

Guidelines:
- **Explore** when you need to investigate FreeCAD source, the active document state, or codebase before knowing the answer.
- **Research** when you need external authoritative info (regs, library docs). Pre-check WebFetch / WebSearch permissions before scheduling.
- **RPC-Exec** for FreeCAD geometry creation / modification. One coherent execute_code call per task.
- **Apply-Patch** for surgical code edits with known before / after.
- **Review** after a build cluster, before the closing phase (but most reviews happen in the dedicated review phase, not here).

Keep tasks small enough that the dispatched subagent has a focused, well-scoped job. If a task has more than 4 sub-bullets in its Inputs, split it.

### 3. Order and dependencies

Number tasks T1, T2, .... Use `Depends on:` to mark explicit ordering. Tasks with no shared dependencies CAN be dispatched in parallel - flag these for the build phase.

Visualisation milestones go between build tasks: schedule a screenshot via `get_view` after any geometry change that should be visually verified.

### 4. Write the plan from the template

Copy `reference/plan-template.md` to `.designs/<doc-name>/journal/<feature-slug>/plan.md`. Fill in:
- Strategy: 2-3 sentence high-level approach.
- Tasks: full list with all fields. Each task's Expected output is a file path under `journal/<feature-slug>/build/<task-id>.md` (or research/reviews subdirs).
- Visualisation milestones.
- Side-effect tracker (start empty; build phase fills it).
- Out of scope: restate from the spec.

### 5. Pre-flight check the plan

Before requesting approval, verify:
- [ ] Each task has a single archetype.
- [ ] Each task's Inputs reference real files that exist (`stat` them) or note them as outputs of an earlier task.
- [ ] Each task's Expected output path is under the journal directory.
- [ ] Each task's Acceptance criterion is checkable.
- [ ] Tasks needing WebFetch have a `Research` archetype and the parent has confirmed web tools are permitted.
- [ ] No mutation task (RPC-Exec / Apply-Patch) hard-codes a live-model identifier that hasn't been verified this session or flagged for a preceding discovery task.

If any check fails, fix the plan before asking for approval.

### 6. Ask the user to approve

Show the plan. Confirm:
- Task decomposition makes sense (no over-decomposition, no missing work).
- Dependencies are right.
- Visualisation milestones cover the critical geometry changes.

Set **Status: approved** only after agreement.

### 7. Update `.designs/<doc-name>/tasks.md`

Update the row added by the spec phase to reflect plan approval:
```markdown
- [ ] <feature-name> -> `journal/<feature-slug>/plan.md` (status: approved, ready to build)
```

## Verification

- [ ] Plan file exists with all sections filled.
- [ ] Status is `approved`.
- [ ] Every task has Archetype, Depends on, Inputs, Expected output, Acceptance.
- [ ] Side-effect tracker section exists (even if empty).
- [ ] User has confirmed in chat.

## Anti-patterns

- One mega-task that does everything (split it).
- Tasks with vague archetypes ("do whatever's needed"). Pick one.
- Skipping the Acceptance line on a task (the build phase needs it to know if the task succeeded).
- Putting reviewers in the build plan. The review phase is separate.

## Next phase

After plan approval, `dispatching-design-subagents` executes tasks in order respecting dependencies.
