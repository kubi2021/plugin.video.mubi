# Hostile audit — severity, ESCALATE, anti-patterns, accepted risks

Read whenever rating a finding, hitting an ESCALATE condition, or deciding whether something is reportable.

## Severity

| Level | Definition |
|---|---|
| **S1** user-blocking | Crash on start, playback fails, sync leaves the library empty or deletes user data, login loop, data corruption, secret exposure. |
| **S2** user-frustrating | Intermittent failure, wrong metadata, silent partial sync, a misleading or missing error, a stale database served as fresh. |
| **S3** edge | Rare configuration, cosmetic, performance, low-volume path. |

Test: "Could a user make a wrong decision, lose data, or hit a broken feature?" YES → S1/S2. NO → S3. When torn between S1 and S2, ESCALATE.

## ESCALATE (stop, ask the user)

| Condition |
|---|
| A fix needs a product/business decision (which countries to sync, what counts as "available"). |
| A fix touches a CODEOWNERS-protected file (`backend/schemas/`, `tests/backend/test_schema_v1.py`). |
| A fix changes the published `films.json` schema or the `database` branch contract. |
| A finding contradicts a deliberate prior commit and you cannot tell if the change is intended. |
| Severity is ambiguous between S1 and S2. |
| A repro is BLOCKED and the finding would be S1 if true. |

## Anti-patterns

| Do NOT | Do |
|---|---|
| Report a bug you did not reproduce | Write a `tmp/` pytest that fails, or cite the command proving the static fact |
| Mark a finding CONFIRMED from reading | Run it; CONFIRMED needs a ledger row |
| Rate a test "fake" by inspection | Mutate the code, run the test, record killed/escaped (P6) |
| Aggregate items ("A1–A9 pass") | One bullet per applicable item with its own evidence |
| Promote an absence claim on a grep alone | grep + the convention path checked |
| Report lint noise, style, or naming | Only defects, security, and decorative tests |
| Report an accepted risk (below) | Skip it; it is a known, deliberate choice |
| Report a finding that a prior commit deliberately introduced | Read `git log -S`; engage with the history or drop it |
| Substitute one command's output for another | Each ledger row is that check's own command |
| Fix one instance of a pattern bug | grep `repo backend` for the same pattern, fix all in one commit |
| Edit a protected file to "just fix it" | ESCALATE; route schema work through `/schema-change` |
| Apply fixes because the report is done | Wait for `--fix` or `APPROVE FIXES` (P4) |
| Leave the tree mutated after Section J | Revert every mutation; verify `git status` clean before finishing |

## Accepted risks (do not report)

- `except Exception` at the three named boundaries: `_perform_sync`, `play_mubi_video`, the `addon.py` router.
- MD5 for download integrity — an availability check on this repo's own branch over HTTPS, not a security control.
- Integer add-on versioning.
- `models.py` importing `pydantic` while it stays test-only.
- The plugin-side TMDb/OMDb matcher being weaker than the backend's — a known legacy path (P5 of the principles doc).
- Generated zips tracked in `main` — already logged in the fix backlog; note once if in scope, do not re-litigate.
