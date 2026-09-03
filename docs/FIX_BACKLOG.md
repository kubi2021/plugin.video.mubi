# Fix backlog

**Last updated:** 2026-09-03

Ordered list of work implied by [DEVELOPMENT_PRINCIPLES.md](DEVELOPMENT_PRINCIPLES.md), by value over effort. Each item cites the principle it serves. Remove an item when it ships; add a line under "Done" with the PR number.

## Open

1. **Replace the `sed` version/news bump in `auto-release.yml` with a tested Python script.** (P8) Small, prevents a repeat of the v27 `<news>` corruption.
2. **Adopt ruff, fix the 77 `F`‑class findings, format once, gate in CI.** (P10) One afternoon; makes every later diff cleaner.
3. **Raise coverage floor to 80 %, mark the live‑network test, resolve the 17 skips.** (P7)
4. **Declare or delete `omdbapiKey`; decide the fate of the plugin‑side matcher.** (P3, P5)
5. **Convert `is_playable` and the `data_source.py` availability filter to datetime comparison.** (P6) Add tests with mixed `Z` / `+00:00` inputs.
6. **Extract `sync_service.py` from `navigation_handler.py`.** (P4) Start with the largest seam; the tests already exist and will guide the move.
7. **Move generated zips out of `main`; extract the VPN composite action.** (P8)
8. **Docs sweep: fix dead links, split README into user vs contributor docs, add "Last updated" lines.** (P9)
9. **Extract `nfo_writer.py` and `api_client.py`.** (P4) Larger refactors, do them when a feature already requires touching those areas.

## Done

- 2026-09-03: `constants.py` as the single home for external URLs, plus daily `healthcheck.yml` (P2). PR #46.
