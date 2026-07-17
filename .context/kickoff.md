# Project Kickoff — `.context/` Workflow Entry Point (Inbound)

<!-- GENERATED AT BOOTSTRAP — the universal kickoff's bootstrap step fills
this in. This file is project DATA: core updates never overwrite it. If
its template (.context/core/templates/kickoff.md) materially changes in a
core release, the next session regenerates it and refills the facts.

Generation rules for the bootstrapping agent:
1. Fill every fact <PLACEHOLDER> OUTSIDE this HTML comment — in "Project
   Facts", in the intro blockquote (the clone URL), AND in the Entry
   Steps code blocks — from the external kickoff's Pre-Flight + what you
   verified on disk (git remote, default branch). Facts you verified
   beat facts the user typed — record what's true. The ONLY placeholders
   that stay symbolic are the token forms
   (`<..._WITH_TOKEN_IF_PRIVATE>`, `${GIT_TOKEN}`) — never a real token.
   After filling, scan:
   `grep -n "<PROJECT\|<GIT_\|<LIVE_\|<REPO>" .context/kickoff.md` —
   hits are allowed only inside this comment and in the token forms.
2. Do NOT copy session parameters here — they live in
   memory/workflows/active.md (single source of truth). This file only
   points at them.
3. Do NOT put secrets, PATs, or tokens anywhere in this file. Ever.
4. Delete nothing else — the Entry Steps below are pre-written and
   correct for every post-bootstrap session. Fill their fact
   placeholders (rule 1) but change no step logic.
5. Keep facts current in later sessions: if a fact changes (repo renamed,
   new default branch, live URL added), update it in place and note the
   change in your session entry.
-->

> **This is the project's own kickoff file — the front door for every
> session.** The full protocol is vendored inside this repo at
> `.context/core/` — nothing needs to be cloned or fetched to run a
> session. To start one, point any agent here:
>
> - **Local agent** (already inside the repo): *"Read `.context/kickoff.md`
>   and follow it."* Add a target description in the same message if you
>   have one.
> - **Cloud/sandbox agent** (empty workspace): *"Clone
>   `https://github.com/TisoneK/flashscore-scraper.git`, read `.context/kickoff.md`, follow it."* If the
>   project repo is private — or the session will push (it will) — paste
>   a PAT for **this project repo** in that same chat message. That is
>   the only credential any session needs: the protocol is already in
>   the repo.

---

## Project Facts (generated — keep current)

- **Project name:** Flashscore Scraper
- **Project repository URL:** https://github.com/TisoneK/flashscore-scraper.git
- **Project repo privacy:** Public
- **Default branch:** main
- **Live application:** N/A
- **Git identity:** Tisone Kironget `tisonkironget@gmail.com`
- **Protocol:** vendored at `.context/core/` (version: see `.context/core/VERSION`)
- **Package upstream (core updates + flaw back-ports):** https://github.com/TisoneK/.context.git
- **Edition routing:** local agents → `.context/core/rules/ai-engineering-protocol-local.md`; cloud/sandbox agents → `.context/core/rules/ai-engineering-protocol.md`

## Session Parameters

Standing defaults live in
[`memory/workflows/active.md`](memory/workflows/active.md) — scope,
target, push policy, deliverable, commit style. **A target in the
user's chat message overrides the standing Target.** If the chat
message is just "start," use the standing Target.

**Agent identity:** never guess your model version. If your system
prompt states the exact model ID, record that; otherwise ask the user
once, or record `unknown`.

---

## Entry Steps (every session after bootstrap)

### Step 0 — Identify your agent type, get the project on disk

- **Local agent** — you are already inside the repo. Confirm:
  `git remote get-url origin` matches the Project repository URL.
  **Never re-clone the project. No PAT, ever** — your pushes use the
  user's own credentials; if one fails with an auth error, stop and
  tell the user.
- **Cloud/sandbox agent** — clone the project repo only:

  ```bash
  # If private: PAT from chat — strip it from .git/config right after.
  # A missing credential is a missing input: if the repo is private (or
  # you'll push, which you will) and no PAT arrived in chat, ask NOW.
  git clone <PROJECT_REPO_URL_WITH_TOKEN_IF_PRIVATE> flashscore-scraper && cd flashscore-scraper
  git remote set-url origin https://github.com/TisoneK/flashscore-scraper.git
  git config user.name "Tisone Kironget" && git config user.email "tisonkironget@gmail.com"
  ```

There is **no package repo to find, clone, or authenticate against** —
the protocol travels inside this repo at `.context/core/`.

### Step 1 — Sync the project, check the core

```bash
git pull --ff-only
```

If the pull fails (diverged) or the tree has changes you didn't make,
**stop and report** — don't stash or discard someone else's work.

Then check the vendored protocol (never fatal — a session must never
fail over sync):

```bash
sh .context/core/bin/context-sync verify    # integrity: core matches its MANIFEST
sh .context/core/bin/context-sync status    # drift: is a newer core available?
```

- `verify` fails → core was hand-edited or corrupted. Run
  `sh .context/core/bin/context-sync rollback`, log a flaw in
  `memory/flaws/log.md`, continue on the restored core.
- `status` reports a newer core with the **same MAJOR** → run
  `sh .context/core/bin/context-sync update` (it replaces `core/` only;
  memory is never touched), commit as
  `chore(context): update core to <version>`, and read the new
  `core/CHANGELOG.md` entries.
- A **MAJOR** bump, or no update source reachable → note it in your
  session entry and move on with the core you have.

### Step 2 — Read `.context/`

`README.md` (the zone map) → then, under `memory/`:
`workflows/active.md` → `agents/sessions.md` (last 3–5 entries) →
`tasks/current.md` → `tasks/backlog.md` → `inefficiencies/log.md` →
`flaws/log.md` → `plans/decisions.md` → `overrides/rules.md` →
`system/` → `user/` → note what's in `secrets/` (never print values).

If `memory/tasks/current.md` shows another live session in progress,
**do not start** — one agent per project repo at a time.

### Step 3 — Load the protocol

Pick the edition by **YOUR agent type** (identified in Step 0), from
the vendored core:

- **Local agent** → `.context/core/rules/ai-engineering-protocol-local.md`
- **Cloud/sandbox agent** → `.context/core/rules/ai-engineering-protocol.md`

`memory/workflows/active.md` gives you the standing parameters and any
role overlay — it does **not** choose your edition. If it names a
single edition, that's whichever agent type wrote it last; ignore that
and follow your own type (a local agent must never run the cloud
edition's PAT/clone steps, whatever the memory says). Also read any
role overlay from `.context/core/roles/`, and the project's overrides
in `memory/overrides/rules.md` (overrides beat the edition, except
secret-handling and append-only rules). Read your edition in full; it
is the instruction set for this session.

### Step 4 — Follow the protocol

All steps, all phases, in order. Don't skip Phase 1 because the task
seems small. Don't forget the Exit checklist: everything committed and
pushed, session logged, `memory/tasks/current.md` cleared, chat summary
delivered.

---

## If this file is stale or missing

The template lives inside this repo at
`.context/core/templates/kickoff.md`. Regenerate by copying that
template over this file and filling **Project Facts** from memory
(`memory/user/identity.md`, `memory/workflows/active.md`,
`git remote get-url origin`). Commit as
`chore(context): regenerate kickoff.md`.
