# Shared convention: the claims ledger

Every artifact-producing subagent (Explore, RPC-Exec, Review) ends its output file with a **claims ledger**: a four-state list separating what the subagent actually proved from what it assumed or left unchecked. This is the single most effective mechanism for stopping a confident-but-wrong subagent result from propagating downstream.

## The four states

```
## Claims I am asserting
- [verified]    <claim> + the evidence (tool output, file:line, query result) that proves it
- [unverified]  <claim the subagent believes but did NOT confirm this run> + why not
- [assumption]  <something taken at face value from the prompt / prior artifact, not re-checked>
- [out-of-scope] <noticed but deliberately not investigated> + where it should be handled
```

## Why it matters

- **Downstream phases target the weak rows.** A reviewer reads the build subagent's `[unverified]` and `[assumption]` rows and verifies exactly those. An integration pass routes `[out-of-scope]` rows to follow-ups instead of must-fix.
- **It exposes scope creep.** If `[out-of-scope]` has entries, the parent can decide whether to dispatch follow-ups.
- **It defeats the "plausible table" failure.** A subagent that fills a structured report from memory (because a tool was denied) must, under this convention, mark those rows `[unverified]` or `[assumption]` instead of presenting them as fact.

## Rules

- A claim is `[verified]` ONLY if the subagent observed the supporting evidence in a tool result THIS run. Prior-knowledge or prompt-restated facts are `[assumption]`, not `[verified]`.
- Any identifier the subagent asserts about live application/document state (a property name, type id, object/field name, API signature) is `[assumption]` until a read-only query confirmed it this run.
- Keep it short: one line per claim, evidence inline.

This convention is referenced by `explore-template.md`, `rpc-exec-template.md`, and `review-template.md`. Define it here once; do not redefine it per template.
