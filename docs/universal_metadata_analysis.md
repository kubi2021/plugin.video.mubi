# Universal Metadata Scraper Analysis

**Date:** 2025-12-29
**Source:** `metadata.universal` (Version 5.6.1)

## Overview

The `metadata.universal` addon involves a traditional **XML-based Kodi scraper** (`universal.xml`) rather than a Python-based script. It relies on Kodi's internal scraper engine to execute Regular Expressions (Regex) that parse search results from external APIs.

The core logic for searching and matching movies resides in the `universal.xml` file, utilizing the `CreateSearchUrl` and `GetSearchResults` XML functions.

## Approach & Algorithm

The scraper's approach for matching movies with **The Movie Database (TMDB)** is straightforward and relies heavily on the API's own search relevance and Kodi's internal fuzzy matching.

### 1. Search Query Construction (`CreateSearchUrl`)

The scraper constructs a search request to the TMDB API using the movie's **Title** and **Year**.

-   **Endpoint:** `https://api.themoviedb.org/3/search/movie`
-   **Parameters Used:**
    -   `query`: The movie title. The scraper attempts to clean the title by removing trailing determiners (e.g., "The", "An", "A") to improve search relevance (e.g., "The Matrix, The" -> "The Matrix").
    -   `year`: The year of release. This is a critical filter that significantly narrows down the search candidates on the API side.
    -   `api_key`: A bundled API key.
    -   `language`: The user's configured search language (e.g., `en-US`).

### 2. Candidate Parsing (`GetSearchResults`)

The scraper parses the JSON response from TMDB using Regular Expressions. It does not perform complex logic (like Levenshtein distance calculations) within the XML itself. Instead, it extracts a list of valid candidates to pass back to Kodi.

-   **Extraction Logic:** It iterates through the JSON results and extracts:
    -   `title`: Localized title.
    -   `original_title`: The movie's original title (crucial for foreign films).
    -   `year`: Extracted from the `release_date` field (YYYY-MM-DD).
    -   `id`: The TMDB ID.

### 3. Matching & "Right Movie" Validation

Since the XML scraper cannot execute Python code for complex validation, it ensures "correctness" through the following mechanisms:

1.  **API-Side Filtering (The "Year" Check):**
    By explicitly sending the `year` parameter to TMDB, the API filters out movies with the same title but different release years. This is the primary "check" for accuracy.

2.  **Original Title Fallback:**
    The regex explicitly captures `original_title`. If a user searches for a movie by its original title (or if the file is named in the original language), Kodi's internal engine compares the file name against both the `title` (localized) and `original_title` returned by the scraper. This disambiguates matches where the localized title might differ significantly.

3.  **Kodi's Internal Ranking:**
    The scraper XML simply returns a *list* of candidates. Kodi's core C++ scraper engine then assigns a "score" to each candidate based on how closely the Title and Year match the search query. The candidate with the highest score is automatically selected (unless the user intervenes).

## Fields Used for Matching

The following fields are strictly used for the matching process:

-   **Title** (Cleaned)
-   **Year**
-   **Original Title** (for fallback matching)

## Summary of Checks

| Check / Logic | Implemented By | Description |
| :--- | :--- | :--- |
| **Title Match** | TMDB API + Kodi Core | TMDB finds relevant titles; Kodi ranks them by similarity. |
| **Year Match** | TMDB API | Sending `year=YYYY` excludes same-title films from different eras. |
| **Original Title** | Scraper Regex | Extracted to allow matching against non-localized filenames. |
| **JSON Integrity** | Scraper Regex | Multiple regex patterns exist to handle situations where JSON keys (id, title, date) appear in different orders, ensuring robustness. |

## Conclusion

The `metadata.universal` scraper relies on a **"Lean Scraper, Smart API"** approach. It offloads the heavy lifting of determining the "right" movie to the TMDB API (via the `year` parameter) and Kodi's internal fuzzy matching engine (via `original_title` support). It does not implement custom Pythonic matching algorithms.
