# Secrets (LOCAL-ONLY — never tracked)

Secret values agents may use while working on this machine: GitHub PATs,
API keys, passwords. The `.gitignore` in this directory keeps everything
here out of git except itself and this README — values never appear in a
commit and never travel with the repo. Every other `.context/` file is
shared memory; this one is strictly per-machine.

## Hard rules

1. **Never commit a value.** The `.gitignore` here enforces it — never
   weaken it, never `git add -f` anything in this directory. Before
   writing a new secret file, prove it's ignored:
   `git check-ignore .context/memory/secrets/<file>` must succeed.
2. **Never echo a value** — not in chat output, not in logs, not in
   reports, not in commit messages, not in error output. Read it, use
   it, move on.
3. **Never copy a value into a tracked file** — not into other
   `.context/` files, not into code, not into `.env.example`. Refer to
   secrets by filename (`secrets/github-pat`), never by value.
4. **`chmod 600` every secret file** you create.
5. **This directory does not travel.** A fresh clone has an empty
   `secrets/`. If a secret you need is missing, ask the user (cloud
   sessions: check the first chat message) — don't hunt the filesystem
   for credentials.
6. **The user owns the credentials.** An agent writes a file here only
   when the user provides the value (in chat or by prior arrangement);
   agents never create, rotate, or revoke credentials on their own.

## Format — one secret per file

The filename is the slug: `github-pat`, `openai-api-key`,
`staging-db-password`. **Line 1 is the value, alone.** Lines 2+ are
notes: scope, date added, rotation policy.

<!-- TEMPLATE — a secret file looks like (no markdown, no extension):
<the-secret-value-alone-on-line-1>
scope: <what it unlocks — e.g. repo:owner/name (contents: rw)>
added: YYYY-MM-DD
rotate: <policy — e.g. "after each cloud session" | "long-lived">
-->

## Using a secret

Read line 1 into an env var; never inline a value into a command —
inlined values end up in shell history and process listings:

```bash
export GIT_TOKEN="$(head -n1 .context/memory/secrets/github-pat)"
```

## Trade-off to know

Values here are plaintext at rest, like a `.env` file — protected by
file permissions and the gitignore, not encryption. Prefer
narrow-scope, expiring credentials (fine-grained PATs scoped to one
repo beat classic full-account tokens).
