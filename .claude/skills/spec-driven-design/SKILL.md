---
name: spec-driven-design
description: Orchestrator for design-session features. Detects the current journal state of the active FreeCAD document and routes to the right phase skill (writing-design-spec, planning-design-feature, dispatching-design-subagents, reviewing-design-feature, closing-design-feature). Entry point for the /sdd flow.
---

# Spec-Driven Design Orchestrator

## When to Use

- User says `/sdd`, "let's run spec-driven design", "do this the structured way", or similar.
- User starts a new design session and you want to anchor it in the journal.
- Resuming work on a feature mid-flow (the orchestrator detects state and picks up).

Skip the orchestrator and invoke phase skills directly when:
- User explicitly wants only one phase (e.g., "just write the spec").
- The work is so small that the structured flow is overkill (1-2 execute_code calls).
- The user is mid-flow and references a phase by name.

## Principles

This is glue, not a re-implementation. The orchestrator's job is to:
1. Know the journal directory layout and current state.
2. Pick the right phase to run next.
3. Hand off to the phase skill cleanly.
4. Track progress across the lifecycle in `tasks.md` and `closeout.md`.

Each phase skill owns its own steps and verification. The orchestrator does not re-explain the phases; it routes.

## Prerequisites

1. A FreeCAD document is active (`mcp__freecad__list_documents`).
2. `.designs/<doc-name>/` exists.
3. The user has either named a feature slug or wants to start a new one.

## Steps

### 1. Identify the active feature

Ask the user (or infer from context) the feature slug. Check `.designs/<doc-name>/journal/<feature-slug>/`:

| Journal state | Next action |
|---|---|
| Directory does not exist | New feature. Run `writing-design-spec`. |
| `spec.md` exists, Status: draft | Resume spec. Run `writing-design-spec`. |
| `spec.md` exists, Status: approved, no `plan.md` | Run `planning-design-feature`. |
| `plan.md` exists, Status: draft | Resume plan. Run `planning-design-feature`. |
| `plan.md` Status: approved, some tasks unmarked | Run `dispatching-design-subagents`. |
| All tasks marked done, no `reviews/integration.md` | Run `reviewing-design-feature`. |
| `integration.md` exists with unresolved must-fix items | Resolve them (loop through `dispatching-design-subagents` with new Apply-Patch tasks), then re-review. |
| All must-fix resolved, no `closeout.md` with `Status: done` | Run `closing-design-feature`. |
| `closeout.md` Status: done | Feature is closed. Ask user what's next. |

### 2. Pre-flight checks (regardless of phase)

- Active FreeCAD document name matches the feature's expected document (read from `spec.md` front matter if it exists).
- Required tools for the upcoming phase are permitted (esp. WebFetch / WebSearch for any Research dispatches).
- The em-dash hook and SubagentStop hook are configured (smoke-check by running `ls .claude/hooks/`).
- `.designs/<doc-name>/` exists and is gitignored (sanity check; should always be true).

### 3. Hand off to the phase skill

Invoke the phase skill explicitly via the Skill tool. The orchestrator does not do the phase's work itself.

When the phase skill finishes, return to step 1 to determine the next phase. Loop until either:
- The feature is closed (closeout.md done).
- The user pauses the flow.
- A phase produces an error or escalates a decision.

### 4. Lightweight status updates

Before each phase handoff, show the user a 3-line status:
- Current feature: `<slug>`
- Current phase: `<phase name>`
- Why: `<one-line reason>`

After each phase, the orchestrator updates `.designs/<doc-name>/tasks.md` with the feature row.

## Verification (per orchestration cycle)

- [ ] The next phase chosen matches the journal state per the table.
- [ ] Pre-flight checks all passed.
- [ ] User has visibility into what's happening (status update shown).
- [ ] After phase completion, journal state was actually advanced (the phase skill's own verification passed).

## Verification (per feature)

- [ ] `closeout.md` Status: done.
- [ ] All Acceptance criteria from `spec.md` are Met or explicitly deferred with rationale.
- [ ] `.designs/<doc-name>/objects.md` updated.
- [ ] `.designs/<doc-name>/tasks.md` reflects the feature as done.

## Anti-patterns

- Running phases out of order (e.g., dispatch before plan approved). The journal-state table prevents this.
- Doing phase work inline instead of invoking the phase skill (defeats the purpose of structure).
- Skipping pre-flight checks for "small" features. Small features are where silent failures bite hardest.
- Treating the orchestrator as a magic wand. The user still has to approve specs and plans; the orchestrator just enforces the order.
- Hidden parallelism. Dispatching multiple features at once across one document fights itself in FreeCAD (single-threaded). One feature at a time.

## Key references
- `.claude/skills/writing-design-spec/`
- `.claude/skills/planning-design-feature/`
- `.claude/skills/dispatching-design-subagents/`
- `.claude/skills/reviewing-design-feature/`
- `.claude/skills/closing-design-feature/`
- `.claude/hooks/subagent-output-check.py`

## How to invoke

Slash command (suggested): `/sdd [feature-slug]`. If the slash command isn't wired yet, just invoke this skill explicitly via the Skill tool and pass the feature slug.

## What's intentionally NOT here (v1)

- No parallel-feature orchestration (one feature at a time).
- No cross-document orchestration (each feature attaches to a single FreeCAD doc).
- No enforcement (advisory only; SubagentStop hook warns but doesn't block).
- No Scope-creep or DevEx reviewer (only Correctness + Conventions in v1).
- No TDD bridge for addon code (deferred).

If you (the agent) feel one of these is needed, surface it to the user as a v2 candidate rather than improvising.
