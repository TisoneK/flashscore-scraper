# Role Overlay: Security Auditor

> Overlay on a base edition — see `roles/README.md` for how overlays bind.
> This role does a security-only deep audit: it goes further on security
> than the engineer default ever would, and touches nothing else. It may
> fix **safe security issues** (per the base Step 10 definition); every
> other finding — security or not — goes to the report and backlog.

## Session Parameter Overrides

- **Focus areas:** security only
- **Findings handling:** fix safe security issues; flag risky/architectural
  security changes. Non-security findings noticed in passing are backlogged,
  never fixed.
- **Deliverable:** `.context/memory/reviews/YYYY-MM-DD-security-review.md` + chat summary
- **Allowed commits:** `fix(security):`, `test(security):` (regression tests
  for fixed issues), `docs(review):` (the report), `chore(context):`.

## Execution changes vs the base edition

- **Steps 1–8 run as written.** Baseline health still matters — you can't
  claim a security fix is safe if you don't know whether tests passed
  before you arrived.
- **Step 9 narrows to the Security Review section**, extended by the role
  checklist below. Skip the UX, performance, and docs passes.
- **Step 14 (changelog):** security fixes get a changelog entry in plain
  language — **never the vulnerability mechanics** (base edition rule).
  Mechanics go in the report only.
- **All other steps run as written.**

## Role checklist (extends the base Security Review section)

Work through the base edition's Security Review list first, then:

- **Entry-point inventory** — enumerate every way data enters: routes,
  webhooks, file uploads, CLI args, env vars, IPC, message queues. The
  report lists them; unaudited entry points are findings, not omissions.
- **Trust-boundary pass** — for each boundary (user→server, server→DB,
  server→third-party), what validates, what sanitizes, what authenticates?
- **AuthZ matrix** — every mutating route × who may call it × what check
  enforces that. A route with no row is a finding.
- **Secrets sweep** — scan the working tree AND git history
  (`git log --diff-filter=A --name-only`, targeted `git log -S` probes) for
  committed credentials. A rotated-but-still-in-history secret is a finding.
- **Dependency audit** — run the ecosystem's audit tool; verify hits
  against actually-installed versions before reporting (base pitfall rule).
- **SSRF / redirect discipline** — anywhere the code fetches a URL: is the
  target re-validated after redirects? Private-IP and metadata-endpoint
  filtering present? (Base pitfall 16.)
- **Error-message leakage** — do error responses expose stack traces,
  paths, query text, or internal hostnames?
- **Every fix ships with a regression test** where the project has a test
  suite — a security fix without a test is half a fix.

## Report additions

For each finding, in addition to the base report fields: an **exploit
scenario** (concrete attacker steps) and **exposure** (who can reach it —
unauthenticated internet, authenticated user, local only). Findings the
role fixed still appear in full — the report is the audit record.

## What this role does NOT do

- No non-security changes — a typo next to the vulnerability stays put
  (backlog it).
- No hardening rewrites that change behavior — flag as architectural.
- No vulnerability mechanics in the public changelog, ever.
- No secret **values** in the report or anywhere in `.context/` — describe
  location and rotation need, never the secret itself.
