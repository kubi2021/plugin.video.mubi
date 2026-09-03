# Development Principles for plugin.video.mubi

**Last updated:** 2026-09-03

This document distils how this repository actually works today and sets out the principles that should guide future changes. It is written for a single maintainer working in spare time with heavy AI‑assistant support, so the principles favour low ceremony, high automation, and protection against the two things that have historically broken the project: upstream MUBI API changes and silent regressions in the sync pipeline.

---

## 1. What the repository is

The project is really **three products in one repo** that share a data contract:

| Product | Location | Runs where | Ships how |
|---|---|---|---|
| Kodi add‑on (the "plugin") | `repo/plugin_video_mubi/` | Inside Kodi, Python 3 embedded, no pip | Zipped by `_repo_generator.py`, released via `auto-release.yml` |
| Shadow backend (scraper + enrichment + ratings) | `backend/` | GitHub Actions, Python 3.11 | Pushes `films.json.gz` to the orphan `database` branch |
| Weekly digest email | `backend/generate_weekly_digest.py` + `backend/emails/` (React Email) | GitHub Actions, Python + Node 18 | Sent via Resend |

The **JSON schema in `backend/schemas/v1_schema.json`** is the contract between the backend and the plugin. It is the single most important artefact in the repo and is already protected by CODEOWNERS.

### Health snapshot (measured 2026‑09‑03)

| Metric | Value |
|---|---|
| Tests | 709 passed, 17 skipped, 0 failed |
| Coverage (plugin + backend) | 83.5 % (CI gate is 65 %) |
| Plugin source | ~6,900 lines in 23 modules |
| Backend source | ~3,600 lines |
| Test source | ~21,600 lines (3× the code) |
| flake8 findings | 1,129 total, of which 77 are `F`‑class (unused imports, unused variables, shadowed names) |
| Lowest‑covered plugin module | `library.py` at 64 % |
| Untested backend modules | `validate_schema.py`, `generate_repo.py` (0 %) |

The suite is healthy and fast (under 30 s). The main weaknesses are structural, not functional: a few very large modules and functions, duplicated logic between the plugin and backend, dead code, and documentation drift.

---

## 2. Principles

### P1. The JSON schema is the contract. Change it deliberately, in one PR, in four places.

The repo already treats the schema as protected. Keep that, and make the procedure mechanical:

1. `backend/schemas/v1_schema.json` (the source of truth)
2. `tests/backend/test_schema_v1.py` (present / null / absent / unknown‑rejected cases, as the last three commits did)
3. `repo/plugin_video_mubi/resources/lib/models.py` (Pydantic mirror, used only in tests today)
4. `docs/mubi_film_schema.md`

Bump `version_label` in `backend/scraper.py` on every schema change. Keep `additionalProperties: false` on nested objects: it is the tripwire that caught the last three upstream changes (`original_audio_language`, `early_access_film_date_message`). Prune new upstream fields on fresh scrapes unless the plugin needs them, so the JSON stays small.

**Why:** Every recent commit on this branch was a schema tripwire firing because MUBI added a field. That is the system working as designed. The cost is a broken nightly sync until someone reacts, so the fix path must be fast and boring.

### P2. Treat the MUBI API as hostile and undocumented.

- All requests go through `Mubi._make_api_call` in the plugin and `MubiScraper._create_session` in the backend. Never add a raw `requests.get` elsewhere.
- Every external URL lives in `resources/lib/constants.py`, and URLs that should answer a bare GET are listed in `HEALTHCHECK_URLS` so the daily `healthcheck.yml` catches a retired page before a user does.
- Every new field read from an API response uses `.get()` with a default, or is validated by the schema first. Never index a nested dict directly.
- Keep `docs/MUBI_API_V4_Documentation.md` and `docs/MUBI_API_Film_Response_Fields.md` current when a new endpoint or field is used. They are the only documentation of the API that exists anywhere.
- When MUBI breaks something, add a regression test that pins the new behaviour before fixing it (the login‑URL commit did this well).

### P3. The plugin runs inside Kodi. Respect that environment's constraints.

- **Dependencies:** the plugin may import only the Python standard library plus modules declared in `addon.xml` (`requests`, `dateutil`, `inputstreamhelper`). `models.py` imports `pydantic`, which Kodi does not ship. It is currently only imported by tests, so it is harmless, but it must never be imported from runtime code. If runtime validation is wanted, either vendor a minimal validator or declare a Kodi module dependency.
- **Python floor:** Kodi 19 (Matrix) ships Python 3.8. CI tests 3.8 through 3.11. Do not use syntax or stdlib features newer than 3.8 in `repo/`. The backend may use anything 3.11 supports.
- **Kodi API:** use `xbmcvfs` for all path and file work, never `xbmc.translatePath`. Use `xbmc.log` with an explicit level. Never `print()`.
- **User‑visible strings** belong in `strings.po` and are read with `getLocalizedString`. Today 18 dialogs in `navigation_handler.py` hard‑code English text and no module calls `getLocalizedString`. New dialogs should use string IDs; migrate existing ones opportunistically.
- **Settings:** every `getSetting*` key in code must exist in `settings.xml`. `omdbapiKey` is read by the metadata factory but is not declared in `settings.xml`, so the OMDb fallback path is dead for new installs. Either declare it or remove the code path.

### P4. One responsibility per module, and keep functions under a screen.

The three largest modules carry most of the risk:

| Module | Lines | Longest function |
|---|---|---|
| `mubi.py` | 1,356 | `get_film_metadata` (130 lines) |
| `navigation_handler.py` | 1,235 | `_perform_sync` (164 lines) |
| `film.py` | 879 | `_get_nfo_tree` (248 lines) |

Do not add to these. When touching them, extract. Natural seams that already exist in the code:

- `mubi.py`: split into `api_client.py` (transport, headers, token refresh, logging sanitisation), `film_mapper.py` (`get_film_metadata`, artwork and trailer selection), and `geo.py` (`get_cli_country`, VPN hints).
- `navigation_handler.py`: move `_perform_sync`, `wait_for_library_idle`, `update_kodi_library`, `clean_kodi_library` into a `sync_service.py`. Move `play_mubi_video`, `_is_country_available`, `_get_vpn_suggestions` into `playback_controller.py`. The handler should only route URLs to services.
- `film.py`: move NFO XML construction into `nfo_writer.py` and filename sanitisation into `sanitize.py`. The `Film` class should be a value object.

Rule of thumb: a function that needs a `# 1. ... # 2. ... # 3.` comment structure is three functions.

### P5. Share logic between plugin and backend, or make the split explicit.

The following pairs are near‑duplicates:

| Plugin | Backend |
|---|---|
| `external_metadata/title_utils.py` (`TitleNormalizer`, `RetryStrategy`) | `metadata_utils.py` (same classes, same methods) |
| `external_metadata/tmdb_provider.py` | `tmdb_provider.py` (a much more advanced three‑phase matcher) |
| `external_metadata/omdb_provider.py` | `omdb_provider.py` |

The backend's matcher is the good one (it implements the algorithm in `docs/MUBI to TMDB Movie Matching Algorithm.md`). The plugin's is a legacy path for users not on Fast Sync.

Decide explicitly, and document the decision in this file:

- **Preferred:** make Fast Sync the default and the API‑crawl path a fallback. Then the plugin's `external_metadata` package becomes thin (read `imdb_id`/`tmdb_id` from the JSON) and the backend owns matching.
- **Alternative:** if both paths must live on, put shared pure‑Python code (title normalisation, retry) in one place and copy it into the plugin at build time via `_repo_generator.py`, so there is one source of truth.

Do not fix a matching bug in one copy without fixing it in the other.

### P6. Compare times as datetimes, never as strings.

`Film.is_playable` compares ISO timestamp strings lexically. This works only while every timestamp from every source is in exactly the same format and timezone (`...Z`). One `+00:00` from a different serialiser and the comparison silently becomes wrong. Parse with `dateutil.parser.isoparse` and compare aware datetimes, as `mubi.get_film_metadata` already does. Apply the same rule to `availability_ends_at` filtering in `data_source.py`.

### P7. Tests are the specification. Keep them fast, isolated, and honest.

The test culture here is strong. Preserve it with these rules:

- **Location:** all tests live under `tests/`, mirroring the source tree. `backend/tests/test_weekly_digest.py` should move to `tests/backend/`. One `conftest.py` per test package; the root `conftest.py` and `tests/conftest.py` currently contain an identical `pytest_ignore_collect`, so keep only the root copy.
- **Kodi stubs:** use `tests/plugin_video_mubi/kodi_stubs.py` (typed stubs with realistic defaults) rather than bare `MagicMock()` for `xbmc*` modules. Five test files still patch `sys.modules['xbmc']` by hand; migrate them when touched.
- **Skips:** 17 tests are skipped with the reason "os.startfile not available on macOS". That reason describes a Windows‑only call, so either the tests are mis‑labelled or the code path is untestable off‑Windows. Each skip should either be fixed, guarded with `sys.platform`, or deleted. A permanent skip is a deleted test with extra steps.
- **Markers:** `pytest.ini` declares `unit`, `integration`, `e2e`, `slow`, `network`. Only `integration` is used. Mark `tests/integration/test_live_data.py` as `network` and exclude it from the default run so the suite never depends on GitHub being reachable.
- **Coverage floor:** raise `--cov-fail-under` from 65 to 80. The suite is at 83.5 %, so this costs nothing today and stops backsliding. Add `.coveragerc`'s `source` to include `backend` so local runs match CI.
- **Golden files:** `tests/fixtures/golden_film_sample.json` is the right pattern. Refresh it whenever the schema changes, and keep it small.
- **What to test:** behaviour, not assignment. A test that asserts `obj.x == value` after `obj.x = value` is a tautology. Use `/test-audit` before merging large test additions.

### P8. Automate every release step, and make the automation idempotent.

In v27 the release workflow's `sed` produced nested `<news>` tags in `addon.xml` (an `&#39;` in the notes matched a previous `<news>` block). v28 shipped clean, but the same `sed` is still in place, so it will happen again on the next apostrophe.

- Replace the `sed` pipeline in `auto-release.yml` with a small Python script (`scripts/bump_version.py`) that parses `addon.xml` with `xml.etree`, sets `version` and `news`, and writes it back. Test that script.
- Stop committing generated zips to `main`. `repo/zips/` holds 32 tracked zips totalling 52 MB and grows with every release. Publish zips as release assets and serve the repository index from GitHub Pages built by the release workflow, or move them to the `gh-pages` branch. Keep only `addons.xml` and its md5 in `main` if the Kodi repository add‑on needs them.
- Pin GitHub Actions to major versions consistently (`setup-python@v5` everywhere; `test.yml` still uses `v4`). Replace the archived `actions/create-release@v1` and `upload-release-asset@v1` with `softprops/action-gh-release` or `gh release create`.
- The three sync workflows share ~80 identical lines of VPN setup. Extract a composite action under `.github/actions/connect-vpn/` so a fix lands once.

### P9. Documentation lives next to the thing it documents, and dead docs are deleted.

Drift found today:

- `README.md` links to `docs/RELEASE_MANAGEMENT.md` (does not exist) and to `python -m tools.analyze_coverage` (the `tools/` package does not exist).
- `README.md` says the plugin syncs from "~23 countries"; `data_source.py` hard‑codes six in `SYNC_COUNTRIES`.
- `tests/plugin_video_mubi/README.md` gives `pytest tests/ --cov=resources`, which is a path from before the repo restructure.
- `docs/email_generation.md` says the digest JSON step is "pending integration"; the workflow already runs it.

Rules going forward:

- The README is for **users**. Move the "Contributing", "Shadow Backend", and "Release Process" sections into `docs/CONTRIBUTING.md` and link to it.
- Every doc has a "Last updated" line (several already do). A doc not touched in a year is reviewed or deleted.
- A PR that changes behaviour a doc describes updates the doc in the same PR. Reviewers check this.
- Keep `CLAUDE.md` short and current: it is what every AI session reads first. Its "Lessons learned" section is the right place for one‑line post‑mortems.

### P10. Lint and format automatically, so reviews are about logic.

flake8 reports 1,129 issues, the vast majority whitespace. Nobody should fix these by hand.

- Adopt `ruff` (replaces flake8, isort, and most of black's role) with a `pyproject.toml` at the root. Start with `select = ["E", "F", "W", "I"]`, `line-length = 120`, and `target-version = "py38"` for `repo/`.
- Run `ruff format` once as a single "no functional change" commit, then add `ruff check` to `test.yml` so it gates PRs.
- Fix the 77 `F`‑class findings first: 40 unused imports, 22 f‑strings without placeholders, 10 unused variables, 5 redefinitions. These are real code smells and take an hour.
- Fix the `W605` invalid escape in `film.py:94` (a docstring containing `\ `): Python 3.12+ warns on it today and will error in the future.

### P11. Fail loudly in the backend, degrade gracefully in the plugin.

The two halves have opposite failure philosophies, and that is correct:

- **Backend** runs unattended. Any anomaly (fewer than `MIN_TOTAL_FILMS`, a critical country returning zero, schema validation failure) must fail the job so the previous good `films.json.gz` stays live. The auto‑filed GitHub issue on failure is a good pattern; keep it.
- **Plugin** runs in front of a user. Network errors, missing metadata, and a stale database must never crash navigation. Catch at the boundary (`_perform_sync`, `play_mubi_video`), log the traceback at `LOGERROR`, and show one short notification. Never swallow an exception without logging it.

Corollary: `except Exception` is acceptable only at those boundaries. Inside a helper, catch the specific exception you expect. There are ten broad catches in the plugin today; each should be reviewed against this rule.

### P12. Keep secrets, keys and rate limits out of the plugin.

- The plugin never embeds an API key. Users supply their own TMDb key; the backend holds `TMDB_API_KEY`, `OMDB_API_KEYS`, `RESEND_API_KEY`, and WireGuard secrets in GitHub Actions secrets only.
- `Mubi._sanitize_*_for_logging` redacts tokens before logging. Any new log line that includes headers, params or JSON goes through those helpers.
- The backend's OMDb key rotation (`_get_next_key`, `_mark_key_bad`) exists because OMDb's free tier is 1,000 calls/day. Keep enrichment incremental (only films missing `imdb_id`) so a full re‑enrichment is never needed in a scheduled run.

### P13. Every PR is small, tested, and describes the user‑visible effect.

Recent commits are a good model: one concern each, a body that explains what broke upstream and why the fix is shaped the way it is, and a regression test. Continue that, plus:

- Use conventional prefixes (`fix:`, `feat:`, `schema:`, `ci:`, `docs:`) so `git log --oneline` is scannable.
- If the change should ship to users, say so in the PR and add a line to the README changelog. If it should not (tests, refactors, docs), say that too so releases can be batched.
- Release when a user‑facing fix has merged and CI is green. Do not let fixes sit unreleased for weeks.

---

## 3. Suggested order of work

These are the concrete tasks the principles above imply, ordered by value over effort:

1. **Replace the `sed` version/news bump in `auto-release.yml` with a tested Python script.** (P8) Small, prevents a repeat of the v27 `<news>` corruption.
2. **Adopt ruff, fix the 77 `F`‑class findings, format once, gate in CI.** (P10) One afternoon; makes every later diff cleaner.
3. **Raise coverage floor to 80 %, mark the live‑network test, resolve the 17 skips.** (P7)
4. **Declare or delete `omdbapiKey`; decide the fate of the plugin‑side matcher.** (P3, P5)
5. **Convert `is_playable` and the `data_source.py` availability filter to datetime comparison.** (P6) Add tests with mixed `Z` / `+00:00` inputs.
6. **Extract `sync_service.py` from `navigation_handler.py`.** (P4) Start with the largest seam; the tests already exist and will guide the move.
7. **Move generated zips out of `main`; extract the VPN composite action.** (P8)
8. **Docs sweep: fix dead links, split README into user vs contributor docs, add "Last updated" lines.** (P9)
9. **Extract `nfo_writer.py` and `api_client.py`.** (P4) Larger refactors, do them when a feature already requires touching those areas.

---

## 4. Things that are already right and should not change

- The thin‑client architecture: scraper on GitHub Actions, plugin downloads one gzip. Do not move heavy work back into Kodi.
- MD5 verification of the downloaded database and the `SUPPORTED_VERSIONS` check.
- CODEOWNERS protection on the schema and its tests.
- Typed Kodi stubs in tests rather than blanket mocks.
- Level 2 filename sanitisation policy (remove only filesystem‑dangerous characters, keep Unicode).
- Auto‑filing a GitHub issue when a scheduled sync fails.
- `CLAUDE.md` plus `.claude/skills/` as the place for AI‑assistant context and workflows (migrated from `.agent/` on 2026‑09‑03). Keep `CLAUDE.md` terse; put rationale here.
- `constants.py` as the single home for external URLs, verified daily by `scripts/healthcheck.py`.
- Integer‑only add‑on versioning. Kodi does not need semver here, and the simplicity has served the project well.
