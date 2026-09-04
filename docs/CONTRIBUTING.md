# Contributing to plugin.video.mubi

This guide covers everything a contributor needs: repository layout, the development
workflow, testing, the "Shadow Backend" that pre-computes the catalogue, and the
release process. User-facing install and usage instructions live in the
[README](../README.md).

See also [DEVELOPMENT_PRINCIPLES.md](DEVELOPMENT_PRINCIPLES.md) for the reasoning
behind the rules, and the top-level `CLAUDE.md` for the terse rule list.

## Repository Structure

This project uses a **Kodi repository structure** with automated release management:

```
├── repo/                           # Kodi repository files
│   └── plugin_video_mubi/          # Main MUBI add-on source code
│       ├── addon.xml               # Add-on definition (version managed here)
│       ├── addon.py                # Main entry point
│       └── resources/              # Add-on resources and Python modules
│           ├── settings.xml
│           ├── data/               # Pre-computed data (e.g. country_catalogue.json)
│           └── lib/                # Core Python modules
├── backend/                        # GitHub-Actions catalogue backend (Python 3.11)
├── tests/                          # Test suite
│   ├── plugin_video_mubi/          # Tests for the MUBI add-on
│   ├── backend/                    # Tests for the backend pipeline
│   ├── repository_kubi2021/        # Tests for the repository add-on
│   └── integration/                # Integration tests
├── docs/                           # Documentation
├── _repo_generator.py              # Repository build script
└── .github/workflows/              # CI/CD automation
```

## Development Workflow

1. **Make Changes**: Edit files in `repo/plugin_video_mubi/` (plugin) or `backend/` (catalogue backend).
2. **Run Tests**: `pytest tests/` (see [Testing](#testing)).
3. **Create PR**: Submit a pull request to the `main` branch. Keep one concern per PR.
4. **Merge PR**: Normal merge — merging does **not** cut a release.
5. **Manual Release** (when ready): Go to Actions → "Release Plugin Update" → Run workflow:
   - Enter release notes (user-facing description)
   - GitHub Actions automatically:
     - Increments the version number (simple: 5 → 6)
     - Updates `addon.xml` news section with release notes
     - Generates repository zip files
     - Creates the GitHub release with assets
     - Updates repository metadata

## Key Files for Contributors

- **Main Add-on Code**: `repo/plugin_video_mubi/`
- **Version Management**: `repo/plugin_video_mubi/addon.xml` (line 2) — auto-updated on release
- **Plugin Tests**: `tests/plugin_video_mubi/`
- **Backend Pipeline**: `backend/` (`scraper` → `enrich_metadata` → `rating_calculator` → `generate_repo` → `validate_schema`)
- **Schema Contract**: `backend/schemas/v1_schema.json` (CODEOWNERS-protected)
- **Release Workflow**: `.github/workflows/auto-release.yml` — manual trigger only

## Testing

The test suite lives under `tests/`. See [`tests/plugin_video_mubi/README.md`](../tests/plugin_video_mubi/README.md)
for the plugin test conventions (Kodi stubs, fixtures, mocking strategy).

```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/plugin_video_mubi/test_library.py

# Run with coverage (matches CI: minimum 80%)
pytest tests/ --cov=repo/plugin_video_mubi --cov=backend \
  --cov-config=.coveragerc --cov-report=term-missing
```

CI (`.github/workflows/test.yml`) runs the suite across Python 3.8–3.11 and enforces
coverage ≥ 80%.

## Manual Repository Generation

```bash
# Generate repository files manually
python3 _repo_generator.py

# Files created in repo/zips/:
# - plugin.video.mubi-X.zip (add-on)
# - repository.kubi2021-2.zip (repository)
# - addons.xml (metadata)
# - addons.xml.md5 (checksum)
```

## Country Coverage Data

The classic (direct-API) worldwide sync uses a pre-computed JSON catalogue to decide
which countries to fetch from. That file — `repo/plugin_video_mubi/resources/data/country_catalogue.json`
— maps each film to the countries where it is available, and
`resources/lib/coverage_optimizer.py` runs a greedy set-cover over it to find the
minimum set of countries needed for full coverage, starting with the user's country.

The catalogue is a **committed artifact**; there is currently no regeneration script in
the repository. If MUBI's catalogue changes significantly and the file needs to be
rebuilt, regenerate it and commit the result.

> Note: the direct-API sync also has a small built-in fallback set,
> `SYNC_COUNTRIES = ['CH', 'DE', 'US', 'GB', 'FR', 'JP']`, defined in
> `resources/lib/data_source.py` and `resources/lib/mubi.py`. This is used when no
> client country is configured. Most users are now on **Fast Sync**, which downloads
> the whole pre-computed catalogue from the backend and does not crawl per country.

## The "Shadow Backend" 👻

As of **Dec 2025**, this project uses a decoupled architecture to manage the global film catalogue.

**Concept:**
Instead of the Kodi plugin crawling the Mubi API for every user (which is slow and error-prone), a GitHub Action runs periodically to harvest the entire catalogue. This data is compressed and pushed to an orphan branch (`database`), acting as a "CDN" for the plugin.

**Benefits:**
- ⚡ **Instant Sync:** Plugin downloads a single compressed file instead of making thousands of API calls.
- 🛡️ **Reliability:** Scraper runs on a server, reducing rate-limiting issues for end-users.
- 📉 **Low Bandwidth:** Tiny updates compared to full crawls.

**How to Run Manually:**
1. Go to the [Actions tab](https://github.com/kubi2021/plugin.video.mubi/actions).
2. Select **"Update Mubi Catalog"**.
3. Click **"Run workflow"**.

**Where are the files?**
The generated database files are stored in the **[database branch](https://github.com/kubi2021/plugin.video.mubi/tree/database)** (orphan branch).
- **Catalogue:** [`v1/films.json.gz`](https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz)
- **Checksum:** [`v1/films.json.gz.md5`](https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz.md5)

For the weekly digest email pipeline, see [email_generation.md](email_generation.md).

## Versioning Policy

- **Simple incremental**: 1, 2, 3, 4, 5… (no semantic versioning)
- **Auto-managed**: Version increments automatically when a release is cut
- **Repository stable**: Repository version stays at 2, only add-on versions increment

## Release Process

**Manual Release Control**:
1. **Regular Development**: Merge PRs normally (tests, docs, refactoring) — no automatic releases
2. **When Ready to Release**:
   - Go to **Actions** → **"Release Plugin Update"** → **"Run workflow"**
   - Enter **release notes**: "Fixed audio detection and improved error handling"
   - Click **"Run workflow"**
3. **Result**: New version appears in GitHub releases, users get update notifications in Kodi

**When to Release**:
- ✅ New features for users
- ✅ Bug fixes affecting functionality
- ✅ Security updates
- ❌ Test improvements, documentation, refactoring

**Example Workflow**:
```
Week 1: Merge "Improve test coverage" → No release
Week 1: Merge "Update README" → No release
Week 2: Merge "Add 5.1 audio support" → Manual release v6
Week 2: Merge "Fix login timeout" → Include in next release
Week 3: Manual release v7 → "Audio improvements and login fixes"
```

---

_Last updated: 2026-09-03_
