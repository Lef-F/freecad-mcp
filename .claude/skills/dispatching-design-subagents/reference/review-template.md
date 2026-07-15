# Archetype: Review

Audit existing code / artefacts against a specific rubric. Output is a severity-tagged findings list.

## When to use
- After a build phase to audit the changes before commit.
- After a research artefact lands to check it for hallucinations / scope issues.
- When the parent suspects bugs and has specific hypotheses to verify (the gold-standard pattern).

## When NOT to use
- Open-ended quality check with no rubric (you'll get noise - 16 KB of mixed-severity findings).
- Reviewing without a change manifest ("look at this file and find issues") - provide concrete hypotheses or a checklist.

## Required tool surface
- `Read`, `Grep`, `Glob`
- **Optional (strongly recommended when the feature mutated live application/document state): a READ-ONLY live-model query tool** (FreeCAD session: `mcp__freecad__execute_code`, `capture_screenshot=False`). This lets the reviewer verify hypotheses against live state FIRST-HAND instead of trusting the build artifact -- which is the single biggest reducer of reviewer hallucination.
- **For the Conventions archetype: read-only `Bash`** for inspecting the working-tree diff (`git status` / `git diff`), scanning artifacts for forbidden characters/encodings, and file stats. No writes, no test/lint execution.

No write to source. The subagent writes ONLY its findings file. Do NOT run linters or tests (that is a separate verification step, not a review).

## Prompt template

```
PURPOSE: <reviewer archetype + scope, e.g., "Correctness review of T3-T7 changes to server.py">

REVIEWER ARCHETYPE: <Correctness | Conventions>
(See reference brief at `.claude/skills/reviewing-design-feature/reference/<archetype>-brief.md` for what to look for)

FILES TO REVIEW (read fully):
- /absolute/path/1
- /absolute/path/2

KEY CHANGES MADE (the change manifest - parent enumerates):
1. <what changed in file 1>
2. <what changed in file 2>
...

HYPOTHESES TO VERIFY (specific bug claims, not open-ended):
H1. <claim - e.g., "the new try/except in line 612 doesn't handle KeyError, which set_object_property can raise">
H2. <claim>
...

QUESTIONS (broader checklist for this archetype - pulled from the reviewer brief):
- Question 1
- Question 2

CONSTRAINTS:
- Stay in scope: only flag issues in the changed lines + 50 lines of context
- Every finding needs (file, line) citation and a quoted code snippet
- Severity rubric: bug / improvement / nitpick (review your finding before submitting - bug = will break in normal use; improvement = could be better; nitpick = style)
- Maximum 10 findings, ranked by severity. If you have more, return top 10.

RETURN: Write findings to `<journal-path>/reviews/<archetype>.md`:
- Front matter: reviewer archetype, files reviewed, total findings count by severity
- One section per hypothesis with Verified? (yes/no/partial) + evidence
- One section "Other findings" for issues not in hypotheses
- `## Claims I am asserting` ledger at the end (see below)

Required claims ledger (shared convention -- see `reference/claims-ledger.md`):
- [verified] each (file, line) or live-query result you cited was observed this turn
- [unverified] anything you could not check (e.g., runtime behavior, downstream effects)
- [assumption] anything you took at face value from the prompt or the build artifact
- [out-of-scope] issues you noticed but did not investigate

Your chat reply: file path + counts (bugs/improvements/nitpicks) + count of unverified claims.

# expected_output: <journal-path>/reviews/<archetype>.md
```

## Pre-flight checks (parent runs before dispatching)
1. The archetype brief file exists at `.claude/skills/reviewing-design-feature/reference/<archetype>-brief.md`.
2. The change manifest is non-empty (without it, the reviewer reconstructs blindly and hallucinates).
3. Hypotheses are concrete (not "find bugs"). If the parent has no hypotheses, run an Explore first.
4. Output file path is under `journal/<feature>/reviews/` for the active feature.

## Anti-patterns to avoid
- Open-ended "review for quality" - gives severity-inflated 16 KB reports.
- Reviewing without the change manifest - reviewer hallucinates context.
- Reviewing multiple unrelated changes in one Review - split by archetype or by file cluster.
- Accepting a review without checking the claims ledger - that's the hallucination filter.

## Evidence this works
- `agent-ad3b35844ecd57116`: 6 numbered hypotheses → 6/6 verified with exact line numbers. The gold standard.
- `agent-a55572fe7ee19b553`: severity-tagged findings, file:line citations, caught a real assignment bug.

## Evidence of failure when violated
- `agent-aa990c50aae8eb15d`: open-ended "review for quality" with 6 orthogonal check-categories → 16 KB report, some nitpicks the user later ignored.
- Reviewer hallucination (`a59df20bfdc565b33`): claimed `FreeCADConnection.disconnect()` would AttributeError, but the call had already been removed in a prior commit. No cross-reviewer integration caught the desync.
