# TMDB Performance Analysis (Session: 2025-12-11)

## 1. Statistics Summary

| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Total Titles Processed** | **414** | 100% |
| ✅ **Found Matches** | **398** | **96.1%** |
| ❌ **Failures** | **16** | **3.9%** |
| - *Not Found (No Match)* | 16 | 3.9% |
| - *HTTP Errors* | 0 | 0.0% |

**Comparison to OMDB:**
*   Success rate increased from **87.0%** (OMDB) to **96.1%** (TMDB).
*   Zero network timeouts or HTTP errors observed (vs 13% timeouts/errors with OMDB).

## 2. Failure Analysis

Inspection of the 16 "No match found" failures reveals specific patterns:

### A. Non-Movie Content (Music Videos)
*   `Leningrad Cowboys: Those Were the Days [MV]`
*   `Melrose: Rich Little Bitch [MV]`
*   `Leningrad Cowboys: These Boots`
*   **Cause:** MUBI includes music videos that are likely not in TMDB's movie database or require searching as "Music Video" type.

### B. Title Formatting/Version Issues
*   `Until the End of the World (Director's Cut)`
*   **Cause:** The suffix `(Director's Cut)` likely prevents an exact title match.
*   **Fix:** `TitleNormalizer` could strip text in parentheses looking like versions/cuts.

### C. Complex/Foreign Titles
*   `O-Bi, O-Ba: The End of Civilization` (Polish: *O-bi, o-ba: Koniec cywilizacji*)
*   `Ga-ga: Glory to the Heroes` (Polish: *Ga, ga: Chwala bohaterom*)
*   **Cause:** While TMDB handles international titles better than OMDB, some specific English translations might not match the primary or alternative titles exactly in TMDB.

### D. Obscure Shorts/Docs
*   `Crayons of Askalan` (Short documentary)
*   `Desire Pie` (Short animation)
*   **Cause:** Very niche content might simply be missing from TMDB.

## 3. Conclusions & Recommendations

The switch to TMDB has been highly effective, resolving the majority of missing metadata issues.

**Recommendations:**
1.  **Enhance Title Normalizer**: Add logic to strip common suffixes like `(Director's Cut)`, `(Restored)`, etc.
2.  **Music Video Handling**: Detecting "[MV]" in titles and skipping metadata lookup or using a different provider could reduce "false" failures.
3.  **Manual Matching**: For the remaining <4%, manual NFO creation is the only viable path if automated fuzzy matching fails.
