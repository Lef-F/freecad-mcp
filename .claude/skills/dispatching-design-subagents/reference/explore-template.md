# Archetype: Explore

Read-only investigation of the codebase or FreeCAD source. Produces a structured findings doc.

## When to use
- The parent doesn't yet know what the right answer / approach is.
- Need to map a region of the codebase (e.g., "how is X implemented across these 5 files").
- Need to verify hypotheses against actual source before planning.

## When NOT to use
- The parent already knows the answer and just needs to apply it (use Apply-Patch).
- The work requires external resources (use Research with WebFetch).
- The work needs FreeCAD to be running (use RPC-Exec).

## Required tool surface
- `Read`, `Grep`, `Glob`
- `Bash` for `find`, `wc`, simple shell ops (no installs, no edits)

No Edit, no Write to source files. The subagent writes ONLY its findings file.

## Prompt template

```
PURPOSE: <one-line goal, e.g., "Map how MCP_Role is read by show_by_role across the visibility system">

CONTEXT (parent's current understanding, if any):
- <bullet>
- <bullet>

QUESTIONS (numbered, specific):
1. <question with a file/line hint or grep target>
2. <question>
3. <question>
...

SEARCH HINTS (where to look):
- `addon/FreeCADMCP/rpc_server/rpc_server.py`
- `.claude/context/freecad-visibility.md`
- `grep -rn "MCP_Role" .claude/ addon/`
- vendor/FreeCAD/src/Mod/<...> if applicable

CONSTRAINTS:
- Do NOT propose code changes (this is investigation only)
- Do NOT use WebFetch or WebSearch (local code only)
- Cite every claim with (file, line) or grep evidence

RETURN: Write findings to `<journal-path>/research/<topic-slug>.md`. Structure:
- One section per numbered question, in order
- Each section starts with the question, then the answer with citations
- End with `## Open questions` for things you could not verify

Your chat reply: file path + 5-line executive summary + count of questions answered vs deferred.

# expected_output: <journal-path>/research/<topic-slug>.md
```

## Pre-flight checks (parent runs before dispatching)
1. All cited paths exist (`stat`).
2. Number of questions is between 1 and 8 (more → split into multiple Explores).
3. The journal `research/` subdir exists.
4. If exploring vendor FreeCAD source, confirm `vendor/FreeCAD/` is present (run `scripts/setup-freecad-source.sh` if not).

## Anti-patterns to avoid
- "Comprehensive deep dive into entire .claude/ directory" - produces 23 KB of narrative prose, useless. Replace with 6 specific questions.
- "Find any bugs in X" - too open. Use Review archetype with specific hypotheses instead.
- Returning the full research inline in chat - always go through the file.

## Evidence this works
- `agent-a5fa986f37f83b667`: 8 numbered questions about DrawViewDimension → 8-section answer mirroring the structure + "Known Limitations" appendix. Perfect adherence.
- `agent-a323941f74b391997`: 7 numbered Placement/transform questions with line-number hints → exact answers with source citations.

## Evidence of failure when violated
- `agent-aa0046e1baf27d790`: "Read EVERY file" with no narrowing → 23 KB of unstructured narrative.
