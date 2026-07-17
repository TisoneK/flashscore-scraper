# Protocol Overrides (update in place — project-owned)

Project-local adjustments to the protocol. Sessions read this file
right after loading their edition; where an override and the edition
conflict, **the override wins** — except the two rules nothing can
override: secret handling and append-only guarantees.

Overrides are standing, project-shaped deltas — not session
instructions (those die with the session) and not user preferences
(those live in `../user/preferences.md`). Core updates never touch
this file: customizations here survive every core version bump.

<!-- TEMPLATE — one bullet per override, with provenance:
- **<what the protocol says>** → **<what THIS project does instead>** —
  <why> (set by <user/agent>, YYYY-MM-DD)

Example:
- **Push to main after each commit** → **push to the `develop` branch;
  main is release-only** — repo uses git-flow (set by user, 2026-07-14)
-->

*(none yet)*
