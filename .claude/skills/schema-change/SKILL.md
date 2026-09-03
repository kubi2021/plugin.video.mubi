---
name: schema-change
description: Procedure for changing the films.json / series.json schema (adding, removing, or retyping a field). Use whenever a Mubi API change breaks "Validate Schema" in CI, or a new field is needed by the plugin.
argument-hint: "<field path> <add|remove|retype> [reason]"
---

# Schema change

Contract between backend (producer) and plugin (consumer). Version 1, label `1.0-beta.N`, status BETA.
Protected by CODEOWNERS: `backend/schemas/v1_schema.json`, `tests/backend/test_schema_v1.py`. Say so in the PR; a human must approve.

## Classify

| Change | Compatible | Needs |
|---|---|---|
| Add optional field | yes | schema + test |
| Optional → required | beta only | schema + test |
| Remove field, change type, restructure | no | human review, consider v2 |

Default for a new upstream field the plugin does not need: **allow it in the schema, prune it in `scraper.py`** (`_prune_film_data` / `_prune_series_data`). Shallow sync keeps old per-country data, so the schema must accept the field even if fresh scrapes drop it.

## Edit, in one PR

1. `backend/schemas/v1_schema.json`. Keep `additionalProperties: false` on nested objects; it is the tripwire.
2. `tests/backend/test_schema_v1.py`: four cases: present, `null`, absent, unknown sibling rejected.
3. `repo/plugin_video_mubi/resources/lib/models.py` (Pydantic mirror, test-only).
4. `docs/mubi_film_schema.md`.
5. `backend/scraper.py`: bump `version_label` (`1.0-beta.N+1`). Prune if applicable.
6. If the plugin reads the field: `mubi.get_film_metadata` or `data_source.GithubDataSource`, with `.get()` and a default, plus a plugin test.

## Validate

```bash
pytest tests/backend/test_schema_v1.py tests/plugin_video_mubi/test_data_loading_schema.py -q
```

Against production data (into the repo's gitignored `tmp/`, timestamp-first name):

```bash
mkdir -p tmp && F="tmp/$(date +%Y%m%d-%H%M%S)-films" && curl -sL https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz -o "$F.json.gz" && gzip -df "$F.json.gz" && python backend/validate_schema.py --path "$F.json" --version 1
```

Refresh `tests/fixtures/golden_film_sample.json` with two or three real items if the field is now common.

## Breaking change after 1.0

New `v2_schema.json` and `test_schema_v2.py`; scraper emits `version: 2` to `database/v2/`; plugin `SUPPORTED_VERSIONS = [1, 2]` with a v2 parser; keep v1 files published during transition.

## Commit

`schema: <what> (<why, e.g. Mubi added X on YYYY-MM-DD>)`. Body: how many items failed validation, and whether the plugin consumes the field.
