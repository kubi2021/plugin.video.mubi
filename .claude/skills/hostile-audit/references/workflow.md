# Hostile audit — workflow (steps 1, 2, 4, 5) + Step 3 execution detail

Read at the matching step. Defines finding formats, the Verification Ledger, Coverage Disclosure, the mutation protocol, prevention categories, and apply rules.

## Finding formats

PASS: `✅ **A3 — API dict access** — PASS. get_film_metadata uses .get() throughout (mubi.py:894-920).`

FINDING:
```
🚩 **B1 — string timestamp compare** — FINDING (S2 · CONFIRMED)
- What: is_playable compares ISO strings lexically; a "+00:00" offset sorts wrong vs "Z".
- Evidence: film.py:57  `if now < available_at:`
- Repro: tmp/20260903-101500-audit-is-playable.py — asserted playable film reported not playable; FAILED as predicted.
- Fix: parse both with dateutil.parser.isoparse, compare aware datetimes.
- Regression test: test_is_playable_mixed_tz_offset in tests/plugin_video_mubi/test_film.py
- Prevention: CLAUDE.md rule (already states "never compare ISO strings") — was missed → add lessons-learned line + this regression test.
```

## Step 1 — Scope & inventory

1. Resolve `$ARGUMENTS`:

   | Argument | Scope |
   |---|---|
   | none / `diff` | `git diff main...HEAD` + uncommitted |
   | `pr <n>` | `gh pr diff <n>` (token from Keychain if gh is the wrong account) |
   | a path | that file/package + its direct callers |
   | a module | `repo/plugin_video_mubi/resources/lib/<m>.py` or `backend/<m>.py` |
   | `repo` | everything; budget by the priority order below |

2. Priority when scope is wide (audit in this order, stop when budget is spent): `mubi.py`, `navigation_handler.py`, `library.py`, `film.py`, `data_source.py`, `backend/scraper.py`, `backend/enrich_metadata.py`, `playback.py`, `.github/workflows/*.yml`, rest.
3. Build the inventory table: `| # | File | Role (plugin/backend/ci/test) | Sections |`. For a diff/PR, group each `.py` (plus co-changed test) as one object.
4. Select sections from the SKILL.md applicability table.
5. State the scope estimate: file count, checklist-item count, planned runs (repro tests, `pytest`, `flake8`/`ruff`, `git log -S`). Each planned run becomes a Verification Ledger row in Step 3 and may not silently vanish.
6. **Gate** (only for `repo` or >5 files): `⛔ Step 1: <N> files, <N> items, <N> planned runs. Reply APPROVE SCOPE or NARROW: <subset>.` A single file/module/diff/PR: print the one-line scope and go straight to Step 2.

## Step 2 — Gather context (zero analysis)

1. Read every inventory file in full — not excerpts. Include the co-located test file.
2. Callers: `grep -rn "<symbol>" repo backend tests`. Know who depends on the code before judging it.
3. History: `git log -S<symbol> --oneline -- <file>` and `git log --oneline -- <file>`. A behaviour that looks wrong may be a deliberate prior fix; a finding that contradicts one is invalid unless it engages with that history.
4. Absence claims (`no test`, `setting not declared`, `URL not centralised`): record the exact grep AND the convention path checked (e.g. `tests/**/test_<m>.py`, `settings.xml` `id="..."`, `constants.py`). Never promote an absence claim without both.
5. Environment probe once: is a venv with pytest available (`ls */bin/pytest` or the scratch venv), or must repros use `python3 -m pytest`? Record it; a BLOCKED repro must name what was missing.

## Step 3 — Audit

Run every applicable checklist item (`references/checklist.md`). One bullet per item: PASS + evidence, FINDING + severity + verdict + evidence, or `UNVERIFIED — <reason>`.

**Verify every candidate before it becomes a FINDING:**

1. Write a throwaway pytest in `tmp/` that imports the real module (reuse `tests/plugin_video_mubi/kodi_stubs.py` and the conftest path setup) and drives the failure.
2. Run `python3 -m pytest tmp/<file> -q -p no:cacheprovider --rootdir=.` (or the repo venv). Leave the file in `tmp/`.
3. Classify:
   - **CONFIRMED** — the test shows wrong behaviour, or the defect is a static fact (missing `settings.xml` key, py3.9 syntax under `repo/`, a `continue-on-error` that then `exit 1`s, a URL absent from `constants.py`). A static fact is proven by the command that shows it, not by assertion.
   - **PLAUSIBLE** — could not reproduce in-process (needs a running Kodi, live network, or a real race), but the reasoning holds after reading callers. State exactly what could not be checked.
   - Neither → drop it. Do not report style, lint noise, or accepted risks (see `references/severity-antipatterns.md`).

**Verification Ledger (mandatory).** Every item whose verification is "run something" gets a row: `| Item | Command (verbatim) | Result (summary / exit code) |`. An item with no row cannot be marked CONFIRMED — only PLAUSIBLE or BLOCKED. A PASS asserted from a different command's output is invalid.

**Mutation protocol (Section J, and any "this test is fake" claim).** Comment out or invert one branch in the implementation, run that module's existing tests (`pytest tests/**/test_<m>.py -q`), record killed (≥1 test failed) or escaped (all passed), then revert. Never commit a mutation; verify a clean tree (`git status`) before finishing the step. A test that survives a realistic single-point mutation is decorative; one that catches it is real even if it "looks tautological".

**Coverage Disclosure (mandatory, two buckets):**
- **CHECKED-CLEAN** — ran, no defect. One line each; this is what stops the next audit repeating your work.
- **BLOCKED** — could not run (needs Kodi / network / a secret). Name the blocker. A check runnable in this environment may not be disclosed away — run it.

## Step 4 — Report

Write to the `tmp/` report. Max 10 findings, ranked by severity then confidence.

Sections: `Scope | Findings (F1..) | Verification Ledger | Summary (S1/S2/S3/PASS/PLAUSIBLE counts) | Checked-clean | Blocked | Accepted risks not reported`.

Each finding uses the FINDING format above. End with a one-paragraph plain-language summary for the maintainer: the worst thing found and whether it ships to users. Do not apply anything.

## Step 5 — Apply fixes

Pre-flight: `--fix` was passed, or `APPROVE FIXES` arrived in a prior turn. Else stop and say so.

1. Fix CONFIRMED S1 then S2 findings. One commit each, `fix:` prefix, body citing the finding. PLAUSIBLE and S3 findings are reported, not auto-fixed, unless asked.
2. Each fix ships with its named regression test in the same commit. Confirm the test fails against the pre-fix code first.
3. Pattern-search: `grep -rn "<pattern>" repo backend` for the same defect elsewhere; fix all instances in the one commit.
4. Never touch a CODEOWNERS-protected file without flagging it first (P5).
5. Validate: `pytest tests/ -q` (and `--cov` if coverage is in scope). Paste the real pass/fail line. Fix regressions, re-run until clean.
6. Apply each prevention mechanism (regression test already in; a CLAUDE.md lessons-learned line; a schema tripwire; a `settings.xml` declaration; a CI gate; a healthcheck URL). Verify it: the regression test fails pre-fix and passes post-fix; a new lint/CI gate fails on the old code.

## Prevention categories

Every finding → exactly one.

| Category | Required output |
|---|---|
| Regression test | full pytest function + target file; the input that reproduces the bug |
| CLAUDE.md rule / lesson | exact line to add under Hard rules or Lessons learned, and why the existing rules missed it |
| Schema tripwire | `v1_schema.json` change + `test_schema_v1.py` case (via `/schema-change`; P5 applies) |
| Settings declaration | the `<setting>` block to add to `settings.xml`, or the dead read to delete |
| CI gate | the `test.yml` step or `healthcheck.yml` URL that would have caught it |
| Constants / dedup | the value to move into `constants.py`, or the duplicated function to unify |
| Already covered | cite the rule that exists and was ignored; say whether it needs clarifying or was simply missed |
