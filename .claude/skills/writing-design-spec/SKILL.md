---
name: writing-design-spec
description: Captures a design feature's intent into a structured spec.md inside the journal directory of the active FreeCAD document. First phase of the spec-driven-design lifecycle.
---

# Writing a Design Spec

## When to Use

- The user introduces a new piece of work on the active FreeCAD document ("let's add wood fences", "fix the stair carving", "wire up a bike storage door").
- A design session is exploratory but needs structure before turning into action.
- An ad-hoc effort has been going for a while and you realise it deserves journalling.

Do NOT use for:
- Pure code changes unrelated to any FreeCAD document (this skill collection is design-scoped; if a code task is genuinely standalone, run it without the spec-driven flow).
- Re-running a closed feature (start a new feature slug instead).

## Prerequisites

1. A FreeCAD document is active (confirm with `mcp__freecad__list_documents`). The feature attaches to this doc.
2. `.designs/<doc-name>/` exists (per project convention; create if not).
3. Read `.designs/<doc-name>/README.md` and `objects.md` to know the current state. The spec's Background section quotes from these.

## Steps

### 1. Pick a feature slug
Ask the user for a short kebab-case slug if not obvious from context (e.g., `wood-fence-z-placement`, `bike-storage-doors`, `stair-bottom-steps`). Make it specific enough that future-you reading the journal can tell what's there.

### 2. Create the journal directory
```bash
mkdir -p .designs/<doc-name>/journal/<feature-slug>/research
mkdir -p .designs/<doc-name>/journal/<feature-slug>/build
mkdir -p .designs/<doc-name>/journal/<feature-slug>/reviews
```

### 3. Draft the spec from the template
Copy `reference/spec-template.md` to `.designs/<doc-name>/journal/<feature-slug>/spec.md` and fill it in section by section. Use AskUserQuestion to resolve ambiguities BEFORE writing each section, not after.

Order to fill in:
1. **Background** - quote prior conversation, screenshots, or `.designs/<doc>/objects.md` entries.
2. **Goal** - one sentence the next Claude can read cold.
3. **Scope** and **Out of scope** - be specific about FreeCAD objects, geometry, drawings, docs.
4. **Acceptance criteria** - numbered, concrete, verifiable. If you can't make one verifiable, push back and refine.
5. **Constraints** - project invariants are pre-listed; add feature-specific ones.
6. **References** - link to relevant `.designs/`, `.claude/context/`, external docs.
7. **Open questions** - anything that must be answered before moving to plan phase.
8. **Side-effects expected** - anticipated code changes (often unknown at this stage; leave a placeholder).

### 4. Ask the user to approve

Show the user the filled spec. Confirm explicitly:
- Goal is correct.
- Scope and Out-of-scope are right.
- Acceptance criteria are verifiable AND sufficient.
- Open questions are accurate.

Set **Status: approved** in the front matter only after user agreement. Do NOT proceed to plan phase until approved.

### 5. Update `.designs/<doc-name>/tasks.md`

Add a row pointing to the new journal entry so the per-doc task list reflects active work:
```markdown
- [ ] <feature-name> -> `journal/<feature-slug>/spec.md` (status: approved, plan pending)
```

## Verification

- [ ] Spec file exists at the expected path with all sections filled (no `<placeholder>` text left).
- [ ] Status is `approved`.
- [ ] Acceptance criteria are numbered and each one is checkable (no "make it look nice" criteria).
- [ ] `.designs/<doc-name>/tasks.md` references the journal entry.
- [ ] User has confirmed in chat.

## Anti-patterns

- Writing the spec without the user looking. The spec IS the alignment artefact, not a checkbox.
- Vague acceptance criteria like "make it look right". Replace with measurable claims.
- Including implementation details in the spec. Spec says WHAT and WHY; plan says HOW.
- Padding Out-of-scope with everything imaginable. Only list things that might plausibly be in scope.
- Asserting live-model identifiers (property names, type ids, object/field names, API signatures) in the spec's Constraints or References as if they were facts. Unless you confirmed it against the live model this session, tag any such identifier "assumed -- to be verified in the plan/explore phase". An unverified identifier baked into the spec quietly becomes a wrong premise the plan trusts.

## Next phase

After spec approval, the user (or orchestrator) invokes `planning-design-feature` which reads this spec.
