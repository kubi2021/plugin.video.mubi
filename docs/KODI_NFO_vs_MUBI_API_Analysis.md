# Kodi NFO Tags vs MUBI API Fields Analysis

This document compares Kodi NFO tags with what's currently implemented in the plugin and what's available from the MUBI API.

**Generated on:** 2025-12-05

## Summary

| Category | Count |
|----------|-------|
| ✅ NFO Tags Currently Used | 17 |
| ⚠️ NFO Tags Available from MUBI (Not Implemented) | 8 |
| ❌ NFO Tags Not Available from MUBI | 12 |

---

## ✅ NFO Tags Currently Implemented

| Kodi NFO Tag | MUBI API Field | Implementation Notes |
|--------------|----------------|---------------------|
| `<movie>` | - | Root element (required) |
| `<title>` | `title` | ✅ Fully implemented |
| `<originaltitle>` | `original_title` | ✅ Fully implemented |
| `<ratings>` | `average_rating_out_of_ten`, `number_of_ratings` | ✅ Using name="MUBI", max="10" |
| `<plot>` | `default_editorial` / `short_synopsis` | ✅ Uses editorial with synopsis fallback |
| `<outline>` | `short_synopsis` | ✅ Short synopsis for single-line display |
| `<runtime>` | `duration` | ✅ Duration in minutes |
| `<mpaa>` | `content_rating.label` | ✅ Content rating (CAUTION, etc.) |
| `<country>` | `historic_countries[]` | ✅ First country only (could use multiple) |
| `<genre>` | `genres[]` | ✅ Multiple genre tags |
| `<director>` | `directors[].name` | ✅ Multiple director tags |
| `<year>` | `year` | ✅ Release year (deprecated in Kodi v20) |
| `<trailer>` | `trailer_url`, `optimised_trailers[]` | ✅ Best trailer URL |
| `<thumb>` | `stills.*`, `artworks[]` | ✅ Landscape artwork |
| `<fanart>` | `stills.*`, `artworks[]` | ✅ Fanart implementation |
| `<fileinfo>/<streamdetails>` | `consumable.playback_languages.*` | ✅ Audio/subtitle languages |
| `<dateadded>` | - | ✅ Set to current date |

---

## ⚠️ NFO Tags Available from MUBI API (NOT YET IMPLEMENTED)

These tags could be populated with data already available from the MUBI API:

| Kodi NFO Tag | MUBI API Field | Priority | Notes |
|--------------|----------------|----------|-------|
| `<uniqueid>` | `id`, `slug`, `web_url` | **HIGH** | MUBI film ID should be stored as `<uniqueid type="mubi">` |
| `<premiered>` | `consumable.available_at` | **MEDIUM** | MUBI premiere date (preferred over `<year>` in Kodi v20+) |
| `<tag>` | `content_warnings[].name` | **MEDIUM** | Content warnings as library tags |
| `<tagline>` | `press_quote` | **LOW** | Press quote could work as tagline (often null) |
| `<actor>` | `cast_members_count` | **LOW** | Count available but need separate API call for actor details |
| `<fileinfo>/<video>/<codec>` | `consumable.playback_languages.media_features[]` | **LOW** | "HD", "4K" could map to resolution hints |
| `<fileinfo>/<video>/<hdrtype>` | `consumable.playback_languages.media_features[]` | **LOW** | Could detect HDR from features |
| `<fileinfo>/<audio>/<channels>` | `consumable.playback_languages.extended_audio_options[]` | **LOW** | "5.1" channel info available |

---

## ❌ NFO Tags NOT Available from MUBI API

These Kodi tags cannot be populated from the current MUBI API response:

| Kodi NFO Tag | Availability | Notes |
|--------------|--------------|-------|
| `<sorttitle>` | ❌ Not available | For custom sort order |
| `<userrating>` | ❌ Not available | Personal user rating |
| `<top250>` | ❌ Not available | IMDB ranking |
| `<playcount>` | ❌ Not available | Watch history (local only) |
| `<lastplayed>` | ❌ Not available | Watch history (local only) |
| `<credits>` | ❌ Not available | Writer credits |
| `<studio>` | ❌ Not available | Production studio |
| `<set>` | ❌ Not available | Movie set/collection |
| `<showlink>` | ❌ Not available | TV show link |
| `<resume>` | ❌ Not available | Playback position (local only) |
| `<id>` | ❌ Deprecated | Use `<uniqueid>` instead |
| `<imdbid>` | ❌ External lookup | Currently fetched via OMDB API |

---

## Recommended Improvements

### Priority 1: Add `<uniqueid>` Tag (HIGH)

```xml
<uniqueid type="mubi" default="true">453108</uniqueid>
```

**MUBI API source:** `id` field  
**Benefit:** Enables Kodi to properly identify films, prevents duplicates on re-scan

### Priority 2: Add `<premiered>` Tag (MEDIUM)

```xml
<premiered>2025-11-14</premiered>
```

**MUBI API source:** `consumable.available_at` (parse date from ISO format)  
**Benefit:** Kodi v20+ prefers this over deprecated `<year>` tag

### Priority 3: Add `<tag>` for Content Warnings (MEDIUM)

```xml
<tag>discriminatory language</tag>
<tag>violence</tag>
```

**MUBI API source:** `content_warnings[].name`  
**Benefit:** Adds searchable library tags for content warnings

### Priority 4: Improve `<country>` to Support Multiple (LOW)

Currently only first country is used. Should be:
```xml
<country>France</country>
<country>Italy</country>
```

**MUBI API source:** `historic_countries[]`  
**Benefit:** Complete country information

### Priority 5: Enhanced Audio Details (LOW)

```xml
<fileinfo>
  <streamdetails>
    <audio>
      <language>French</language>
      <channels>6</channels>  <!-- from "5.1" -->
    </audio>
  </streamdetails>
</fileinfo>
```

**MUBI API source:** `consumable.playback_languages.extended_audio_options[]`  
**Benefit:** Complete audio channel information

---

## MUBI API Fields NOT Used

The following MUBI API fields are available but not used in NFO generation:

| MUBI Field | Potential Use |
|------------|---------------|
| `slug` | Could be stored as additional uniqueid |
| `web_url` | Could link to MUBI website |
| `average_colour_hex` | Theming/UI enhancement |
| `popularity` | Custom sorting |
| `critic_review_rating` | Additional rating source |
| `mubi_release` | Library tag for MUBI exclusives |
| `industry_events_count` | Info about festival presence |
| `comments_count` | Social metadata |
| `award` | Festival/award information |

