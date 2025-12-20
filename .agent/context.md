---
type: "always_apply"
---

# MUBI Plugin Project Context

## Project Overview

This is a **Kodi plugin** for streaming films from MUBI. The architecture uses a "thin client" design:

```
GitHub Actions (scraper) → films.json → Plugin (downloads & displays)
```

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Backend Scraper** | `backend/scraper.py` | Scrapes MUBI API, generates JSON |
| **Plugin** | `repo/plugin_video_mubi/` | Kodi addon that syncs and plays films |
| **Workflows** | `.github/workflows/` | Automated deep/shallow syncs |

---

## Current Schema Version

- **Version**: 1
- **Label**: `1.0-beta.1`
- **Status**: **BETA** - changes allowed with review

## Protected Files

These files require human review (CODEOWNERS):
- `tests/backend/test_schema_v1.py`
- `backend/schemas/*.json`

---

## Security Policy

**Level 2 (Filesystem Safety)** - optimal balance for Kodi plugins.

### Filename Sanitization
- **Remove**: `< > : " / \ | ? *` (filesystem-dangerous)
- **Preserve**: International chars (`Amélie`, `東京物語`), punctuation (`' & , ( )`)
- **NFO files**: Keep original titles intact, only remove control characters

### Protected Against
- Path traversal attacks (`../../../etc/passwd`)
- Windows reserved names (CON, PRN, AUX, COM1)
- Control character injection

---

## Testing Standards

**Framework**: `pytest` with Arrange-Act-Assert pattern

### Test Requirements
- ✅ Happy path (expected inputs/outputs)
- ✅ Edge cases (empty, `None`, zero, large values)
- ✅ Error handling (`pytest.raises`)
- ✅ Isolation via mocks (`pytest-mock`)

### Naming Convention
```
test_<function_or_behavior>_<scenario>
```

---

## Key Workflows

| Slash Command | Use For |
|---------------|---------|
| `/json-versioning` | Schema changes |
| `/bug-hunt` | Code review for bugs |
| `/security` | Filename sanitization rules |
| `/kodi-logs` | Debugging with Kodi logs |
| `/test-writing` | Writing pytest tests |

---

## Lessons Learned

> **When you make a mistake, document it here** so future agents don't repeat it.

### Kodi API Compatibility

**Target**: Kodi 19 (Matrix) and later only.

| ❌ Deprecated | ✅ Correct |
|--------------|-----------|
| `xbmc.translatePath()` | `xbmcvfs.translatePath()` |
| `xbmc.getCacheThumbName()` | Use `xbmcvfs` temp directory |

**Always use `xbmcvfs` for file operations**, not `xbmc`.

### Key Principles

1. **Test for deprecated APIs** - automated tests should catch these
2. **Defensive coding** - use proper error handling and logging
3. **No silent failures** - always log errors at appropriate levels

---

## Important Paths

- JSON database: `database/v1/films.json.gz` (on `database` branch)
- Pydantic models: `repo/plugin_video_mubi/resources/lib/models.py`
- Data source: `repo/plugin_video_mubi/resources/lib/data_source.py`
