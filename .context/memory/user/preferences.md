# User Preferences (update in place)

How the user likes things done **on this project**. Seeded from
Pre-Flight at bootstrap; grows as sessions reveal preferences —
corrections the user gives, patterns they approve, things they state
outright. This file exists so the user never has to give the same
correction twice.

## Learning rules

1. **Record preferences, not instructions.** A preference is standing:
   it would apply to future sessions ("plain-language changelog
   entries"). An instruction is one-off ("skip the tests this once") —
   it dies with the session and does not belong here.
2. **Every bullet carries provenance** — how and when it was learned:
   `(pre-flight)`, `(stated, YYYY-MM-DD)`, `(correction, YYYY-MM-DD)`,
   `(approved pattern, YYYY-MM-DD)`. An explicit statement or correction
   outranks an inferred pattern.
3. **Current-state file.** When the user changes their mind, update the
   bullet in place and refresh its provenance — don't keep the stale
   version. History lives in the session log, not here.
4. **A session instruction beats a recorded preference for that
   session.** Follow the instruction; afterwards, if it looked like a
   standing change of mind, update this file.
5. **Committed to git — keep it professional.** Working-style facts
   only. Never personal details, never opinions about people, never
   credentials.

<!-- TEMPLATE — keep these headings; add bullets under each as learned.
Format: - <preference> — <how to apply it> (provenance, YYYY-MM-DD)
## Workflow
- <e.g., push to main directly; one logical change per commit> (pre-flight)

## Communication
- <e.g., plain-language changelog, technical detail in reports> (stated, 2026-07-11)

## Code style
- <e.g., comment the why not the what; prefer DRY helpers> (correction, 2026-07-11)

## Review depth
- <e.g., fix safe issues, flag architectural ones for approval> (pre-flight)

## Risk & approvals
- <e.g., never bump a major version without flagging it; schema changes need explicit approval> (correction, 2026-07-11)
-->

## Workflow

- Push to main directly after each commit (pre-flight)
- One logical change per commit (pre-flight)

## Communication

## Code style

## Review depth

- Fix safe issues; flag architectural changes for approval (pre-flight)

## Risk & approvals
