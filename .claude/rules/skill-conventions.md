# Skill Conventions

Guidelines for creating and maintaining skills in `.claude/skills/`.

## Structure

Each skill is a directory under `.claude/skills/` containing:
```
skill-name/
  SKILL.md          # Main instructions (keep under 500 lines)
  reference/        # Optional: supporting docs, lookup tables
  scripts/          # Optional: automation scripts
```

## SKILL.md Format

```markdown
---
name: verb-ing-noun-kebab-case
description: Third-person description of what this skill does and when to invoke it.
---

# Skill Title

## When to Use
Describe trigger conditions.

## Steps
Numbered procedure.

## Verification
How to confirm the skill completed successfully.
```

## Naming

- Directory name: gerund-form kebab-case (e.g., `adding-mcp-tool`, not `add-mcp-tool`)
- Keep names descriptive but concise (2-4 words)

## Content Rules

- Write for Claude as the executor — be precise and procedural
- Don't explain concepts Claude already knows (Python syntax, git commands, etc.)
- Reference existing context files instead of duplicating information
- Include a verification section with concrete checks
- One level of nesting max — `reference/` files should be self-contained
