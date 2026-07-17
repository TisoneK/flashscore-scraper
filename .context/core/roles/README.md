# Role Overlays

> A role overlay is a small file that re-scopes a base protocol edition.
> Hand the agent **two files**: the base edition that matches its platform
> (`ai-engineering-protocol.md` for cloud/sandbox agents,
> `ai-engineering-protocol-local.md` for local/IDE agents) plus one role
> file from this directory. Where the role file and the base edition
> conflict, **the role file wins**. Everything the role file doesn't
> mention stays exactly as the base edition says.

## Why overlays, not more editions

The two base editions differ by **platform** — how the agent reaches the
repo (clone + PAT vs. already-on-disk). Roles differ by **mission** — what
the session is for. Keeping roles as overlays means the `.context/` spec,
git workflow, and quality gates live in exactly one place per platform;
a role file is ~80 lines, not another 790-line document to keep aligned.

## Available roles

| Role | File | Mission | Writes code? |
|---|---|---|---|
| **Engineer** (default) | *(none — run the base edition as-is)* | discovery + review + fix all safe issues | yes |
| **Feature engineer** | [`feature-engineer.md`](feature-engineer.md) | design + build a requested feature (Phase 2 = design/ADRs, Phase 3 = implement) | yes |
| **Reviewer** | [`reviewer.md`](reviewer.md) | audit and report; change nothing | no |
| **Security auditor** | [`security-auditor.md`](security-auditor.md) | security-only deep audit | security fixes only |
| **Docs agent** | [`docs-agent.md`](docs-agent.md) | make the docs match the code | docs only |

## What a role file may override

- **Session Parameters** — scope, focus areas, findings handling,
  deliverable, allowed commit types.
- **Review checklists** — narrow the base edition's checklists to the
  role's focus areas and extend them with role-specific checks.
- **Execution steps** — skip or no-op steps that don't apply (e.g., the
  reviewer role skips Phase 3 entirely). The role file must say so
  explicitly, step by step — silence means the step runs as written.
- **Report filename** — role reports are named
  `YYYY-MM-DD-<role>-review.md` (e.g., `2026-07-11-security-review.md`)
  so different lenses on the same day don't collide. The engineer default
  and the reviewer role use the plain `YYYY-MM-DD-review.md`.

## What a role file may NEVER override

- **The `.context/` rules** — append-only logs, no secrets, entry
  templates, `chore(context):` prefix.
- **Phase 5 (Steps 15–17)** — the memory update is mandatory for every
  role, every session, including sessions with no findings.
- **Quality gates** — gates that concern code changes are simply vacuous
  for roles that don't change code; the rest still apply.
- **The base edition's git/push workflow** — including "never force-push
  without `--force-with-lease`" and the PAT handling rules (cloud).

## Session entries record the role

Whatever the role, the session entry in `.context/memory/agents/sessions.md`
fills in its **Role** field — the next agent needs to know which lens
produced which findings (a reviewer's "no security issues found" after a
docs-only session would be a lie of omission).

## Adding a new role

Copy the structure of an existing role file:

1. Header blockquote — one-paragraph mission + the overlay binding rule.
2. **Session Parameter Overrides** — only the parameters that change.
3. **Execution changes vs the base edition** — every step skipped or
   altered, by step number. Unlisted steps run as written.
4. **Role checklist** — what this role hunts for.
5. **What this role does NOT do** — explicit boundaries.
6. Add a row to the table above and to the reviews naming note in
   `core/templates/memory/reviews/README.md` if the role has its own filename.
