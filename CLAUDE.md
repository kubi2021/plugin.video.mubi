# plugin.video.mubi

Kodi add-on for MUBI plus a GitHub-Actions backend that pre-computes the catalogue.
Rules below are terse on purpose. Rationale lives in `docs/DEVELOPMENT_PRINCIPLES.md`; read it only when a rule needs justifying.

## Layout

| Part | Path | Runtime | Notes |
|---|---|---|---|
| Plugin | `repo/plugin_video_mubi/` | Kodi, Python 3.8+ | stdlib + `requests`, `dateutil`, `inputstreamhelper` only |
| Backend | `backend/` | GH Actions, Py 3.11 | `scraper` → `enrich_metadata` → `rating_calculator` → `generate_repo` → `validate_schema` |
| Contract | `backend/schemas/v1_schema.json` | | CODEOWNERS-protected. Mirrors: `resources/lib/models.py` (tests only), `docs/mubi_film_schema.md` |
| Data | branch `database`, `v1/films.json.gz` + `.md5` | | Consumed by `resources/lib/data_source.py`, `SUPPORTED_VERSIONS=[1]` |
| URLs | `resources/lib/constants.py` | | Sole home of external URLs. `scripts/healthcheck.py` GETs `HEALTHCHECK_URLS` daily |
| Tests | `tests/{plugin_video_mubi,backend,repository_kubi2021,integration}` | | Kodi stubs: `tests/plugin_video_mubi/kodi_stubs.py`; golden: `tests/fixtures/golden_film_sample.json` |
| CI | `.github/workflows/` | | `test.yml` (py3.8–3.11, cov ≥65), 3 sync jobs, `healthcheck`, `weekly-digest`, `auto-release` (manual) |

## Commands

```bash
pytest tests/ -q
pytest tests/ --cov=repo/plugin_video_mubi --cov=backend --cov-config=.coveragerc --cov-report=term-missing
pytest tests/plugin_video_mubi/test_film.py -k <name>
python3 _repo_generator.py            # build zips; release workflow does this
```
Local Kodi dev: symlink `repo/plugin_video_mubi` into the Kodi addons dir (`docs/note_to_self.md`).

## Temporary files

All scratch output (throwaway tests, downloaded JSON, PR bodies, reports) goes in `tmp/` at the repo root. It is gitignored; `mkdir -p tmp` if absent. Never use `/tmp` or a session scratchpad. Name every file timestamp first: `YYYYMMDD-HHMMSS-<name>.<ext>`, e.g. `tmp/20260903-141500-audit-film-playable.py`.

## Hard rules: plugin (`repo/`)

- Python 3.8 syntax and stdlib only. No `match`, no `X | Y` types, no builtin generics at runtime (`list[str]`); use `typing` or `from __future__ import annotations`.
- Imports: stdlib, `requests`, `dateutil`, `inputstreamhelper`, `xbmc*`. Never `pydantic` at runtime (`models.py` is test-only).
- Paths: `xbmcvfs.translatePath`, never `xbmc.translatePath`. Logs: `xbmc.log(msg, xbmc.LOGxxx)`, never `print`.
- External URLs only in `constants.py`; add to `HEALTHCHECK_URLS` when a bare GET should succeed.
- Every `getSetting*` key must exist in `resources/settings.xml`. User-facing text → `strings.po` + `getLocalizedString`.
- API JSON: `.get()` with defaults, never chained `[]`. All HTTP via `Mubi._make_api_call`; redact with `_sanitize_*_for_logging`.
- Timestamps: parse with `dateutil`, compare aware datetimes. Never compare ISO strings.
- Filenames: strip only `< > : " / \ | ? *`, control chars, Windows reserved names; keep Unicode and punctuation. NFO text: strip control chars only. Policy: `docs/SECURITY_POLICY.md`.
- `except Exception` only at user boundaries (`_perform_sync`, `play_mubi_video`, `addon.py` router): log traceback at `LOGERROR`, show one short notification. Elsewhere catch specific exceptions. Never swallow silently.
- Do not grow `mubi.py`, `navigation_handler.py`, `film.py`. When touching them, extract into a new module (seams: principles P4). Functions over ~50 lines: split.

## Hard rules: backend (`backend/`)

- Fail loudly (`sys.exit(1)`) on anomalies so the previous `films.json.gz` stays live. Never emit partial data.
- Enrichment is incremental (only items missing `imdb_id`/`tmdb_id`). OMDb free tier is 1000 calls/day/key.
- Secrets via env and GH secrets only. Never log a key or token.
- Logic shared with the plugin (title normalisation, retry, TMDb matching): backend copy is canonical, plugin copy is legacy. Fix both or neither.

## Schema changes

Never edit `v1_schema.json` alone. Use `/schema-change` (schema + test + models + docs + `version_label` bump).

## Tests

- pytest, Arrange-Act-Assert, `test_<behaviour>_<scenario>`. Cover happy, edge (`None`/empty/huge), error (`pytest.raises`).
- Kodi modules: `kodi_stubs`, not bare `MagicMock`. `requests` is mocked globally in `tests/plugin_video_mubi/conftest.py`; real-network tests get `@pytest.mark.network`.
- Assert behaviour, not assignment or "mock was called". No permanent skips: guard with `sys.platform` or delete.
- Every bug fix ships with a regression test in the same commit.

## Commits and PRs

- Prefix `fix:` `feat:` `schema:` `ci:` `docs:` `test:` `refactor:`. Body says what broke and why the fix is shaped that way.
- One concern per PR. State whether it is user-visible (add a README changelog line) or not.
- Release: Actions → "Release Plugin Update" (manual). Version is an integer in `addon.xml`.

## Lessons learned (append after any mistake)

- Mubi adds API fields without notice. `additionalProperties: false` is the intended tripwire. Fix: allow in schema + test, prune in scraper if the plugin does not need it.
- Mubi retired `https://mubi.com/android`. `constants.py` and the healthcheck exist because of this.
- `xbmc.translatePath` is deprecated → `xbmcvfs`.
- 17 tests are skipped citing `os.startfile` (Windows-only). Resolve them; do not add more skips.
- The release workflow's `sed` produced nested `<news>` tags in v27. Edit XML with a parser, not `sed`.
- A redirect's `Location` is not proof its target exists. mubi.com 301s `/activate`, `/tv/activate` and the retired `/android` alike to `/tv/<path>`, which then 404s. Follow the chain and check the final status before baselining a URL.
- Notify-on-failure steps gate on `steps.<id>.outcome == 'failure'`, not bare `failure()`, or a broken `pip install` files an "endpoint failed" issue.

## Skills

| Skill | Use |
|---|---|
| `/hostile-audit` | Adversarial bug and security review with verified findings |
| `/schema-change` | `films.json` schema change procedure |
| `/test-writing` | Write pytest tests for a module |
| `/test-audit` | Score existing tests: robustness, reality gap, maintainability |
| `/kodi-logs` | Debug from a Kodi log file |
