---
name: test-writing
description: Write or extend pytest tests for a module in this repo, using its Kodi stubs and fixtures. Use when asked to add tests, cover a function, or write a regression test.
argument-hint: "<module or function> [scenario]"
---

# Test writing

## Where

| Code | Tests |
|---|---|
| `repo/plugin_video_mubi/resources/lib/<m>.py` | `tests/plugin_video_mubi/test_<m>.py` |
| `repo/plugin_video_mubi/addon.py` | `tests/plugin_video_mubi/test_addon.py` |
| `backend/<m>.py` | `tests/backend/test_<m>.py` |
| `_repo_generator.py`, `scripts/*.py` | `tests/repository_kubi2021/`, `tests/test_<script>.py` |

Extend the existing file. Create a new one only if none exists.

## Harness facts

- `tests/plugin_video_mubi/conftest.py` installs `xbmc*` and a global `requests` mock into `sys.modules` at import time. Do not re-mock them; patch behaviour on the existing objects.
- Prefer typed stubs from `tests/plugin_video_mubi/kodi_stubs.py` (`AddonStub`, dialog and monitor stubs) over `MagicMock`. They mimic real return types (`getSetting` → `""`, `getSettingBool` → `False`).
- Fixtures: `addon_mocks` (tests/conftest.py) for addon routing; `freezegun` is installed for time; `tests/fixtures/golden_film_sample.json` for realistic film dicts.
- Imports: `from plugin_video_mubi.resources.lib.<m> import X` (pytest `pythonpath = . repo`).
- Backend tests run without Kodi; use `requests-mock` or `mocker.patch` on the provider's session.

## Rules

- Arrange, Act, Assert, in that order, one behaviour per test. Name `test_<behaviour>_<scenario>`.
- For each function: happy path, edge (`None`, empty, huge, Unicode title), error (`pytest.raises`). Use `@pytest.mark.parametrize` for input matrices.
- Assert outcomes (return value, file written, `xbmc.log` called with `LOGERROR`), not that a collaborator was merely called.
- Real network is forbidden; mark anything that needs it `@pytest.mark.network`.
- No `@pytest.mark.skip`. Platform-specific code gets `@pytest.mark.skipif(sys.platform != ...)`.
- Regression test for a bug: name it after the bug, reproduce the failing input, and confirm it fails against the pre-fix code before committing.

## Finish

```bash
pytest <test file> -q
pytest tests/ --cov=repo/plugin_video_mubi --cov=backend --cov-config=.coveragerc --cov-report=term-missing -q | tail -40
```

Report the pass count and the coverage line for the module touched.
