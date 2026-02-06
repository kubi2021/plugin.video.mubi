---
description: Semantic Test Auditor - Evaluate the quality and reality of unit tests using the Agent
---

# Semantic Test Auditor Workflow

This workflow leverages the AI Assistant (me) to directly evaluate the "semantic value" of your unit tests. I will check if tests are robust, plausible, and maintainable.

---

## Pre-Flight Check (Run First!)

**Before running any audit**, verify this workflow is up-to-date with the codebase:

> "Check if all modules are covered in the semantic-test-audit workflow"

When asked, I will:
1. **Scan all Python modules** in `repo/plugin_video_mubi/resources/lib/` and `backend/`
2. **Compare against the Priority Matrix** and Category tables below
3. **Report any gaps** — modules not listed or new modules added since last update
4. **Suggest updates** to add missing modules to the appropriate priority/category

> [!IMPORTANT]
> If the pre-flight check finds gaps, update this workflow **before** proceeding with audits.

---

## How to Use

### Single File Audit
> "Audit the tests for `[implementation_file]` vs `[test_file]`"

### Batch Audit (by category)
> "Audit all **Core Engine** modules"
> "Audit the **Backend** test suite"

### Priority-Based Audit
> "Audit the top 3 highest-priority modules"

---

## Evaluation Criteria

When you ask me to audit, I will evaluate based on:

1.  **Robustness (Score 1-5):**
    *   Do we test logic or just assignment (tautologies)?
    *   Do we check error states (Happy Path only)?
    *   Are assertions specific?

2.  **Reality Gap (Score 1-5):**
    *   Are mocks realistic (especially `xbmc` and API responses)?
    *   Does the test simulate the actual environment constraints?

3.  **Maintainability (Score 1-5):**
    *   Is the test brittle?
    *   Is the intent clear?

---

## Output Format (The "Antigravity" Style)

Produce the report in a structured markdown format:

```markdown
# Semantic Audit: [File Name]

## Executive Summary
**Verdict:** [Pass / Refactor Needed / Critical Failure]
[Brief 1-sentence overview of the findings]

## Scorecard
| Dimension | Score | Verdict |
| :--- | :--- | :--- |
| **Robustness** | X/5 | [Short comment] |
| **Reality Gap** | X/5 | [Short comment] |
| **Maintainability** | X/5 | [Short comment] |

## Qualitative Analysis
[Detailed analysis of the good, the bad, and the potential issues. Use code blocks to cite specific examples.]

## Recommendations
- [ ] [Actionable item 1]
- [ ] [Actionable item 2]
```

---

## Audit Targets

### Priority Matrix

| Priority | Module | Impl Size | Test Size | Reason |
|:--------:|--------|----------:|----------:|--------|
| 🔴 P1 | `mubi.py` | 57KB | 124KB | Core API client, highest complexity |
| 🔴 P1 | `navigation_handler.py` | 53KB | 85KB | All UI routing, user-facing |
| 🔴 P1 | `scraper.py` *(backend)* | 32KB | 16KB | Mubi data scraping, core pipeline |
| 🔴 P1 | `tmdb_provider.py` *(backend)* | 29KB | 9KB | TMDB matching, external API |
| 🟠 P2 | `film.py` | 40KB | 56KB | Data model, Bayesian rating logic |
| 🟠 P2 | `library.py` | 20KB | 39KB | Kodi library sync, NFO generation |
| 🟠 P2 | `enrich_metadata.py` *(backend)* | 10KB | 13KB | Metadata enrichment pipeline |
| 🟠 P2 | `rating_calculator.py` *(backend)* | 10KB | 7KB | Bayesian rating calculation |
| 🟠 P2 | `playback.py` | 9KB | 20KB | DRM, streaming, inputstream |
| 🟡 P3 | `data_source.py` | 19KB | 3KB | GitHub sync, caching |
| 🟡 P3 | `metadata_utils.py` *(backend)* | 10KB | — | Metadata utilities |
| 🟡 P3 | `omdb_provider.py` *(backend)* | 9KB | 7KB | OMDB API integration |
| 🟡 P3 | `session_manager.py` | 7KB | 11KB | Auth, token refresh |
| 🟡 P3 | `mpd_patcher.py` | 10KB | 9KB | MPD manipulation |
| 🟢 P4 | `generate_weekly_digest.py` *(backend)* | 10KB | — | Email digest generation |
| 🟢 P4 | `validate_schema.py` *(backend)* | 5KB | 13KB | JSON schema validation |
| 🟢 P4 | `migrations.py` | 6KB | 18KB | Schema migrations |
| 🟢 P4 | `metadata.py` | 5KB | 12KB | Kodi metadata formatting |
| 🟢 P4 | `filters.py` | 3KB | 4KB | List filtering |
| 🟢 P4 | `local_server.py` | 2KB | 3KB | Local HTTP server |
| 🟢 P4 | `countries.py` | 14KB | — | Country code mappings |
| 🟢 P4 | `coverage_optimizer.py` | 6KB | — | Multi-country coverage |
| 🟢 P4 | `models.py` | 6KB | — | Data models/types |
| 🟡 P3 | `external_metadata/tmdb_provider.py` | 8KB | 19KB | TMDB provider (plugin) |
| 🟡 P3 | `external_metadata/title_utils.py` | 9KB | — | Title matching utilities |
| 🟢 P4 | `external_metadata/omdb_provider.py` | 4KB | — | OMDB provider (plugin) |
| 🟢 P4 | `external_metadata/factory.py` | 3KB | — | Provider factory |
| 🟢 P4 | `external_metadata/base.py` | 1KB | — | Base provider class |

---

### Category: Core Engine (P1-P2)

These are the most critical modules—audit these first.

| Implementation | Test File |
|----------------|-----------|
| `resources/lib/mubi.py` | `tests/plugin_video_mubi/test_mubi.py` |
| `resources/lib/navigation_handler.py` | `tests/plugin_video_mubi/test_navigation_handler.py` |
| `resources/lib/film.py` | `tests/plugin_video_mubi/test_film.py` |
| `resources/lib/library.py` | `tests/plugin_video_mubi/test_library.py` |
| `resources/lib/playback.py` | `tests/plugin_video_mubi/test_playback.py` |

---

### Category: Kodi Interface

| Implementation | Test File |
|----------------|-----------|
| `plugin_video_mubi/addon.py` | `tests/plugin_video_mubi/test_addon.py` |
| `resources/lib/session_manager.py` | `tests/plugin_video_mubi/test_session_manager.py` |
| `resources/lib/metadata.py` | `tests/plugin_video_mubi/test_metadata.py` |

---

### Category: External Metadata Providers

| Implementation | Test File | Notes |
|----------------|-----------|-------|
| `resources/lib/external_metadata/tmdb_provider.py` | `tests/plugin_video_mubi/test_tmdb_provider.py` | TMDB integration |
| `resources/lib/external_metadata/title_utils.py` | `tests/plugin_video_mubi/test_external_metadata.py` | Title matching |
| `resources/lib/external_metadata/omdb_provider.py` | ⚠️ *No dedicated tests* | Uses shared fixtures |
| `resources/lib/external_metadata/factory.py` | ⚠️ *No dedicated tests* | Provider factory |
| `resources/lib/external_metadata/base.py` | ⚠️ *No dedicated tests* | Base class |

---

### Category: Static Data & Models

| Implementation | Test File | Notes |
|----------------|-----------|-------|
| `resources/lib/countries.py` | ⚠️ *No tests* | Country mappings |
| `resources/lib/coverage_optimizer.py` | ⚠️ *No tests* | Availability optimizer |
| `resources/lib/models.py` | ⚠️ *No tests* | Data models |

---

### Category: Backend (Scraper & Enrichment)

| Implementation | Test File | Notes |
|----------------|-----------|-------|
| `backend/scraper.py` | `tests/backend/test_scraper.py` | Core scraping logic |
| `backend/tmdb_provider.py` | `tests/backend/test_tmdb_algo.py` | TMDB matching |
| `backend/enrich_metadata.py` | `tests/backend/test_enrich_metadata.py` | Enrichment pipeline |
| `backend/rating_calculator.py` | `tests/backend/test_rating_calculator.py` | Bayesian rating |
| `backend/omdb_provider.py` | `tests/backend/test_omdb_provider.py` | OMDB API |
| `backend/metadata_utils.py` | ⚠️ *No tests* | Needs coverage |
| `backend/validate_schema.py` | `tests/backend/test_schema_v1.py` | JSON schema |
| `backend/generate_weekly_digest.py` | ⚠️ *No tests* | Email digest |
| `backend/generate_repo.py` | ⚠️ *No tests* | Repo generation |

---

### Category: Infrastructure & Utilities

| Implementation | Test File |
|----------------|-----------|
| `resources/lib/data_source.py` | `tests/plugin_video_mubi/test_data_source.py` |
| `resources/lib/mpd_patcher.py` | `tests/plugin_video_mubi/test_mpd_patcher.py` |
| `resources/lib/migrations.py` | `tests/plugin_video_mubi/test_migrations.py` |
| `resources/lib/filters.py` | `tests/plugin_video_mubi/test_filters.py` |
| `resources/lib/local_server.py` | `tests/plugin_video_mubi/test_local_server.py` |

---

### Category: Integration & E2E

| Test File | Scope |
|-----------|-------|
| `tests/plugin_video_mubi/test_integration.py` | Full plugin integration |
| `tests/plugin_video_mubi/test_kodi_plugin_integration.py` | Kodi-specific integration |
| `tests/plugin_video_mubi/test_e2e.py` | End-to-end flows |
| `tests/plugin_video_mubi/test_github_sync_flow.py` | GitHub sync workflow |

---

### Category: Shadow Backend (Repository Generator)

| Implementation | Test File |
|----------------|-----------|
| `_repo_generator.py` | `tests/repository_kubi2021/test_repo_generator.py` |

---

## Quick Reference: Batch Prompts

```
# Audit the most critical modules
"Audit all P1 priority modules from the semantic-test-audit workflow"

# Audit by category
"Audit the Core Engine category"
"Audit the Backend category"

# Audit a specific pair
"Audit resources/lib/mubi.py vs tests/plugin_video_mubi/test_mubi.py"

# Generate a summary report across multiple modules
"Generate a consolidated audit report for P1 and P2 modules"
```
