# Mubi Film JSON Schema

This document describes the structure of a single film entry in the `films.json` file, including data from the Mubi API and enriched metadata from external sources (TMDB, IMDB).

**Last Updated:** 2025-12-18

---

## Overview

Each film in `films.json` is a combination of:
1. **Mubi API Data** – Scraped from `/v4/browse/films`
2. **Enriched Data** – Added via TMDB/IMDB lookups
3. **Scraper Metadata** – Added during the scraping/merge process

---

## Single Film Object Schema

```json
{
  // ─────────────────────────────────────────────
  // Core Identifiers
  // ─────────────────────────────────────────────
  "mubi_id": 243900,
  "tmdb_id": 123456,
  "imdb_id": "tt1234567",

  // ─────────────────────────────────────────────
  // Basic Metadata (from Mubi API)
  // ─────────────────────────────────────────────
  "title": "Example Film",
  "original_title": "Film Original Title",
  "year": 2023,
  "duration": 120,
  "genres": ["Drama", "Thriller"],
  "directors": ["Director Name 1", "Director Name 2"],
  "short_synopsis": "A short description of the film.",
  "default_editorial": "Mubi's editorial text about the film.",
  "historic_countries": ["France", "Italy"],

  // ─────────────────────────────────────────────
  // Mubi-specific Fields
  // ─────────────────────────────────────────────
  "popularity": 712,
  "average_rating_out_of_ten": 7.5,
  "number_of_ratings": 3611,
  "hd": true,
  "critic_review_rating": 0,

  // ─────────────────────────────────────────────
  // Content Rating & Warnings
  // ─────────────────────────────────────────────
  "content_rating": {
    "label": "caution",
    "rating_code": "CAUTION",
    "description": "Contains material that may not be suitable for children.",
    "icon_url": null
  },
  "content_warnings": [
    {
      "id": 32,
      "name": "discriminatory language",
      "key": "discriminatory_language"
    }
  ],

  // ─────────────────────────────────────────────
  // Imagery & Artwork
  // ─────────────────────────────────────────────
  "stills": {
    "small": "https://assets.mubicdn.net/images/film/243900/image-w256.jpg",
    "medium": "https://assets.mubicdn.net/images/film/243900/image-w448.jpg",
    "standard": "https://assets.mubicdn.net/images/film/243900/image-w856.jpg",
    "retina": "https://assets.mubicdn.net/images/film/243900/image-w1280.jpg",
    "small_overlaid": "https://assets.mubicdn.net/images/film/243900/image-w512_overlaid.jpg",
    "large_overlaid": "https://assets.mubicdn.net/images/film/243900/image-w1504_overlaid.jpg",
    "standard_push": "https://assets.mubicdn.net/images/film/243900/image-w856_two_one.jpg"
  },
  "still_url": "https://images.mubicdn.net/images/film/243900/cache-466837/image-w1280.jpg",
  "portrait_image": null,
  "artworks": [
    {
      "format": "tile_artwork",
      "locale": null,
      "image_url": "https://images.mubicdn.net/images/artworks/765938/images-original.png"
    },
    {
      "format": "cover_artwork_vertical",
      "locale": "en-US",
      "image_url": "https://images.mubicdn.net/images/artworks/840800/images-original.png"
    }
  ],

  // ─────────────────────────────────────────────
  // Trailer Information
  // ─────────────────────────────────────────────
  "trailer_url": "https://example.com/trailer.mp4",
  "trailer_id": 12345,
  "optimised_trailers": null,

  // ─────────────────────────────────────────────
  // Playback Languages (Global)
  // ─────────────────────────────────────────────
  "playback_languages": {
    "audio_options": ["French"],
    "extended_audio_options": ["French (5.1)"],
    "subtitle_options": ["English", "English (SDH)", "Dutch", "French", "German"],
    "media_options": {
      "duration": 1255,
      "hd": true
    },
    "media_features": ["HD", "5.1"]
  },

  // ─────────────────────────────────────────────
  // Availability & Playback (Per-Country)
  // ─────────────────────────────────────────────
  "available_countries": {
    "US": {
      "film_id": 243900,
      "available_at": "2025-04-15T07:00:00Z",
      "availability": "live",
      "availability_ends_at": "2027-04-15T07:00:00Z",
      "expires_at": "2027-04-15T19:00:00Z",
      "film_date_message": null,
      "exclusive": false,
      "permit_download": true,
      "offered": [
        {
          "type": "catalogue",
          "download_availability": null
        }
      ]
    },
    "GB": {
        // ... same structure for Great Britain ...
    }
  },

  // ─────────────────────────────────────────────
  // Awards & Press
  // ─────────────────────────────────────────────
  "award": {
    "name": "Cannes Film Festival",
    "category": "Best Director",
    "year": 2023
  },
  "press_quote": "A masterpiece of modern cinema.",

  // ─────────────────────────────────────────────
  // Series/Episode Info (null for films)
  // ─────────────────────────────────────────────
  "episode": null,
  "series": null,

  // ─────────────────────────────────────────────
  // Scraper-added Metadata
  // ─────────────────────────────────────────────
  // Legacy 'countries' list is removed in favor of available_countries keys
  
  // ─────────────────────────────────────────────
  // Ratings (Multi-source)
  // ─────────────────────────────────────────────
  "ratings": [
    {
      "source": "mubi",
      "score_over_10": 7.5,
      "voters": 3611
    },
    {
      "source": "imdb",
      "score_over_10": 6.8,
      "voters": 12345
    },
    {
      "source": "tmdb",
      "score_over_10": 7.1,
      "voters": 2890
    }
  ]
}
```

---

## Field Reference

### Core Identifiers

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `mubi_id` | integer | Unique Mubi film ID | Mubi API |
| `tmdb_id` | integer | TMDB movie ID | Enrichment |
| `imdb_id` | string | IMDB ID (e.g., "tt1234567") | Enrichment |

### Basic Metadata

| Field | Type | Description | Source | NFO Tag |
|-------|------|-------------|--------|---------|
| `title` | string | Display title (localized) | Mubi API | `<title>` |
| `original_title` | string | Original language title | Mubi API | `<originaltitle>` |
| `year` | integer | Release year | Mubi API | `<year>` |
| `duration` | integer | Runtime in minutes | Mubi API | `<runtime>` |
| `genres` | string[] | List of genre names | Mubi API | `<genre>` (multiple) |
| `directors` | string[] | List of director names | Mubi API | `<director>` (multiple) |
| `short_synopsis` | string | Brief plot summary | Mubi API | `<outline>` |
| `default_editorial` | string | Mubi's editorial description | Mubi API | `<plot>` |
| `historic_countries` | string[] | Production countries | Mubi API | `<country>` (multiple) |

### Mubi-specific Fields

| Field | Type | Description | Source | NFO Tag |
|-------|------|-------------|--------|---------|
| `popularity` | integer | Mubi popularity ranking | Mubi API | — |
| `average_rating_out_of_ten` | float | Mubi user rating (0-10) | Mubi API | `<ratings><rating>` |
| `number_of_ratings` | integer | Vote count | Mubi API | `<votes>` |
| `hd` | boolean | HD availability flag | Mubi API | — |
| `critic_review_rating` | integer | Critic rating | Mubi API | — |

### Content Rating & Warnings

| Field | Type | Description | Source | NFO Tag |
|-------|------|-------------|--------|---------|
| `content_rating` | object | Age/content rating info | Mubi API | `<mpaa>` |
| `content_rating.label` | string | Display label (e.g., "caution") | Mubi API | `<mpaa>` |
| `content_rating.rating_code` | string | Code (e.g., "CAUTION", "MATURE") | Mubi API | — |
| `content_rating.description` | string | Full description | Mubi API | — |
| `content_warnings` | object[] | Content warning tags | Mubi API | `<tag>` (multiple) |
| `content_warnings[].name` | string | Warning name | Mubi API | `<tag>` |

### Imagery & Artwork

| Field | Type | Description | Source | NFO Tag |
|-------|------|-------------|--------|---------|
| `stills` | object | Still image URLs at various sizes | Mubi API | `<thumb>`, `<fanart>` |
| `stills.retina` | string | High-res still (1280px) | Mubi API | `<thumb aspect="landscape">` |
| `still_url` | string | Primary still image URL | Mubi API | `<thumb>` |
| `portrait_image` | string\|null | Portrait/poster image | Mubi API | `<poster>` |
| `artworks` | object[] | Additional artwork assets | Mubi API | Various artwork types |
| `artworks[].format` | string | Type: tile_artwork, cover_artwork_vertical, etc. | Mubi API | — |
| `artworks[].image_url` | string | Artwork URL | Mubi API | — |

**Artwork Formats:**
- `tile_artwork` → General tile
- `cover_artwork_vertical` → Poster
- `cover_artwork_horizontal` → Banner
- `cover_artwork_box` → DVD-style box
- `centered_background` → Fanart
- `tvos_cover_artwork` → Apple TV artwork
- `clearlogo` → Transparent logo (if available)

### Trailer Information

| Field | Type | Description | Source | NFO Tag |
|-------|------|-------------|--------|---------|
| `trailer_url` | string\|null | Direct trailer URL | Mubi API | `<trailer>` |
| `trailer_id` | integer\|null | Mubi trailer ID | Mubi API | — |
| `optimised_trailers` | object\|null | Optimized trailer variants | Mubi API | — |

### Playback Languages (Global)
| `playback_languages` | object | Audio/subtitle info | Mubi API | `<fileinfo>` |
| `playback_languages.audio_options` | `<audio><language>` | Audio tracks | Mubi API | `<audio><language>` |
| `playback_languages.subtitle_options` | `<subtitle><language>` | Subtitles | Mubi API | `<subtitle><language>` |
| `playback_languages.media_features` | string[] | Features: "HD", "4K", "5.1" | Mubi API | — |

### Availability & Playback (available_countries)

Top-level `consumable` field is removed. Availability is now stored per-country in `available_countries` dictionary.

| Field | Type | Description | Source | NFO Tag |
|-------|------|-------------|--------|---------|
| `available_countries` | object | Dict of availability per country code | Scraper | `<mubi_availability>` |
| `{country_code}` | object | Availability data for specific country | Mubi API | `<country code="...">` |
| `{code}.available_at` | string | Availability start (ISO date) | Mubi API | `<available_at>` |
| `{code}.availability` | string | Status: "live", "upcoming" | Mubi API | `<availability>` |
| `{code}.availability_ends_at` | string | Availability end (ISO date) | Mubi API | `<availability_ends_at>` |

### Awards & Press

| Field | Type | Description | Source | NFO Tag |
|-------|------|-------------|--------|---------|
| `award` | object\|null | Award information | Mubi API | — |
| `press_quote` | string\|null | Press quote / tagline | Mubi API | `<tagline>` |

### Series/Episode Info

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `episode` | object\|null | Episode info (for series content) | Mubi API |
| `series` | object\|null | Parent series info (for series content) | Mubi API |

> **Note:** If `episode` or `series` is not null, the item is a series episode and is stored in `series.json` instead of `films.json`.

### Scraper Metadata

Legacy `countries` list is removed. Use keys of `available_countries` instead.


---

## Ratings Structure

Each rating source follows this schema:

```json
{
  "source": "mubi",          // Rating source identifier
  "score_over_10": 7.5,      // Normalized score (0-10)
  "voters": 3611             // Number of votes/ratings
}
```

### Supported Rating Sources

| Source | Description | Score Range |
|--------|-------------|-------------|
| `mubi` | Mubi community rating | 0-10 |
| `imdb` | IMDB user rating | 0-10 |
| `tmdb` | TMDB user rating | 0-10 |

---

## NFO Generation Requirements

The following fields from `films.json` are used to generate Kodi-compatible `.nfo` files:

### Required Fields (Must Be Present)

| JSON Field | NFO Tag | Notes |
|------------|---------|-------|
| `mubi_id` | `<uniqueid type="mubi">` | Default identifier |
| `title` | `<title>` | Display title |
| `original_title` | `<originaltitle>` | Original language |
| `year` | `<year>` | Release year |
| `duration` | `<runtime>` | Minutes |
| `genres` | `<genre>` | Multiple tags |
| `directors` | `<director>` | Multiple tags |
| `default_editorial` | `<plot>` | Primary description |
| `short_synopsis` | `<outline>` | Short description |

### Recommended Fields (Enhance NFO)

| JSON Field | NFO Tag | Notes |
|------------|---------|-------|
| `average_rating_out_of_ten` | `<ratings><rating>` | Mubi rating |
| `number_of_ratings` | `<votes>` | Vote count |
| `historic_countries` | `<country>` | Production countries |
| `content_rating.label` | `<mpaa>` | Age rating |
| `content_warnings[].name` | `<tag>` | Content warning tags |
| `{country}.available_at` | `<premiered>` | YYYY-MM-DD format (from active country) |
| `press_quote` | `<tagline>` | Press quote |
| `trailer_url` | `<trailer>` | Trailer URL |
| `stills.retina` | `<thumb>` | Artwork |
| `artworks[]` | `<poster>`, `<fanart>` | Additional artwork |
| `{country}.playback_languages.audio_options` | `<audio><language>` | Audio tracks (from active country) |
| `{country}.playback_languages.subtitle_options` | `<subtitle><language>` | Subtitles (from active country) |
| `tmdb_id` | `<uniqueid type="tmdb">` | Cross-reference |
| `imdb_id` | `<uniqueid type="imdb">`, `<imdbid>` | Cross-reference |

---

## Data Flow

```
┌─────────────────┐
│   Mubi API      │
│ /v4/browse/films│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Scraper      │  ← Extracts ALL fields listed above
│  (scraper.py)   │  ← Adds 'countries' metadata
│                 │  ← Separates films/series
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ films.json      │  (or series.json)
│ (raw scraped)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Metadata        │  ← TMDB API lookups
│ Enrichment      │  ← Adds tmdb_id, imdb_id
│ (enrich_meta    │  ← Adds ratings array
│  data.py)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ films.json      │
│ (enriched)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ NFO Generator   │  ← Creates .nfo files
│ (film.py)       │  ← Downloads artwork
│                 │  ← Fetches IMDB/TMDB
└─────────────────┘
```

---

## Sample Raw API Response

For the complete raw Mubi API response structure, see [MUBI_API_Film_Response_Fields.md](./MUBI_API_Film_Response_Fields.md).
