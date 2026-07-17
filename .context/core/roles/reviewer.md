# Role Overlay: Reviewer (read-only)

> Overlay on a base edition — see `roles/README.md` for how overlays bind.
> This role audits and reports; it changes **no product code and no docs**.
> The only commits it makes are the review report and the `.context/`
> memory updates. Use it for frequent low-stakes audits, for agents that
> shouldn't have write access to product code, or as the scouting pass
> before a full engineer session.

## Session Parameter Overrides

- **Scope:** discovery + review + report — **no fixes of any kind**
- **Findings handling:** report everything; fix nothing. Every actionable
  finding becomes a `.context/memory/tasks/backlog.md` entry.
- **Deliverable:** `.context/memory/reviews/YYYY-MM-DD-review.md` + chat summary
- **Allowed commits:** `docs(review):` (the report) and `chore(context):`
  (memory updates) only. Nothing else gets committed.

## Execution changes vs the base edition

- **Steps 1–9 run as written** (setup, `.context/` read, install, docs,
  discovery, baseline health, review). Installing dependencies and running
  health checks is still required — a review without a baseline is a guess.
- **Phase 3 (Steps 10–12) is skipped** — no fixes, no code commits. The
  push workflow is still used for the report and `.context/` commits.
- **Step 14 (changelog) is a no-op** — no behavior changed, so there is
  nothing to add. Note "N/A — read-only session" in the report.
- **Steps 13, 15–19 run as written.**

## Role checklist

Everything in the base edition's review sections (Code Review Checklist,
Security, Performance, UX/UI, Documentation) applies — the difference is
that findings end in the report and backlog instead of commits. In
addition, because this role's entire value is the handoff:

- **Every Critical/High finding gets a backlog entry** written so a fresh
  engineer session can act without this session's chat history: file paths,
  the failing scenario, the recommended fix, severity.
- **Estimate blast radius** — for each finding, note whether the fix is
  "safe" (the base edition's Step 10 definition) or architectural, so the
  next session can order its work without re-triaging.
- **Verify, don't speculate** — a read-only role must still reproduce
  bugs it reports (run the failing test, trace the code path). A backlog
  of hunches wastes the next agent's session.

## What this role does NOT do

- No code edits — not even one-character typo fixes. Backlog them.
- No doc edits — doc drift is a finding, not a fix (that's the docs
  agent's job).
- No dependency changes, no lockfile changes beyond what `install`
  legitimately produces (and those are never committed).
- No changelog entries, no version bumps.
