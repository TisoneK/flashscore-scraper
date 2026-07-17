# The `.context/` Schema — Single Source of Truth

This file defines every file in a project's `.context/` directory: where
it lives, who owns it, how it may be written, and which *scope* its facts
belong to. When any other document (a README, an edition, a template
comment) disagrees with this schema, **this schema wins** — and the
disagreement is a flaw to log.

A machine-readable mirror lives beside this file as
`context.schema.json`. The markdown is authoritative; the JSON is
generated from it by hand and must be updated in the same commit as any
schema change.

---

## The two zones

```text
{project}/
├── AGENTS.md              # generated digest for agent discovery (see Translation layer)
└── .context/
    ├── README.md          # zone map — copied from core/templates at bootstrap/update
    ├── kickoff.md         # front door — generated at bootstrap, project-owned
    ├── core/              # ZONE 1 — package-owned, READ-ONLY, version-stamped
    └── memory/            # ZONE 2 — project-owned, writable, never synced
```

| Zone | Owner | Agents may write? | How it changes |
|---|---|---|---|
| `core/` | The protocol package | **Never.** Not one byte. | Only via `context-sync update` (whole-tree, version-stamped) |
| `memory/` | The project | Yes — per each file's write mode below | Normal session work, committed with the project |

The zone rule is the entire sync model: **core is replaced as a unit,
memory is never touched by sync.** There is no per-file structural/data
classification anymore (the old `SYNC.md` basename rule is retired). If
you are editing a path that starts with `.context/core/`, stop — you are
either syncing (use `context-sync`) or making a protocol change, which
belongs in the package repo, not in a project.

Two root files sit outside both zones:

- **`.context/README.md`** — the zone map. Package-owned *content*
  (refreshed from `core/templates/context-README.md` on core updates)
  but deliberately kept at the root so a fresh agent's first `ls` +
  `cat` explains the layout.
- **`.context/kickoff.md`** — the front door. Project-owned **data**:
  generated once at bootstrap from `core/templates/kickoff.md`, its
  facts kept current by sessions. Core updates never overwrite it; if
  its template changes materially (see `core/CHANGELOG.md`), the next
  session **regenerates** it from the new template and refills the
  facts from memory.

---

## Zone 1 — `core/` (read-only reference)

```text
core/
├── VERSION              # semver of this core tree, e.g. 0.2.0
├── CHANGELOG.md         # one entry per release + migration notes
├── MANIFEST.sha256      # checksums of every core file — integrity check
├── bin/
│   └── context-sync     # status / verify / update / rollback / bootstrap
├── rules/
│   ├── ai-engineering-protocol-local.md   # LOCAL agents' edition
│   └── ai-engineering-protocol.md         # CLOUD/SANDBOX agents' edition
├── roles/               # mission overlays: reviewer, security-auditor, docs-agent, feature-engineer
├── schemas/
│   ├── context-schema.md    # this file
│   └── context.schema.json  # machine-readable mirror
└── templates/
    ├── AGENTS.md            # root discovery digest (translation layer)
    ├── context-README.md    # becomes .context/README.md
    ├── kickoff.md           # becomes .context/kickoff.md (filled at bootstrap)
    └── memory/              # the memory/ stub tree copied at bootstrap
```

Integrity: `sh .context/core/bin/context-sync verify` checks every core
file against `MANIFEST.sha256`. A failed verify means core was
hand-edited or corrupted — restore it (`context-sync rollback` or
`git checkout` of the last good commit) and log a flaw. Never "fix"
core in place inside a project.

---

## Zone 2 — `memory/` (the project's living memory)

File inventory, write modes, and scopes. **Write modes:**

- **append-only** — entries are only added at the bottom; corrections
  are appended, never edited in. Sole exception: byte-identical
  duplicate entries may be removed, leaving a one-line note in place.
- **overwrite** — current-state only; replace the content, history
  lives in the append-only logs.
- **update-in-place** — structured records updated where they stand
  (a row, a block, a bullet); never wholesale replaced.
- **generated** — created from a `core/templates/` file at bootstrap,
  then maintained as data (facts updated in place; regenerated only
  when the template materially changes).
- **local-only** — never tracked by git, never travels.

| Path (under `.context/memory/`) | Mode | Scope | Holds |
|---|---|---|---|
| `agents/sessions.md` | append-only | project | One entry per session: agent, model, platform, task, commits, outcome |
| `tasks/current.md` | overwrite | project | The one task in progress — doubles as the concurrency lock |
| `tasks/backlog.md` | append-only | project | Open items for future sessions |
| `plans/decisions.md` | append-only | project | ADR-style decisions — respected, not relitigated |
| `flaws/log.md` | append-only | project→package | Friction with the protocol/`.context/` system itself; flows upstream |
| `flaws/README.md` | generated | project | The flaws-vs-inefficiencies split rule (pointer to this schema) |
| `inefficiencies/log.md` | append-only | project | Friction with the project's code, env, deps |
| `reviews/YYYY-MM-DD-*.md` | new file per session | project | Session reports (deliverables — commit as `docs(review):`) |
| `reviews/README.md` | generated | project | Naming + report structure (pointer to this schema) |
| `workflows/active.md` | overwrite | project (see scoping!) | Standing session parameters + core version in force |
| `system/environments.md` | update-in-place | **machine** | One block per machine/sandbox, keyed by an "Identify by" line |
| `system/ai-models.md` | update-in-place | **agent** | Registry + evidence-based observations per agent/model |
| `user/identity.md` | update-in-place | user | Who the user is |
| `user/preferences.md` | update-in-place | user | Standing preferences, each bullet with provenance |
| `overrides/rules.md` | update-in-place | project | Project-local protocol adjustments (see Overrides) |
| `core.lock` | overwrite (by `context-sync`) | project | Last-known-good core version + when it was verified |
| `secrets/<slug>` | local-only | machine | One secret per file; line 1 = value. Self-gitignored |
| `secrets/README.md`, `secrets/.gitignore` | generated | project | The secrets hard rules; the self-ignore |

Entry formats: every writable file carries its entry template in an HTML
comment at the top (seeded from `core/templates/memory/`). **Read the
template before writing; never invent formats.** If a file's in-repo
template comment and this schema's mode column disagree, this schema
wins.

### Reading order (session start)

`.context/README.md` → `kickoff.md` → `memory/workflows/active.md` →
`memory/agents/sessions.md` (last 3–5) → `memory/tasks/current.md` →
`memory/tasks/backlog.md` → `memory/inefficiencies/log.md` →
`memory/flaws/log.md` → `memory/plans/decisions.md` →
`memory/overrides/rules.md` → `memory/system/` → `memory/user/` →
note what's in `memory/secrets/` (never print values).

---

## Fact scoping — the contamination rules

`.context/` memory serves **every** agent that will ever work on the
project: local and cloud, strong and weak, on any machine. The single
biggest failure mode observed in the field is *scope contamination*:
one agent records a fact that is true only for its own type, machine,
or model — and the next agent of a different kind reads it as binding.
(A local agent on a cloud-bootstrapped repo starts doing PAT dances and
re-cloning; a cloud agent trusts a macOS-only command.)

Every fact you write into memory belongs to exactly one scope. Record
it so the scope is explicit:

| Scope | Definition | Where it lives | How it's keyed |
|---|---|---|---|
| **project** | True for this repo regardless of who works on it (repo URL, default branch, decisions, backlog) | most of `memory/` | nothing — unqualified facts are project facts |
| **agent-type** | True only for local OR only for cloud/sandbox agents (edition, credential flow, clone steps) | **never as a single value** — always recorded keyed "by agent type", naming both branches | explicit `local: … / cloud: …` |
| **machine** | True only on one machine/sandbox (paths, installed tools, verified commands) | `memory/system/environments.md` blocks | the block's "Identify by" line — apply a block only if it matches where you are |
| **agent/model** | True only for one agent or model (capabilities, blind spots) | `memory/system/ai-models.md` | the registry row |
| **user** | About the person (identity, preferences) | `memory/user/` | provenance markers |

Binding consequences:

1. **Edition choice is a function of your agent type at session start —
   never of memory.** `workflows/active.md` records the protocol "by
   agent type", naming BOTH editions. If you ever find a single edition
   recorded there, that's the *previous* agent's type leaking; follow
   your own type and fix the record.
2. **A machine-scoped block applies only where its "Identify by"
   matches.** Never run another environment's verified commands as if
   they were yours; add or update your own block.
3. **Credential flows are agent-type facts.** PAT steps exist only in
   the cloud edition; a local agent that finds PAT instructions in
   memory ignores them and logs a flaw.
4. **When writing, ask: "would this sentence be wrong for an agent of
   the other type, on another machine?"** If yes, key it to its scope
   or don't write it.

---

## Overrides — project-local protocol adjustments

`memory/overrides/rules.md` is the one sanctioned place a project bends
the protocol without forking core. Sessions read it right after loading
their edition; where an override and the edition conflict, **the
override wins** — with two exceptions that nothing can override:
secret-handling rules and the append-only guarantee.

Overrides are for standing, project-shaped deltas ("this repo squashes
to a release branch, not main", "reports go in docs/reports/ for
legacy reasons"). They are *not* a scratchpad for session instructions
(those die with the session) or user preferences (those go in
`user/preferences.md`). Each override carries provenance and a date,
like a preference. Core updates never touch this file — that's the
point: customizations survive every core version bump.

---

## Translation layer — how weaker agents consume this system

Not every agent reads a 900-line edition reliably. The system degrades
gracefully through three tiers, all generated from core — never
hand-maintained per project:

1. **`AGENTS.md` at the project root** (from `core/templates/AGENTS.md`,
   generated at bootstrap; optionally copied as `CLAUDE.md` and
   `.github/copilot-instructions.md` for tools that auto-load those
   paths). ~60 lines: the zones, the read-only rule for core, the entry
   point (`.context/kickoff.md`), and the condensed binding rules. This
   is the floor — an agent that reads nothing else still learns where
   memory lives, what it must never write to, and where to start.
2. **`.context/kickoff.md`** — the front door: typed entry steps that
   route by agent type and point into core.
3. **The full edition in `core/rules/`** — the complete instruction set
   for agents that can hold it.

Each tier links down to the next; no tier contradicts another because
all three are rendered from the same core version. A weak agent
following only tier 1 does less, but nothing *wrong* — it cannot
clobber core (rule stated in tier 1), cannot miss the entry point, and
cannot pick the wrong edition (the kickoff routes by type).

---

## Sync, change detection, and fallback

- **Startup check:** the kickoff's entry steps run
  `sh .context/core/bin/context-sync status` — compares the vendored
  core's `VERSION` against the best reachable source (an explicit path,
  a sibling package clone, or the package remote). Unreachable source =
  skip and note; **never fail a session over sync.**
- **Safe auto-update:** same-MAJOR updates (`0.2.x → 0.2.y`, minor
  bumps included) may be applied without asking; a MAJOR bump requires
  the user (there may be migration steps in `CHANGELOG.md`). Updating
  core never touches `memory/` — that is what makes auto-update safe.
- **core.lock:** after any successful `verify`, `context-sync` records
  the version + date in `memory/core.lock`. That is the
  **last-known-good** marker.
- **Fallback:** if a session cannot parse or trust the current core
  (failed verify, half-applied update), roll back to the locked
  version — `context-sync rollback` restores `core/` from the project's
  own git history — then log the incident in `memory/flaws/log.md` and
  continue on the restored version. The session proceeds; the flaw
  flows upstream.
