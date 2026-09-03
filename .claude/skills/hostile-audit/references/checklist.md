# Hostile audit — checklist (sections A–J)

Read at Step 3. Never skip an applicable item; one bullet per item, PASS or FINDING or UNVERIFIED. Bold titles let a finding cite an exact ID. Cross-refs point at `CLAUDE.md` rules and `docs/DEVELOPMENT_PRINCIPLES.md` principles (Pn).

## A. Data & API contract

| # | Check | Verify |
|---|-------|--------|
| A1 | **Chained dict access** | Any `x['a']['b']` on an API/JSON response? MUBI omits fields without notice. Must be `.get('a', {}).get('b')` or schema-validated first. |
| A2 | **Empty-list indexing** | `[0]` on `directors`, `artworks`, `offered`, search results — empty list raises `IndexError`. |
| A3 | **Nullable coercion** | `int(x)`, `float(x)`, arithmetic on `tmdb_id`/`year`/`duration`/`popularity` which the schema allows to be `null`. |
| A4 | **Type drift the schema permits** | `tmdb_id` is `int\|str\|null`; `directors` is list-of-str in `films.json` but list-of-dict from the API (`data_source` normalises — is every path covered?). Code assuming one shape breaks on the other. |
| A5 | **`consumable` null** | `film_info.get('consumable')` can be `None`; `(... or {}).get(...)` is required, not `['consumable']`. |
| A6 | **Series leakage** | A series object reaching a film path. `get_film_metadata` filters on `series is not None` — is every entry point guarded? |
| A7 | **Pruned-field reads** | The plugin reads a field the scraper prunes (`_prune_film_data`/`_prune_series_data`), or the scraper keeps a field nothing consumes. Cross-check `scraper.py` prune list vs plugin reads. |
| A8 | **Raw HTTP outside the client** | Any `requests.get/post` not routed through `Mubi._make_api_call` (plugin) or `MubiScraper.session` (backend). Bypasses retry, headers, and log redaction. |
| A9 | **Rating fallback** | 10-point vs 5-point rating fallback, Bayesian vs MUBI rating selection in `film.py` — a missing/zero value silently yielding 0 or a wrong scale. |

## B. Time & availability

| # | Check | Verify |
|---|-------|--------|
| B1 | **String timestamp compare** | ISO timestamps compared with `<`/`>` as strings (`film.is_playable`, `data_source` availability filter). Breaks on `Z` vs `+00:00`, naive vs aware, differing precision. Parse with `dateutil`, compare aware datetimes (P6). |
| B2 | **Naive now()** | `datetime.now()` without `timezone.utc` compared against an aware/UTC API value. |
| B3 | **Availability window semantics** | `available_at` / `availability_ends_at` / `expires_at` confused; a film shown before `available_at` (the "upcoming" bug the changelog records) or after expiry. |
| B4 | **Missing-field default direction** | When `available_at` is absent, does the code default to playable or not? Safe default is not-playable; confirm. |
| B5 | **Shallow-sync staleness** | Backend shallow sync keeps `available_countries` for countries not re-scraped this run — an expired window persisting. |

## C. Filesystem & library

| # | Check | Verify |
|---|-------|--------|
| C1 | **Sanitisation bypass** | `_sanitize_filename`: `..`, a trailing dot/space (Windows strips them → collision), reserved names in any case (`CON`, `NUL`, `com1`), a title that is only prohibited chars → empty name. Policy: `docs/SECURITY_POLICY.md`. |
| C2 | **Folder-name collision** | Two distinct films sanitising to the same folder overwriting each other's `.strm`/`.nfo`. |
| C3 | **Length limit** | A long multibyte title exceeding the 255-byte filename limit (bytes, not chars). |
| C4 | **Partial write on crash** | `sync_locally` / `prepare_files_for_film` crashing mid-write leaving half a film folder; is it atomic or cleaned? |
| C5 | **Obsolete-file deletion scope** | `remove_obsolete_files` deleting anything the plugin did not create, or a path built from unsanitised input. |
| C6 | **Thread-shared paths** | Worker threads in `sync_locally` writing into the same directory or a shared counter without a lock. |
| C7 | **xbmcvfs vs os** | File ops using `os`/`open` on a `special://` path that only `xbmcvfs` resolves. Deprecated `xbmc.translatePath`. |
| C8 | **NFO integrity** | `_sanitize_xml_content` letting a control char or unescaped `&`/`<` into the NFO, breaking Kodi's scraper parse. |

## D. Concurrency & process model

| # | Check | Verify |
|---|-------|--------|
| D1 | **Cross-call state** | Kodi spawns a fresh Python process per plugin call. A class-level flag (`NavigationHandler._sync_in_progress`) does NOT survive across calls — ask what actually prevents two concurrent syncs. CONFIRMED if two invocations would each see the flag unset. |
| D2 | **Shared Kodi objects across threads** | `xbmcaddon.Addon()`, a `Dialog`, or a progress dialog created once and used from worker threads. |
| D3 | **Cancellation correctness** | `pDialog.iscanceled()` path: are futures cancelled, half-written files cleaned, counters left consistent? |
| D4 | **Setting read per thread** | `getSettingInt("sync_concurrency")` and friends read inside a thread pool; a bad/negative/zero value handled? |
| D5 | **Backend thread pool** | `scraper.py` `ThreadPoolExecutor`: a per-country failure swallowed by `future.result()` without recording an error; `MIN_TOTAL_FILMS` computed on partial results. |

## E. Kodi environment & settings

| # | Check | Verify |
|---|-------|--------|
| E1 | **Python 3.8 floor** | Under `repo/`: `match`, `X\|Y` unions at runtime, builtin generics (`list[str]`) without `from __future__ import annotations`, `str.removeprefix`, walrus misuse. CI tests 3.8. |
| E2 | **Import allowlist** | Plugin imports beyond stdlib + `requests`/`dateutil`/`inputstreamhelper`/`xbmc*`. `pydantic` must not be imported at runtime (`models.py` is test-only). |
| E3 | **Settings key exists** | Every `getSetting*("key")` has a matching `id="key"` in `settings.xml`. Known gap: `omdbapiKey` is read but undeclared (E-class CONFIRMED by grep). |
| E4 | **print / translatePath** | Any `print(`; any `xbmc.translatePath` (use `xbmcvfs`). |
| E5 | **Unlogged swallow** | `except` that neither re-raises nor logs at `LOGERROR`. `except Exception` allowed only at the three boundaries in `CLAUDE.md`. |
| E6 | **executebuiltin injection** | User/API string reaching `xbmc.executebuiltin`, `RunPlugin`, `Container.Update` without escaping. |
| E7 | **URL safety** | `_is_safe_url` bypass: scheme case (`JavaScript:`), `file:`, userinfo `@host`, IDN/homoglyph, redirect. Trailer/web-play URLs from the API. |
| E8 | **parse_qsl trust** | Router params from `parse_qsl` used without a default or type check; a missing/duplicated key. |
| E9 | **Hardcoded external URL** | An external URL outside `constants.py`; if it should answer a bare GET, absent from `HEALTHCHECK_URLS`. |

## F. Data flow & schema versioning

| # | Check | Verify |
|---|-------|--------|
| F1 | **Contract drift** | `v1_schema.json`, `models.py`, and `docs/mubi_film_schema.md` disagreeing on a field's presence or type. |
| F2 | **Version default** | `meta.version` missing → silently defaults to 1; an unsupported version only warning, then best-effort parsing wrong data. |
| F3 | **MD5 handling** | `.md5` format assumptions (`hash filename` vs bare); a redirect on the GitHub raw URL served as HTML passing as content. |
| F4 | **Unbounded load** | The gzip decompressed and `json.load`ed fully into memory on a low-end device; no size ceiling. |
| F5 | **Normalisation coverage** | `GithubDataSource` maps `mubi_id`→`id` and str→dict directors; does every consumer see the normalised shape, or do some read raw? |
| F6 | **additionalProperties tripwire** | A nested schema object missing `additionalProperties: false`, so a new upstream field passes silently instead of tripping CI (the intended early warning). |

## G. Backend pipeline

| # | Check | Verify |
|---|-------|--------|
| G1 | **Silent partial output** | An anomaly (fewer than `MIN_TOTAL_FILMS`, a `CRITICAL_COUNTRIES` member returning 0, `MAX_MISSING_PERCENT` exceeded) that does NOT `sys.exit(1)`, so bad data overwrites the good `films.json.gz`. |
| G2 | **Greedy targets degenerate** | `calculate_greedy_targets` on empty or single-country input producing an empty or wrong target set. |
| G3 | **Rating constants** | `rating_calculator` when the history file is absent or malformed — constants defaulting to something that skews every score. |
| G4 | **Enrichment idempotence** | `enrich_metadata` re-querying items that already have `imdb_id`/`tmdb_id`, burning the OMDb 1000/day quota. |
| G5 | **Key rotation** | OMDb `_get_next_key`/`_mark_key_bad` exhausting all keys silently, or a bad key not marked. |
| G6 | **Merge correctness** | Deep vs shallow merge in `scraper.run` losing a field, or `available_countries` from a prior run overwritten wrongly. |
| G7 | **Exit code masking** | A pipeline step whose real failure is hidden by `|| echo` or a bare `continue`. |

## H. CI & release

| # | Check | Verify |
|---|-------|--------|
| H1 | **continue-on-error + exit** | A step with `continue-on-error: true` that then `exit 1`s (the VPN steps): the failure is ignored and the job proceeds on no/old data. CONFIRMED by reading the YAML. |
| H2 | **force push guard** | The `github-pages-deploy-action` with `force: true` to `database`: what stops an empty or truncated `films.json.gz` from being published? |
| H3 | **sed on structured files** | `sed` editing `addon.xml` or JSON (the v27 nested-`<news>` corruption). Must parse with a real parser. |
| H4 | **Secret exposure** | A secret echoed, written to a file readable in logs, or interpolated into a shell without quoting. |
| H5 | **Action pinning** | An archived or unpinned action (`create-release@v1`, mixed `setup-python@v4`/`v5`). |
| H6 | **Duplicated CI logic** | The ~80-line VPN block copied across three sync workflows — a fix that must land in one place. |
| H7 | **Version bump integrity** | The release workflow's integer bump and news replacement round-tripping `addon.xml` without breaking XML. |

## I. Security & secrets

| # | Check | Verify |
|---|-------|--------|
| I1 | **Token in output** | A token/API key reaching a log line, a URL, an exception message, or a `.strm`/`.nfo`/DRM-config string. All logged headers/params/json must pass `Mubi._sanitize_*_for_logging`. |
| I2 | **local_server exposure** | `local_server.py` bind address and what it serves; reachable off-host? |
| I3 | **Untrusted to sink** | Anything from the network passed to `open()`, `subprocess`, `eval`, or a shell. |
| I4 | **DRM key material** | `generate_drm_config`/`generate_drm_license_key` embedding the token where it can be logged. |
| I5 | **PII in URL** | A user id/country/token placed in a query string that gets logged, vs a header. |

## J. Test quality (only when auditing tests)

| # | Check | Verify |
|---|-------|--------|
| J1 | **Tautology** | A test asserting a value it just assigned or mocked; asserting only that a mock was called. |
| J2 | **Mutation kill** | Break three branches in the implementation (an `if`, an `except`, a default), run the module's tests; a surviving mutation means the test is decorative (P6). Record each in the ledger. |
| J3 | **Mock realism** | `xbmc*`/API mocks returning shapes the real thing never does; use `kodi_stubs.py` and `docs/MUBI_API_Film_Response_Fields.md` as ground truth. |
| J4 | **Self-mock** | The unit under test itself patched out. |
| J5 | **Permanent skip** | `@pytest.mark.skip` without a `sys.platform` guard (the 17 `os.startfile` skips) — a deleted test in disguise. |
| J6 | **Global-mock reliance** | A test passing only because `requests` is globally mocked in conftest, hiding a real network call in the code. |
