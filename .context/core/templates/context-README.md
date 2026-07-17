# .context/ — Agent Memory + Vendored Protocol

<!-- CORE-OWNED — refreshed from core/templates/context-README.md on
core updates. Project-specific notes belong in memory/ files, never here. -->

This directory makes any AI agent — any model, any machine, local or
cloud — a continuing member of this project instead of a stranger. It
is committed to git and travels with the repo. It has **two zones**:

```text
.context/
├── README.md     # this file — the zone map
├── kickoff.md    # THE FRONT DOOR — read this first, every session
├── core/         # the protocol, vendored — package-owned, READ-ONLY
│   ├── VERSION           # core semver in force here
│   ├── rules/            # the protocol editions (local + cloud)
│   ├── roles/            # mission overlays
│   ├── schemas/          # context-schema.md — the single source of truth on formats
│   ├── templates/        # what memory files are generated from
│   └── bin/context-sync  # status / verify / update / rollback
└── memory/       # this project's living memory — project-owned, writable
    ├── agents/sessions.md       # append-only session log
    ├── tasks/current.md         # the task in progress (also the session lock)
    ├── tasks/backlog.md         # append-only open items
    ├── plans/decisions.md       # append-only ADRs
    ├── flaws/log.md             # protocol friction — flows upstream to the package
    ├── inefficiencies/log.md    # project friction
    ├── reviews/                 # session reports
    ├── workflows/active.md      # standing session parameters
    ├── system/                  # machines + agent/model registry
    ├── user/                    # identity + preferences
    ├── overrides/rules.md       # project-local protocol adjustments
    ├── core.lock                # last-known-good core version (context-sync writes it)
    └── secrets/                 # LOCAL-ONLY — self-gitignored, never travels
```

## The three rules that matter most

1. **Never write under `core/`.** It is a versioned, checksummed copy
   of the protocol package — updated only as a whole tree by
   `core/bin/context-sync`. Protocol improvements go to the package
   repo via `memory/flaws/log.md`, not into this copy.
2. **`memory/` is this project's data.** Write it per each file's mode —
   append-only logs stay append-only, `chore(context):` commit prefix,
   no secret values in tracked files, ever. The full spec:
   `core/schemas/context-schema.md`.
3. **Sessions start at `kickoff.md`** (one level up from memory —
   `.context/kickoff.md`). It routes you by agent type to your edition
   in `core/rules/`. Memory never chooses your edition — your agent
   type does.
