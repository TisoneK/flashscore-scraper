# Core Changelog

One entry per released core version, newest first. An agent syncing a
project's `.context/core/` from an older version reads every entry
between the two versions — migration notes live here.

Semver: breaking changes to the `.context/` spec or the memory layout
bump MAJOR; new features (roles, pitfalls, templates, schema fields)
bump MINOR; wording and fixes bump PATCH.

---

## 0.2.0 — 2026-07-14

**The vendored-core release.** The protocol no longer lives in a sibling
clone — it travels inside every project as `.context/core/`, beside the
project's own memory in `.context/memory/`.

- **Two-zone layout:** `.context/core/` (package-owned, read-only,
  version-stamped) + `.context/memory/` (project-owned, writable, never
  synced). Replaces the basename-based structural/data split; `SYNC.md`
  is retired.
- **Memory modules move under `memory/`:** `agents/`, `tasks/`, `plans/`,
  `flaws/`, `inefficiencies/`, `reviews/`, `system/`, `user/`,
  `workflows/`, `secrets/` keep their names and formats — only the path
  prefix changes. `kickoff.md` and `README.md` stay at the `.context/`
  root as the front door and zone map.
- **New memory modules:** `memory/overrides/rules.md` (project-local
  protocol adjustments, read after the edition) and `memory/core.lock`
  (last-known-good core version, written by `context-sync`).
- **Unified schema:** `core/schemas/context-schema.md` (+
  `context.schema.json`) is now the single authority on every memory
  file's format, write mode, ownership, and fact scope — including the
  per-agent-type vs per-project vs per-machine scoping rules that stop
  cross-agent-type contamination.
- **`core/bin/context-sync`:** POSIX-sh tool — `status`, `verify`,
  `update`, `rollback`, `bootstrap`. Startup change detection, checksum
  integrity via `core/MANIFEST.sha256`, git-based rollback to the
  locked version.
- **Weak-agent translation layer:** bootstrap generates a root
  `AGENTS.md` digest (from `core/templates/AGENTS.md`) so agents that
  never read a 900-line edition still learn the zones, the entry point,
  and the binding rules.
- **Cloud sessions need no package access after bootstrap** — the
  protocol is on disk inside the project. Package PATs are a
  bootstrap-only concern.
- **Migration from 0.1.x:** see `MIGRATION.md` in the package repo.
  Summary: create `memory/`, `git mv` the modules into it, vendor
  `core/`, regenerate `kickoff.md`, delete `SYNC.md`.

## 0.1.0 — 2026-07-13 (retroactive)

The sibling-clone era: two protocol editions at the package root,
`context-skeleton/` bootstrapped into projects as a flat `.context/`,
structural-vs-data sync per `SYNC.md`, package cloned beside every
project as `../context`. Never formally released; version assigned
retroactively as the baseline `MIGRATION.md` migrates from.
