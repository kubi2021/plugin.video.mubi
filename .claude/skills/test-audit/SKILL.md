---
name: test-audit
description: Score the quality of existing tests for a module (robustness, reality gap, maintainability) and list concrete improvements. Use when asked whether tests are good, meaningful, or trustworthy, or to audit a test file.
argument-hint: "<module> | P1 | core | backend | all"
---

# Test audit

Evaluates whether tests would catch a real regression. Complements `/hostile-audit`, which hunts bugs in the implementation.

## Targets

| Arg | Pairs |
|---|---|
| P1 | `mubi.py`, `navigation_handler.py`, `backend/scraper.py`, `backend/tmdb_provider.py` |
| core | P1 + `film.py`, `library.py`, `playback.py`, `data_source.py` |
| backend | everything in `backend/` |
| `<module>` | that module and `tests/**/test_<module>.py` |
| all | every module under `repo/plugin_video_mubi/resources/lib` and `backend`; report gaps first |

Before auditing, list modules with no test file (`ls repo/plugin_video_mubi/resources/lib backend | sed 's/.py//' | while read m; do ls tests/**/test_$m.py 2>/dev/null || echo "NO TESTS: $m"; done`).

## Method

1. Read implementation and tests fully.
2. Map each public function to the tests that exercise it. Note functions with zero tests and tests that exercise nothing (fixtures only).
3. Mutation spot-check: pick three branches (an `if`, an `except`, a default), break each, run the file. Record which mutations survive.
4. Mock realism: compare `xbmc*` and API mocks against `kodi_stubs.py` and `docs/MUBI_API_Film_Response_Fields.md`. Flag mocks returning shapes the real API never does.

## Scores

| Dimension | 1 | 5 |
|---|---|---|
| Robustness | asserts assignments, happy path only | logic and error states asserted, mutations caught |
| Reality gap | `MagicMock()` everywhere, impossible data | typed stubs, golden data, real environment constraints |
| Maintainability | brittle patch paths, unclear intent | fixtures reused, names describe behaviour |

## Report

```
# Test audit: <module>
Verdict: Pass | Refactor | Critical
| Dimension | Score | Note |
Untested functions: ...
Surviving mutations: <what you broke, which tests still passed>
Unrealistic mocks: <file:line, why>
Recommendations (ordered):
- [ ] ...
```

Do not rewrite tests unless asked. If asked, use `/test-writing`.
