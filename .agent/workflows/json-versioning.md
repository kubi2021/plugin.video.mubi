---
description: JSON versioning rules and schema change procedures
---

# JSON Versioning Workflow

This workflow explains how to handle schema changes for the Mubi films.json and series.json files.

## Protected Files (CODEOWNERS)

The following files require human review (@kubi2021) before any changes can be merged:

- `/tests/backend/test_schema_v1.py` - Schema validation tests
- `/backend/schemas/` - JSON Schema definition files

**Agents CANNOT bypass these protections.** If your changes affect the schema, request human review.

## Current Version

- **Version**: 1
- **Version Label**: 1.0-beta.1
- **Status**: BETA (changes allowed with review)

---

## Making Schema Changes

### Step 1: Determine Change Type

| Change Type | Backward Compatible? | Action Required |
|-------------|---------------------|-----------------|
| Add optional field | ✅ Yes | Update schema, add test |
| Add new array item type | ✅ Yes | Update schema, add test |
| Change optional → required | ⚠️ BETA only | Update schema + tests |
| Remove field | ❌ No | **Human review required** |
| Change field type | ❌ No | **Human review required** |
| Restructure nested object | ❌ No | **Human review required** |

### Step 2: Update Files

1. **Update JSON Schema**: `backend/schemas/v1_schema.json`
2. **Update Pydantic Models**: `repo/plugin_video_mubi/resources/lib/models.py`
3. **Update Tests**: `tests/backend/test_schema_v1.py`
4. **Update Documentation**: `docs/mubi_film_schema.md`

### Step 3: Validate Changes

// turbo
```bash
cd /Users/kubi/Documents/GitHub/plugin.video.mubi
pytest tests/backend/test_schema_v1.py -v
```

### Step 4: Validate Against Production Data

// turbo
```bash
curl -sL https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz -o /tmp/films.json.gz
gzip -df /tmp/films.json.gz
python backend/validate_schema.py --path /tmp/films.json --version 1
```

---

## Version Numbering

### During Beta

```
1.0-beta.1 → 1.0-beta.2 → 1.0-beta.3 → 1.0 (stable)
```

Bump the beta number in `backend/scraper.py` after any schema change:
```python
'version_label': '1.0-beta.2',  # Increment this
```

### After Stable Release (1.0)

- Breaking changes require **v2**
- Only additive optional changes allowed in v1.x
- Plugin must support both v1 and v2 during transition

---

## Plugin Version Compatibility

The plugin checks schema version in `data_source.py`:

```python
SUPPORTED_VERSIONS = [1]  # Add 2, 3, etc. when ready
```

Behavior:
- **Supported version**: Normal parsing
- **Unsupported version**: Warning log, best-effort parsing
- **Parse failure**: User dialog "Please update the plugin"

---

## CI Validation

Schema validation runs in GitHub Actions before deployment:

```yaml
- name: Validate Schema
  run: python backend/validate_schema.py --path database/v1/films.json --version 1
```

If validation fails, the workflow will NOT deploy to the database branch.

---

## Emergency: Breaking Change in v1

If you MUST make a breaking change after v1.0 stable release:

1. Create `backend/schemas/v2_schema.json`
2. Create `tests/backend/test_schema_v2.py`
3. Update scraper to output `version: 2`
4. Update plugin `SUPPORTED_VERSIONS = [1, 2]`
5. Add v2 parser in `GithubDataSource`
6. Update `GITHUB_URL` to use v2 folder: `database/v2/films.json.gz`
7. Keep v1 files available for old plugins (transition period)
