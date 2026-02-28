---
name: scaffolding-skill
description: Creates a new skill directory with the correct structure, naming conventions, and SKILL.md template.
---

# Scaffolding a New Skill

## When to Use
When a recurring workflow should be codified as a reusable skill.

## Arguments
- **name** (required): gerund-form kebab-case (e.g., `optimizing-screenshots`)
- **description** (required): what the skill does, third person
- **needs-reference** (optional): whether to create a `reference/` subfolder

## Steps

### 1. Create directory structure
```
.claude/skills/<name>/
  SKILL.md
  reference/       # only if needs-reference is true
```

### 2. Generate SKILL.md
Use this template:

```markdown
---
name: <name>
description: <description>
---

# <Title Case of Name>

## When to Use
<Describe trigger conditions>

## Steps

### 1. <First step>
<Details>

## Verification
<How to confirm success>
```

### 3. Review against conventions
- Read `.claude/rules/skill-conventions.md`
- Ensure SKILL.md is under 500 lines
- Ensure reference files are self-contained (no cross-references)
- Verify the "When to Use" section has clear trigger conditions
- Confirm there's a "Verification" section with concrete checks

## Verification
- Directory exists at `.claude/skills/<name>/`
- SKILL.md has valid frontmatter with `name` and `description`
- File is under 500 lines
