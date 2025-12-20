# JSON Schema Versioning Guide

This document explains the versioning system for the Mubi plugin's JSON data format (`films.json` and `series.json`).

**Last Updated:** 2025-12-20

---

## Overview

The plugin syncs film data from a pre-computed JSON database hosted on GitHub. This database has a formal schema to ensure compatibility between:
- **Backend Scraper** (generates data) → runs on GitHub Actions
- **Plugin** (consumes data) → runs in Kodi

---

## Current Version

| Field | Value | Location |
|-------|-------|----------|
| `version` | `1` (integer) | JSON `meta.version` |
| `version_label` | `1.0-beta.1` | JSON `meta.version_label` |
| **Status** | **BETA** | — |

### Where It's Defined

1. **Scraper Output**: `backend/scraper.py` (lines ~597 and ~612)
   ```python
   'meta': {
       'version': 1,
       'version_label': '1.0-beta.1',
       ...
   }
   ```

2. **Generated JSON**: `database/v1/films.json` and `series.json` on the `database` branch

3. **Plugin Check**: `repo/plugin_video_mubi/resources/lib/data_source.py`
   ```python
   SUPPORTED_VERSIONS = [1]
   ```

---

## What "Beta" Means

During beta, the schema is **not frozen**. Changes are allowed with proper process:

| Change Type | Allowed? | Required Steps |
|-------------|----------|----------------|
| Add optional field | ✅ Yes | Update schema, add test |
| Remove field | ⚠️ With review | Human review required |
| Change field type | ⚠️ With review | Human review required |
| Restructure objects | ⚠️ With review | Human review required |
| Make optional → required | ✅ Yes | Update schema + tests |

**Key point**: Breaking changes are allowed during beta, but they must be reviewed.

---

## Strict Schema Testing

Schema tests ensure the JSON structure is always valid and prevent accidental breaking changes.

### What Gets Tested

| Test Category | What It Validates |
|---------------|-------------------|
| **Required Fields** | `mubi_id` and `title` must always be present |
| **Type Validation** | Fields have correct types (string, int, array, etc.) |
| **Nested Objects** | `content_rating`, `stills`, `artworks`, `ratings` structures |
| **Golden File** | Real production data always passes validation |

### Protected Files (CODEOWNERS)

The following files require **human review** before changes can be merged:

- `tests/backend/test_schema_v1.py` - Schema tests
- `backend/schemas/v1_schema.json` - Schema definition

This prevents AI agents or accidental commits from bypassing the tests.

### How to Work with Tests

**Adding a new field:**
1. Add field to `backend/schemas/v1_schema.json`
2. Add test case in `tests/backend/test_schema_v1.py`
3. Run tests: `pytest tests/backend/test_schema_v1.py -v`

**If tests fail:**
1. Check if your change matches the schema
2. If intentional breaking change during beta → update schema + tests together
3. If production data fails → schema may need to be more permissive (e.g., allow string OR int)

**Running tests locally:**
```bash
pytest tests/backend/test_schema_v1.py -v
```

---

## Transition to Stable (v1.0)

When you're ready to freeze the schema and release v1.0 stable:

### Step 1: Update Backend Scraper

In `backend/scraper.py`, change the version label:

```python
# Before (beta)
'version_label': '1.0-beta.1',

# After (stable)
'version_label': '1.0',
```

This appears in **two places** (films and series output).

### Step 2: Update Plugin (Optional)

In `repo/plugin_video_mubi/resources/lib/data_source.py`, no change needed for v1.

For **future versions (v2, v3)**, add them to:
```python
SUPPORTED_VERSIONS = [1, 2]  # When v2 is released
```

### Step 3: Update Documentation

Update this file's "Current Version" section to show:
- `version_label`: `1.0`
- **Status**: **STABLE**

### Step 4: Run Deep Sync

Trigger a deep sync in GitHub Actions to generate the new stable JSON.

---

## Post-Stable Rules

Once v1.0 is stable, stricter rules apply:

| Change Type | Allowed in v1.x? |
|-------------|------------------|
| Add optional field | ✅ Yes |
| Remove any field | ❌ **Requires v2** |
| Change field type | ❌ **Requires v2** |
| Restructure objects | ❌ **Requires v2** |

---

## Plugin Version Compatibility

The plugin handles version mismatches gracefully:

1. **Supported version**: Parses normally
2. **Unsupported version**: 
   - Logs a warning
   - Attempts best-effort parsing
   - If parsing fails, shows "Please update the plugin" dialog

### Adding Support for New Versions

When v2 is released:

1. Update plugin's `SUPPORTED_VERSIONS`:
   ```python
   SUPPORTED_VERSIONS = [1, 2]
   ```

2. Add version-specific parsing if needed:
   ```python
   if version == 2:
       return self._parse_v2(data)
   else:
       return self._parse_v1(data)
   ```

### Beta Versions (v2-beta, v3-beta, etc.)

When introducing a new major version as beta (e.g., `v2-beta`):

1. **Add a plugin setting** to opt-in to the beta schema:
   - Create setting: `use_beta_schema` (boolean, default: false)
   - Only users who enable this setting will use the new beta endpoint
   
2. **Maintain parallel endpoints**:
   - Stable: `database/v1/films.json.gz`
   - Beta: `database/v2/films.json.gz`
   
3. **Update plugin URL logic** in `data_source.py`:
   ```python
   if self._use_beta_schema():
       GITHUB_URL = "https://github.com/.../database/v2/films.json.gz"
   else:
       GITHUB_URL = "https://github.com/.../database/v1/films.json.gz"
   ```

4. **When v2 becomes stable**:
   - Make v2 the default
   - Remove/deprecate the beta setting
   - Keep v1 available for old plugin versions

---

## File Locations

| File | Purpose |
|------|---------|
| `backend/schemas/v1_schema.json` | JSON Schema definition |
| `backend/validate_schema.py` | CLI validation script |
| `tests/backend/test_schema_v1.py` | Protected schema tests |
| `tests/fixtures/golden_film_sample.json` | Production data snapshot |
| `.github/CODEOWNERS` | Requires human review for schema changes |
| `.agent/workflows/json-versioning.md` | Agent instructions |

---

## Schema Validation

### Local Validation

```bash
# Validate local films.json
python backend/validate_schema.py --path films.json --version 1
```

### CI Validation

Schema validation runs automatically in GitHub Actions before deployment:
- `mubi_deep_sync.yml` - "Validate Schema" step
- `mubi_shallow_sync.yml` - "Validate Schema" step

If validation fails, the workflow aborts and does NOT deploy to the database branch.

---

## Bumping Beta Version

When making changes during beta:

1. Make your schema changes
2. Update `version_label` in `backend/scraper.py`:
   ```python
   '1.0-beta.1' → '1.0-beta.2'
   ```
3. Update tests in `tests/backend/test_schema_v1.py`
4. Commit and push
5. Run deep sync to regenerate database
