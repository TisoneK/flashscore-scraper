# Role Overlay: Feature Engineer (design + build)

> Overlay on a base edition — see `roles/README.md` for how overlays bind.
> This role exists because the base editions are written for **sweep
> sessions** (discover → review → fix), and a feature request is a
> different shape of work: there is nothing to "review" yet — there is
> something to **design, build, and verify**. Without this overlay,
> agents handed a feature Target improvise a reinterpretation of the
> phases; with it, feature sessions are first-class. Use it whenever the
> Target is `feature <description>` or the chat message asks for new
> functionality rather than fixes.

## Session Parameter Overrides

- **Scope:** design + implement + verify the requested feature
- **Target:** `feature <description>` — from the chat message (which wins)
  or the kickoff's Target field
- **Findings handling:** fix safe issues **in code the feature touches**;
  backlog unrelated findings with file paths and severity. A feature
  session must not silently become a general sweep — but Pitfall #37
  still applies: a safe one-liner you're already staring at gets fixed,
  not backlogged.
- **Deliverable:** feature report in
  `.context/memory/reviews/YYYY-MM-DD-feature-review.md` + chat summary
- **Allowed commits:** `feat(<area>):` for the feature (plus `fix:`/
  `test:`/`docs:` where a touched-code fix, test, or doc change stands
  alone), `docs(review):` for the report, `chore(context):` for memory.

## Execution changes vs the base edition

- **Phase 1 (Steps 1–8) runs as written**, with one scoping change:
  discovery reads the code the feature **touches plus its blast radius**
  (callers, config, tests, deploy surface) — not the whole codebase.
  Baseline health checks (Step 8) are NOT optional: you cannot claim the
  feature didn't break anything without knowing what was broken before.
- **Phase 2 (Step 9) becomes DESIGN, not review.** Before writing any
  code: enumerate the decisions the feature forces (topology, data model,
  API shape, dependency choices), pick, and record each nontrivial one as
  an ADR entry in `.context/memory/plans/decisions.md` — decision, alternatives
  considered, consequences. Respect existing entries there (Pitfall:
  don't "fix" the codebase into violating a prior decision). Small
  features may have exactly one decision; record it anyway — the next
  agent needs to know it was a choice, not an accident.
- **Phase 3 (Steps 10–12) becomes IMPLEMENT.** Build in reviewable
  increments, one logical change per commit. Every quality gate that
  binds a fix binds the implementation: tests for new behavior,
  traversal tests for any user-input→path join (Pitfall #35), schema
  validation for any IaC file (Pitfall #36), lint/typecheck clean.
  Verify the feature end-to-end before calling it done — "it compiles"
  is not verification. If the environment can't run the real thing
  (no Docker, no external service), verify what you can, say exactly
  what you couldn't, and tell the user what to run where.
- **Step 13 — the report is a FEATURE report**, structured as:
  1. Executive Summary (what was requested, what shipped)
  2. Design Decisions (the ADRs, summarized, linked to `plans/decisions.md`)
  3. What Was Built (per-commit map)
  4. What Was Verified (and how — commands, tests, evidence)
  5. What Was NOT Verified (and what the user should check)
  6. Open Items / Backlogged findings
- **Step 14 (changelog) runs as written** — a feature is exactly what a
  changelog is for.
- **Steps 15–19 run as written.**

## Role checklist

- **The Target's acceptance shape is stated before Phase 3** — one
  sentence in the design: "done means X works, verified by Y." If the
  request is too vague to write that sentence, that is genuine ambiguity
  (Pitfall #30's exception) — ask, once, with a recommendation.
- **New surface = new tests.** Behavior added without a test covering it
  is not done.
- **Security review of the new surface only** — auth on new endpoints,
  input validation, path/URL handling, secrets handling. The feature's
  attack surface is this session's responsibility even though a general
  security sweep is not.
- **Docs updated where the feature changes usage** — README, `.env.example`,
  API docs. Doc drift the feature *causes* is in scope; pre-existing
  drift is a backlog entry.

## What this role does NOT do

- **No general sweep** — findings in untouched code go to the backlog,
  not into this session's diff (except safe one-liners per Pitfall #37).
- **No silent scope growth** — if implementation reveals the feature
  needs an architectural change the user didn't ask for, that's a
  design decision to surface in the report (or, if blocking, genuine
  ambiguity to ask about) — not something to just do.
- **No skipping design because the feature "is simple"** — the one-ADR
  minimum stands. Skipping Phase 2 is the feature-session equivalent of
  skipping Phase 1.
