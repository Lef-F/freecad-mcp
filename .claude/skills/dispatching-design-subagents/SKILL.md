---
name: dispatching-design-subagents
description: Dispatches subagents with typed archetypes (RPC-Exec, Apply-Patch, Explore, Research, Review), pre-flight checks, and a magic expected_output comment for hook-based verification. Third phase of spec-driven-design.
---

# Dispatching Design Subagents

## When to Use

- A plan exists at `.designs/<doc-name>/journal/<feature-slug>/plan.md` with `Status: approved`.
- About to execute one or more tasks from that plan.

Do NOT use for:
- One-off subagent calls outside a planned feature (use the Agent tool directly).
- Tasks the parent could do in-thread cheaper (small `execute_code` calls under 20 lines).

## Prerequisites

1. Plan is approved.
2. The journal directory exists with `research/`, `build/`, `reviews/` subdirs.
3. The active FreeCAD document matches the plan's document (if RPC-Exec tasks are involved).
4. Read `.claude/rules/development-patterns.md` for project conventions to enforce.

## Steps

### 1. Pick the next task

Read `plan.md`. Find the next task with all dependencies met (no `Depends on:` entry that isn't marked done). Multiple independent tasks may be dispatched in parallel.

### 2. Pick the archetype reference

Each task has a single archetype tag. Read the matching reference file:
- `RPC-Exec` -> `reference/rpc-exec-template.md`
- `Apply-Patch` -> `reference/apply-patch-template.md`
- `Explore` -> `reference/explore-template.md`
- `Research` -> `reference/research-template.md`
- `Review` -> `reference/review-template.md`

The reference defines: required tool surface, prompt template, pre-flight checks, anti-patterns.

### 3. Run pre-flight checks

Per archetype reference. Common checks:
- All Input file paths exist (`stat` each).
- Required tools are permitted in this session (for Research: probe WebFetch / WebSearch).
- Output path is under `journal/<feature-slug>/` (build / research / reviews subdir).
- Constraints from CLAUDE.md and the feature spec are listed in the prompt.

If a check fails, do NOT dispatch. Either fix the gap (e.g., create the missing dir) or escalate to the user (e.g., permissions denied).

### 4. Fill in the prompt template

Copy the archetype's template. Fill in:
- PURPOSE
- BACKGROUND / CONTEXT (cite the spec and plan by file path)
- TASK / EXACT CHANGE REQUIRED / QUESTIONS (per archetype)
- CONSTRAINTS (start with the archetype defaults, add task-specific)
- RETURN (always file-writing + summary; never full inline)
- `# expected_output: <absolute-path>` magic comment at the end

The magic comment is the contract enforced by the SubagentStop hook (`.claude/hooks/subagent-output-check.py`). It MUST be the absolute path the subagent will write to.

### 5. Dispatch

Use the Agent tool. Subagent type: `general-purpose` (typed archetypes are enforced via prompt + tool surface caveats in the template; future versions may use dedicated subagent_type entries).

For parallel-eligible tasks, dispatch them in a single message with multiple Agent tool uses.

### 6. Wait, verify, integrate

When the subagent returns:
1. Read its chat summary (should be a file path + 3-10 lines).
2. Confirm the file at the magic comment path exists and is non-empty.
3. If the SubagentStop hook warned that the file is missing, the subagent failed its contract: re-dispatch with explicit reminder, or escalate.
4. Update the plan: mark the task with a check or annotate failure.
5. Update the side-effect tracker if the task surfaced code changes.

For Review-type subagents: parse the claims ledger. If any `unverified` or `assumption` rows are load-bearing for the next task, dispatch a follow-up to verify them before proceeding.

### 7. Repeat

Loop to step 1 until all tasks in the plan are done or a task blocks on user input.

## Verification (per task)

- [ ] The expected_output file exists and is non-empty.
- [ ] The task's Acceptance criterion in the plan is met (read the file and confirm).
- [ ] Plan is updated with task status.
- [ ] If side-effect code emerged, side-effect tracker has a row.

## Verification (per batch)

After all tasks done:
- [ ] All build files exist under `journal/<feature-slug>/build/`.
- [ ] All research files exist under `journal/<feature-slug>/research/`.
- [ ] FreeCAD document still opens and `doc.save()` succeeds.
- [ ] `show_by_role(doc, ["Final"])` shows the expected scene.

## Anti-patterns

- Dispatching without the `# expected_output:` magic comment. The hook can't verify silently.
- Dispatching a Review without specific hypotheses (use Explore first, OR provide the hypotheses).
- Dispatching parallel Research subagents that all hit the same URL (sibling-cancellation will nuke the batch - go serial).
- Letting a subagent return prose in chat instead of writing to file. If the return is more than 10 lines of content, the contract was violated.
- Marking a task done because the subagent claimed success. Verify the file and the acceptance.

## Key references
- `reference/rpc-exec-template.md`
- `reference/apply-patch-template.md`
- `reference/explore-template.md`
- `reference/research-template.md`
- `reference/review-template.md`
- `.claude/hooks/subagent-output-check.py` (the verifier hook)

## Next phase

After all tasks in the plan are done (or marked as deferred), invoke `reviewing-design-feature`.
