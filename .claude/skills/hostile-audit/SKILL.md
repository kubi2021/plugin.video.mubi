---
name: hostile-audit
description: Adversarial audit of code, tests, or CI in this repo. Use when asked to audit, red-team, bug-hunt, stress-test, break, or "find what's wrong with" a file, module, diff, PR, or the whole repo. Produces ranked findings that were each verified by reproduction; fixes only on request.
argument-hint: "[path | module | diff | pr <n> | repo] [--fix]"
---

# Hostile audit

You are an adversary with read access. Your job is to make the code fail, then prove it.
A finding without evidence is a hypothesis. Hypotheses are not reported.

## 1. Scope

Resolve `$ARGUMENTS`:

| Argument | Scope |
|---|---|
| none or `diff` | `git diff main...HEAD` plus uncommitted changes |
| `pr <n>` | `gh pr diff <n>` |
| a path | that file or package, plus its direct callers |
| a module name | `repo/plugin_video_mubi/resources/lib/<name>.py` or `backend/<name>.py` |
| `repo` | everything; budget by the priority table below |

Read the full target, not excerpts. Then read its callers (`grep -rn "<symbol>" repo backend tests`) and its tests. Check `git log -S<symbol> --oneline` before calling something a bug: it may be deliberate.

Priority when scope is wide (highest first): `mubi.py`, `navigation_handler.py`, `library.py`, `film.py`, `data_source.py`, `backend/scraper.py`, `backend/enrich_metadata.py`, `playback.py`, `.github/workflows/*.yml`, everything else.

## 2. Attack checklist

Work through every group. Skip a group only if the target cannot touch it.

**Data and API**
- Chained `[...]` on API dicts; `[0]` on possibly empty lists; `int(x)` on nullable fields.
- Type drift the schema allows: `tmdb_id` is `int|str|null`; `directors` is list of str in JSON but list of dict from the API.
- Series objects leaking into film paths; `consumable` being `null`.
- Fields read from JSON that the scraper prunes, or pruned fields the plugin still reads.

**Time**
- ISO strings compared with `<` `>`; `Z` vs `+00:00`; naive vs aware `datetime`.
- `available_at` / `availability_ends_at` / `expires_at` semantics confused.
- Anything using `datetime.now()` without `timezone.utc`.

**Filesystem**
- Sanitisation bypass: `..`, trailing dot or space on Windows, reserved names in any case, 255-byte limit with multibyte titles, two films sanitising to one folder.
- Write-then-crash leaving half a film folder; obsolete-file removal deleting anything not created by the plugin.
- Threads writing into the same folder.

**Concurrency and process model**
- Kodi launches a new Python process per plugin call: class-level flags such as `_sync_in_progress` do not survive across calls. Ask what actually stops two syncs.
- Shared `xbmcaddon.Addon()` or `Dialog` objects used from worker threads.
- Cancellation paths: are futures cancelled, files cleaned, counters correct?

**Kodi environment**
- Syntax or stdlib newer than 3.8 under `repo/`. Imports not in stdlib, `addon.xml`, or `xbmc*`.
- `getSetting*` keys absent from `settings.xml`. Deprecated `xbmc.translatePath`. `print`.
- User-controlled strings reaching `xbmc.executebuiltin`, `RunPlugin(...)`, or `_is_safe_url` bypasses (scheme case, `javascript:`, userinfo `@`, IDN).
- URL params from `parse_qsl` used without defaults or type checks.

**Contract and data flow**
- Schema, `models.py`, and `docs/mubi_film_schema.md` disagree.
- `version` missing → defaults to 1 silently. `.md5` format assumptions. Redirect handling for GitHub raw URLs.
- Gzip size unbounded; JSON loaded fully into memory on low-end devices.

**Backend pipeline**
- Thresholds (`MIN_TOTAL_FILMS`, `MAX_MISSING_PERCENT`) that a partial outage slips under.
- Shallow sync keeping stale `available_countries` for countries not re-scraped.
- Greedy target selection on empty or degenerate input.
- Rating constants when history file is absent or malformed.
- Exit codes hidden by `continue-on-error: true` or `|| echo`.

**CI and release**
- `continue-on-error: true` on a step that then `exit 1`s: the failure is ignored and the job proceeds (check the VPN step in the sync workflows).
- `force: true` deploys to `database`; what guards against pushing an empty or truncated file?
- Secrets echoed, written to files, or interpolated into shell without quoting.
- `sed` on XML or JSON. Unpinned or archived actions.

**Security and secrets**
- Tokens or API keys in logs, URLs, `.strm` or `.nfo` files, DRM config strings, or exception messages.
- `local_server.py` bind address and what it serves.
- Anything from the network passed to `open()`, `subprocess`, or a shell.

**Tests (when auditing tests)**
- Tautologies: asserting a value that was just assigned or mocked.
- Mocking the unit under test, or asserting only that a mock was called.
- Mutation spot-check: comment out a branch in the implementation, run its tests; if they pass, the tests are decorative.
- `@pytest.mark.skip` without a platform guard; tests that pass only because `requests` is globally mocked.

## 3. Verify every candidate

For each candidate:

1. Write a throwaway pytest in `tmp/` (gitignored; name it `tmp/YYYYMMDD-HHMMSS-audit-<topic>.py`) that imports the real module (use `tests/plugin_video_mubi/kodi_stubs.py` and the existing conftest path setup) and drives the failure.
2. Run it with `python3 -m pytest tmp/<file> -q -p no:cacheprovider --rootdir=.` (use the repo venv if one exists). Leave the file in `tmp/` so the reproduction can be re-run.
3. Classify:
   - **CONFIRMED**: the test demonstrates wrong behaviour, or the defect is a static fact (missing setting key, py3.9 syntax, `continue-on-error` contradiction).
   - **PLAUSIBLE**: could not reproduce in-process (needs Kodi, network, or a race), but the reasoning holds after reading callers. State exactly what you could not check.
   - Anything else: drop it.

Do not report style, naming, or lint. Do not report accepted risks (section 6).

## 4. Report

Maximum 10 findings, ranked by severity then confidence. Severity:

- **S1** user-blocking: crash on start, playback fails, sync leaves library empty or deletes user data, login loop, data corruption, secret exposure.
- **S2** user-frustrating: intermittent failure, wrong metadata, silent partial sync, misleading error.
- **S3** edge: rare configuration, cosmetic, performance.

Format:

```
## Findings

| # | Sev | Verdict | Location | Summary |
|---|-----|---------|----------|---------|

### F1 · S1 · CONFIRMED · path/file.py:123
**Failure:** <input or state> → <wrong outcome>. One or two sentences.
**Evidence:** <test name and assertion that failed, or the static fact>
**Fix sketch:** <1–3 lines>
**Regression test:** test_<behaviour>_<scenario> in tests/<path>

## Checked and clean
- <area>: <what was tried, one line each>

## Not reported (accepted risks)
- <item>
```

"Checked and clean" is mandatory: it stops the next audit repeating your work.

## 5. `--fix`

Only after the report is written, and only if `--fix` was passed or the user asks:

- Fix CONFIRMED S1 and S2 findings, one commit each, regression test included, `fix:` prefix, body cites the finding.
- Do not touch CODEOWNERS-protected files (`backend/schemas/`, `tests/backend/test_schema_v1.py`) without saying so first.
- Run the full suite after each fix. Report actual output.

## 6. Accepted risks (do not report)

- `except Exception` at the three user boundaries named in `CLAUDE.md`.
- MD5 for download integrity (not a security control; the source is this repo's own branch over HTTPS).
- Integer add-on versioning.
- `models.py` importing `pydantic` while it stays test-only.
- Plugin-side TMDb/OMDb matcher being weaker than the backend's (known legacy path).
