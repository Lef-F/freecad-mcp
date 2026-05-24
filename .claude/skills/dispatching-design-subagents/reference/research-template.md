# Archetype: Research

External-knowledge investigation (web docs, regulations, library APIs). Distinct from Explore because it needs WebFetch / WebSearch.

## When to use
- Need authoritative info from outside the repo: Boverket regulations, Three.js API docs, FreeCAD wiki, Claude Code documentation.
- Verifying a third-party library's API surface before writing code that depends on it.

## When NOT to use
- The info is in the repo / vendor source (use Explore).
- The info is already in `.claude/context/` (read it directly - no subagent needed).

## Required tool surface
- `WebFetch`
- `WebSearch`
- `Read` (for local cross-reference)

## CRITICAL pre-flight (parent MUST run before dispatching)

**Verify WebFetch and WebSearch are permitted in the current session.** Run a probe:

```bash
# Quick probe: try fetching a known-safe URL. If it returns a permission denial,
# DO NOT DISPATCH the Research subagent - it will silently fall back to training
# data and confabulate authoritative-looking output.
```

If the probe fails with "Permission to use WebSearch denied", the parent must either:
1. Tell the user and request permission grant.
2. Re-route the task to a different archetype (e.g., Explore using cached local docs).
3. Skip the task and note it as "blocked on permissions" in the plan.

**Never dispatch a Research subagent and hope the web tools work. The May 22 corpus has 14 examples of agents silently confabulating regulation tables from training data when web was denied.**

## Prompt template

```
PURPOSE: <one-line goal, e.g., "Get the exact BBR section 5:3 door egress dimension requirements">

SOURCES (parent verified these are reachable):
- https://www.boverket.se/<...>
- https://three.js.org/docs/<...>

QUESTIONS (numbered, specific):
1. <question - exact paragraph / table / API method to find>
2. <question>

CONSTRAINTS:
- Do NOT answer from training-data knowledge - every claim must come from a successful WebFetch or WebSearch result this turn
- If a fetch returns 404 or is denied, FAIL LOUDLY: stop and report the failure, do not fall back to your prior knowledge
- Cite source URL + section number / heading for every claim
- ASCII-only output (no special chars)

RETURN: Write structured findings to `<journal-path>/research/<topic-slug>.md`:
- Source URL list at top (with HTTP status for each)
- One section per numbered question with answer + citation
- Confidence note per claim (high if direct quote, medium if paraphrased)
- `## Open questions` for things sources didn't cover

Your chat reply: file path + 5-line summary + count of citations.

# expected_output: <journal-path>/research/<topic-slug>.md
```

## Recovery if the subagent fails

If the Research subagent returns "all sources denied / 404", do NOT accept its training-data fallback. The skill must instead:
1. Re-probe permissions; if denied, escalate to user.
2. Use sibling-failure protection: dispatch Research subagents serially (one URL at a time), not in parallel - one bad URL cancels every sibling.
3. If the source is genuinely unreachable, downgrade to Explore using cached / vendored local copies if any exist.

## Evidence of failure when web tools were denied
- `agent-a142225523ae8d18a` (BBR rooms): produced a perfect-looking BBR 3:1 / 3:2 table entirely from memory after `WebFetch` denied. Same shape as the prompt asked, no source verifiability.
- `agent-af45034fa65126f5a` (Claude Code Stop hooks): invented a `last_assistant_message` field that does not exist in the schema.

## Evidence of success when web tools worked
- The second BBR fan-out (session `47ef882b`) ran the same 7 prompts with permissions granted and produced cited reference tables that became the `arch-swe-*.md` files in `.claude/context/`.
