# Reviews (one file per session)

Session review reports. One file per session, named `YYYY-MM-DD-review.md`
so they sort chronologically. Role-overlay sessions (see
`.context/core/roles/`) use `YYYY-MM-DD-<role>-review.md`, e.g.
`2026-07-11-security-review.md` — except the reviewer role, which keeps
the plain name (its report *is* the review). If two same-named sessions
land on the same day, suffix the later one: `YYYY-MM-DD-review-2.md`.
Never edit a past report — a correction goes in the next report (or an
appended "Correction" section citing the session that found the error).

Report structure:
1. Executive Summary
2. Discovery Phase
3. Baseline Health
4. Findings (by severity: Critical / High / Medium / Low / Nice to Have)
5. Fixes Applied
6. Open Items
7. Recommended Next Steps

Even a session with no findings writes a report ("baseline healthy, no
findings") — the next agent needs to know the review happened.

Reports migrated from the legacy `docs/report/` location keep their
original filenames.
