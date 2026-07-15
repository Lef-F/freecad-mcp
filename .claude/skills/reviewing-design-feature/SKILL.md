---
name: reviewing-design-feature
description: Runs Correctness and Conventions reviewers in parallel against a feature's build outputs, then an integration pass that dedupes findings and surfaces contradictions. Fourth phase of spec-driven-design.
---

# Reviewing a Design Feature

## When to Use

- A feature's build phase is complete (all tasks in `plan.md` are marked done).
- About to close the feature, but want a pair of eyes before commit / merge.
- A specific concern: the user (or the parent) suspects a problem and wants a focused review.

Do NOT use for:
- Reviewing arbitrary code outside a planned feature (use `superpowers:requesting-code-review`).
- Reviewing before build is complete (premature, the reviewer has no diff to look at).

## Prerequisites

1. `journal/<feature-slug>/spec.md` and `plan.md` exist.
2. `journal/<feature-slug>/build/` contains the per-task artefacts.
3. The change manifest is derivable from the build files OR the side-effect tracker in `plan.md`.

## Steps

### 1. Build the change manifest

Walk the plan and the build files. Produce a structured list of WHAT changed:
- FreeCAD objects created / modified / deleted (from RPC-Exec task artefacts).
- Source files edited (from Apply-Patch task artefacts + side-effect tracker).
- Documentation / context files updated.

This manifest is fed verbatim into both reviewers. Without it, they hallucinate context.

### 2. Generate hypotheses to verify

Read the Correctness brief (`reference/correctness-brief.md`). For each significant change in the manifest, draft 3-8 specific hypotheses (concrete bug claims). If you cannot draft hypotheses, run an Explore dispatch FIRST to surface them.

Examples of good hypotheses:
- H1. The new `Body003` does not propagate Placement updates to its sketches.
- H2. The screenshot screenshot capture happens before recompute, so the new geometry isn't visible.
- H3. `MCP_Role` is set to `"Intermediate"` on the helper objects but the spec called for them as `Alternative`.

### 3. Dispatch the two reviewers in parallel

Use `dispatching-design-subagents` with the Review archetype. Two subagents in one message:

**Grant reviewers read-only live-state access when the feature mutated live state.** This is the single biggest reducer of reviewer hallucination: a reviewer that can query the running model verifies its hypotheses first-hand instead of inferring them from the build artifact (the exact "reviewer trusts a stale/wrong build log" failure these reviews exist to catch). Add the read-only live-model query tool to both reviewers' dispatch prompts; give the Conventions reviewer read-only `Bash` too (working-tree diff, encoding scans). Keep the no-source-write / no-test-execution prohibition.

**Correctness reviewer**
- Reference: `.claude/skills/reviewing-design-feature/reference/correctness-brief.md`
- Inputs: build files + spec.md + changed source files
- Hypotheses: from step 2
- Expected output: `journal/<feature-slug>/reviews/correctness.md`

**Conventions reviewer**
- Reference: `.claude/skills/reviewing-design-feature/reference/conventions-brief.md`
- Inputs: build files + spec.md + changed source files + CLAUDE.md + relevant `.claude/context/*.md`
- Hypotheses: not needed (the conventions checklist is the hypothesis set)
- Expected output: `journal/<feature-slug>/reviews/conventions.md`

Both subagent prompts MUST include `# expected_output: <absolute-path>`. After they return, the parent reads each review file directly to confirm it landed (the SubagentStop hook is advisory only; never rely on its silence).

### 4. Wait for both reviewers

Once both return:
1. Read each file (chat replies should be tiny summaries; the file has the detail).
2. Confirm the SubagentStop hook didn't warn about missing files.
3. Parse the claims ledgers. Note any `unverified` or `assumption` rows that matter.

### 5. Dispatch the integration pass

A third subagent that takes both review files as inputs and produces `journal/<feature-slug>/reviews/integration.md`. Its job:
- Dedupe findings (same bug reported by both reviewers).
- Surface contradictions (e.g., Correctness says fix X by removing Y; Conventions says Y is required).
- Re-rank severity using a single rubric (bugs > improvements > nitpicks).
- Mark which findings are must-fix vs. nice-to-have for this feature.

Integration subagent prompt skeleton:

```
PURPOSE: Reconcile two parallel review findings into a single must-fix vs nice-to-have list.

INPUTS:
- /absolute/path/to/journal/<feature-slug>/reviews/correctness.md
- /absolute/path/to/journal/<feature-slug>/reviews/conventions.md
- /absolute/path/to/journal/<feature-slug>/spec.md (for the acceptance criteria)

QUESTIONS:
1. Are there findings that appear in both reviews? Merge them.
2. Are there contradictions between the two? List each contradiction with the conflicting recommendations.
3. For each finding, mark "must-fix" (blocks acceptance criteria) or "nice-to-have" (improves quality).
4. Are any of the spec's Acceptance criteria definitively NOT met by the build?

CONSTRAINTS:
- Do NOT add new findings of your own; only reconcile what's already there.
- Citations carry over from the source files (do not re-derive).

RETURN: Write to <journal-path>/reviews/integration.md with sections:
- Must-fix (with merged citations)
- Nice-to-have (with merged citations)
- Contradictions (with proposed resolution)
- Acceptance status (per spec criterion)
- Claims ledger

Your chat reply: file path + must-fix count + contradiction count.

# expected_output: <journal-path>/reviews/integration.md
```

### 6. Decide and act

Read `integration.md`. Present the must-fix list to the user. For each:
- Fix it (loop back through `dispatching-design-subagents` with a new Apply-Patch task).
- Defer it (mark in `plan.md` side-effect tracker as a follow-up).
- Dismiss it (annotate why; reviewers do hallucinate).

When all must-fix items are resolved, advance to `closing-design-feature`.

## Verification

- [ ] `journal/<feature-slug>/reviews/correctness.md` exists and is non-empty.
- [ ] `journal/<feature-slug>/reviews/conventions.md` exists and is non-empty.
- [ ] `journal/<feature-slug>/reviews/integration.md` exists and is non-empty.
- [ ] No SubagentStop hook warnings since the dispatch.
- [ ] Claims ledger in each review checked; unverified rows escalated.
- [ ] Must-fix items either resolved or moved to follow-up.

## Anti-patterns

- Skipping the change manifest (reviewers reconstruct blindly and hallucinate).
- Open-ended hypotheses ("find bugs"). The Correctness brief rejects these.
- Skipping the integration pass. Two parallel reviewers without integration leaves you with N reports and no resolution path.
- Acting on a reviewer's claim without checking the claims ledger for `unverified` / `assumption`.
- Inflating Conventions findings (cap nitpicks at 2 per review).

## Key references
- `reference/correctness-brief.md`
- `reference/conventions-brief.md`
- `.claude/skills/dispatching-design-subagents/reference/review-template.md` (the prompt skeleton)

## Next phase

After all must-fix items are resolved, invoke `closing-design-feature`.
