# Flaws (append-only — flows to the protocol package)

Friction caused by **the `.context/` system or the protocol itself** —
not by the project's code, environment, or dependencies. These are
places where the workflow didn't guide the agent well enough, a rule
was ambiguous, a step was missing, or a template was confusing.

Project-level friction (the codebase, the toolchain, the environment)
goes in `../inefficiencies/log.md` — **not here**. The split:

| If the friction is about... | It goes in... |
|---|---|
| The project's code, tests, deps, env, CI | `inefficiencies/log.md` |
| The protocol steps, the `.context/` rules, a template, a missing rule | `flaws/log.md` (this file) |

## How these get fixed

This file is the **source of truth** inside this project. Periodically —
or when a pattern repeats across sessions — the flaws here are
back-ported to the protocol package (the "Package upstream" URL in
`../workflows/active.md` — the repo that `core/` is vendored from). The
package fix might be: a new pitfall, a reworded step, a new template
field, a schema change, or a new core release. It reaches this project
on the next `context-sync update`.

When a flaw is fixed in the package, append a "Fixed in package" line
to the entry here — don't delete the original. The history of what was
wrong and what fixed it is how the next agent learns the protocol's
evolution.

## Two surfaces — know which one you're editing

Every repo managed by this protocol has **two surfaces**:

1. **The project** — product code, docs, tests, config. Commits use
   normal prefixes (`fix:`, `feat:`, `docs:`). Friction with the project
   goes in `inefficiencies/log.md`.
2. **`.context/`** — agent memory. Commits use `chore(context):`. Friction
   with the `.context/` system or the protocol goes in `flaws/log.md`
   (this file).

When you catch yourself confused about which surface you're on, that
confusion is itself a flaw — log it here.

## Format

```
---
## YYYY-MM-DD — <agent> / <model> (Session N)

- **Flaw:** <what in the protocol or .context/ system didn't work>
- **Symptom:** <what happened to the agent — the observable friction>
- **Root cause:** <why the protocol/.context/ let this happen>
- **Suggested fix:** <concrete change to the package — a step, a pitfall,
  a template, a rule>
- **Status:** open | fixed in package <commit-sha or date>
```
