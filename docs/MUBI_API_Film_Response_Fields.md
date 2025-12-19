# MUBI API - Single Film Response Fields

This document describes all fields returned by the MUBI API `/v4/browse/films` endpoint for a single film.

**Generated from live API call on:** 2025-12-05 18:42:29

## API Endpoint

```
GET https://api.mubi.com/v4/browse/films?sort=popularity&playable=true&page=1&per_page=1
```

## Response Structure

### Top-Level Response

```json
{
  "films": [<film_object>],
  "meta": {
    "current_page": <integer>,
    "next_page": <integer|null>,
    "previous_page": <integer|null>,
    "total_pages": <integer>,
    "total_count": <integer>,
    "per_page": <integer>
  }
}
```

## Film Object Fields

| Field Path | Type | Example Value |
|------------|------|---------------|
| `artworks` | array of objects | `[...9 items]` |
| `artworks[].focal_point` | object | `{...}` |
| `artworks[].focal_point.x` | float | `0.5` |
| `artworks[].focal_point.y` | float | `0.0` |
| `artworks[].format` | str | `"tile_artwork"` |
| `artworks[].image_url` | str | `"https://images.mubicdn.net/images/artworks/883158/cache-8..."` |
| `artworks[].locale` | null | `null` |
| `average_colour_hex` | str | `"9D8477"` |
| `average_rating` | float | `4.1` |
| `average_rating_out_of_ten` | float | `8.3` |
| `award` | null | `null` |
| `cast_members_count` | int | `4` |
| `comments_count` | int | `6` |
| `consumable` | object or null | `{...}` or `null` |
| `consumable.availability` | str | `"live"` |
| `consumable.availability_ends_at` | str | `"2026-11-14T08:00:00Z"` |
| `consumable.available_at` | str | `"2025-11-14T08:00:00Z"` |
| `consumable.exclusive` | bool | `false` |
| `consumable.expires_at` | str | `"2026-11-14T20:00:00Z"` |
| `consumable.film_date_message` | null | `null` |
| `consumable.film_id` | int | `453108` |
| `consumable.offered` | array of objects | `[{"type": "catalogue", "download_availability": null}]` |
| `consumable.offered[].download_availability` | null | `null` |
| `consumable.offered[].type` | str | `"catalogue"` |
| `consumable.permit_download` | bool | `true` |
| `consumable.playback_languages` | object | `{...}` |
| `consumable.playback_languages.audio_options` | array of str | `["French"]` |
| `consumable.playback_languages.extended_audio_options` | array of str | `["French (5.1)"]` |
| `consumable.playback_languages.media_features` | array of str | `["HD", "5.1"]` |
| `consumable.playback_languages.media_options` | object | `{...}` |
| `consumable.playback_languages.media_options.duration` | int | `1255` |
| `consumable.playback_languages.media_options.hd` | bool | `true` |
| `consumable.playback_languages.subtitle_options` | array of str | `[...9 items]` |
| `content_rating` | object | `{...}` |
| `content_rating.description` | str | `"Contains material that may not be suitable for children o..."` |
| `content_rating.icon_url` | null | `null` |
| `content_rating.label` | str | `"caution"` |
| `content_rating.label_hex_color` | str | `"e05d04"` |
| `content_rating.rating_code` | str | `"CAUTION"` |
| `content_warnings` | array of objects | `[{"id": 32, "name": "discriminatory language", "key": "discriminatory_language"}]` |
| `content_warnings[].id` | int | `32` |
| `content_warnings[].key` | str | `"discriminatory_language"` |
| `content_warnings[].name` | str | `"discriminatory language"` |
| `critic_review_rating` | int | `0` |
| `default_editorial` | str | `"Alice Diop colors in the blind spots of art history with ..."` |
| `default_editorial_html` | str | `"<p>Alice Diop colors in the blind spots of art history wi..."` |
| `directors` | array of objects | `[{"name": "Alice Diop", "name_upcase": "ALICE DIOP", "slug": "alice-diop"}]` |
| `directors[].name` | str | `"Alice Diop"` |
| `directors[].name_upcase` | str | `"ALICE DIOP"` |
| `directors[].slug` | str | `"alice-diop"` |
| `duration` | int | `21` |
| `episode` | null | `null` |
| `experiment_stills` | null | `null` |
| `experiment_stills_multi` | null | `null` |
| `genres` | array of str | `["Short", "Drama"]` |
| `hd` | bool | `true` |
| `highlighted_industry_event_entry` | null | `null` |
| `historic_countries` | array of str | `["France", "Italy"]` |
| `id` | int | `453108` |
| `industry_events_count` | int | `3` |
| `mubi_go_highlighted` | bool | `false` |
| `mubi_release` | bool | `false` |
| `number_of_ratings` | int | `1804` |
| `optimised_trailers` | null | `null` |
| `original_title` | str | `"Miu Miu Women's Tales #30"` |
| `popularity` | int | `593` |
| `portrait_image` | null | `null` |
| `press_quote` | null | `null` |
| `series` | null | `null` |
| `short_synopsis` | str | `"A Black woman wanders alone through the galleries of a mu..."` |
| `short_synopsis_html` | str | `"<p>A Black woman wanders alone through the galleries of a..."` |
| `should_use_safe_still` | bool | `false` |
| `slug` | str | `"fragments-for-venus"` |
| `star_rating` | null | `null` |
| `still_focal_point` | object | `{...}` |
| `still_focal_point.x` | float | `0.56` |
| `still_focal_point.y` | float | `0.28` |
| `still_url` | str | `"https://images.mubicdn.net/images/film/453108/cache-10777..."` |
| `stills` | object | `{...}` |
| `stills.large_overlaid` | str | `"https://assets.mubicdn.net/images/film/453108/image-w1504..."` |
| `stills.medium` | str | `"https://assets.mubicdn.net/images/film/453108/image-w448...."` |
| `stills.retina` | str | `"https://assets.mubicdn.net/images/film/453108/image-w1280..."` |
| `stills.small` | str | `"https://assets.mubicdn.net/images/film/453108/image-w256...."` |
| `stills.small_overlaid` | str | `"https://assets.mubicdn.net/images/film/453108/image-w512_..."` |
| `stills.standard` | str | `"https://assets.mubicdn.net/images/film/453108/image-w856...."` |
| `stills.standard_push` | str | `"https://assets.mubicdn.net/images/film/453108/image-w856_..."` |
| `title` | str | `"Fragments for Venus"` |
| `title_locale` | str | `"en-US"` |
| `title_treatment_url` | null | `null` |
| `title_upcase` | str | `"FRAGMENTS FOR VENUS"` |
| `trailer_id` | null | `null` |
| `trailer_url` | null | `null` |
| `web_url` | str | `"https://mubi.com/films/fragments-for-venus"` |
| `year` | int | `2025` |


## Complete Raw Response (Single Film)

```json
{
  "id": 453108,
  "slug": "fragments-for-venus",
  "title_locale": "en-US",
  "original_title": "Miu Miu Women's Tales #30",
  "year": 2025,
  "duration": 21,
  "stills": {
    "small": "https://assets.mubicdn.net/images/film/453108/image-w256.jpg?1762770049",
    "medium": "https://assets.mubicdn.net/images/film/453108/image-w448.jpg?1762770049",
    "standard": "https://assets.mubicdn.net/images/film/453108/image-w856.jpg?1762770049",
    "retina": "https://assets.mubicdn.net/images/film/453108/image-w1280.jpg?1762770049",
    "small_overlaid": "https://assets.mubicdn.net/images/film/453108/image-w512_overlaid.jpg?1762770049",
    "large_overlaid": "https://assets.mubicdn.net/images/film/453108/image-w1504_overlaid.jpg?1762770049",
    "standard_push": "https://assets.mubicdn.net/images/film/453108/image-w856_two_one.jpg?1762770049"
  },
  "still_focal_point": {
    "x": 0.56,
    "y": 0.28
  },
  "hd": true,
  "average_colour_hex": "9D8477",
  "trailer_url": null,
  "trailer_id": null,
  "popularity": 593,
  "web_url": "https://mubi.com/films/fragments-for-venus",
  "genres": [
    "Short",
    "Drama"
  ],
  "average_rating": 4.1,
  "average_rating_out_of_ten": 8.3,
  "number_of_ratings": 1804,
  "mubi_release": false,
  "should_use_safe_still": false,
  "still_url": "https://images.mubicdn.net/images/film/453108/cache-1077704-1762770049/image-w1280.jpg",
  "critic_review_rating": 0,
  "content_rating": {
    "label": "caution",
    "rating_code": "CAUTION",
    "description": "Contains material that may not be suitable for children or young adults.",
    "icon_url": null,
    "label_hex_color": "e05d04"
  },
  "episode": null,
  "short_synopsis": "A Black woman wanders alone through the galleries of a museum, carefully examining each painting, searching for something. Across Brooklyn, another Black woman wanders the streets, her gaze full of wonder at the Black women she encounters.",
  "short_synopsis_html": "<p>A Black woman wanders alone through the galleries of a museum, carefully examining each painting, searching for something. Across Brooklyn, another Black woman wanders the streets, her gaze full of wonder at the Black women she encounters.</p>",
  "historic_countries": [
    "France",
    "Italy"
  ],
  "portrait_image": null,
  "title": "Fragments for Venus",
  "title_upcase": "FRAGMENTS FOR VENUS",
  "title_treatment_url": null,
  "experiment_stills": null,
  "experiment_stills_multi": null,
  "default_editorial": "Alice Diop colors in the blind spots of art history with this thoughtful short starring Kayije Kagame (Saint Omer). Countering clich\u00e9s and absences in Black portraiture with the joys of real life, Fragments for Venus leaves behind Old Masters to widen the frame on where we find aesthetic pleasure.",
  "default_editorial_html": "<p>Alice Diop colors in the blind spots of art history with this thoughtful short starring Kayije Kagame (<em>Saint Omer</em>). Countering clich\u00e9s and absences in Black portraiture with the joys of real life, <em>Fragments for Venus</em> leaves behind Old Masters to widen the frame on where we find aesthetic pleasure.</p>",
  "cast_members_count": 4,
  "industry_events_count": 3,
  "comments_count": 6,
  "mubi_go_highlighted": false,
  "optimised_trailers": null,
  "directors": [
    {
      "name": "Alice Diop",
      "name_upcase": "ALICE DIOP",
      "slug": "alice-diop"
    }
  ],
  "consumable": {
    "film_id": 453108,
    "available_at": "2025-11-14T08:00:00Z",
    "availability": "live",
    "availability_ends_at": "2026-11-14T08:00:00Z",
    "expires_at": "2026-11-14T20:00:00Z",
    "film_date_message": null,
    "offered": [
      {
        "type": "catalogue",
        "download_availability": null
      }
    ],
    "exclusive": false,
    "permit_download": true,
    "playback_languages": {
      "audio_options": [
        "French"
      ],
      "subtitle_options": [
        "English",
        "English (SDH)",
        "Dutch",
        "French",
        "German",
        "Italian",
        "Portuguese",
        "Spanish (LatAm)",
        "Turkish"
      ],
      "media_options": {
        "duration": 1255,
        "hd": true
      },
      "media_features": [
        "HD",
        "5.1"
      ],
      "extended_audio_options": [
        "French (5.1)"
      ]
    }
  },
  "press_quote": null,
  "star_rating": null,
  "award": null,
  "series": null,
  "content_warnings": [
    {
      "id": 32,
      "name": "discriminatory language",
      "key": "discriminatory_language"
    }
  ],
  "artworks": [
    {
      "format": "tile_artwork",
      "locale": null,
      "image_url": "https://images.mubicdn.net/images/artworks/883158/cache-883158-1762772228/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    },
    {
      "format": "cover_artwork_box_episode",
      "locale": null,
      "image_url": "https://images.mubicdn.net/images/artworks/883159/cache-883159-1762772232/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    },
    {
      "format": "centered_background",
      "locale": null,
      "image_url": "https://images.mubicdn.net/images/artworks/883160/cache-883160-1762772236/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    },
    {
      "format": "centered_background_small",
      "locale": null,
      "image_url": "https://images.mubicdn.net/images/artworks/883161/cache-883161-1762772239/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    },
    {
      "format": "cover_artwork_horizontal",
      "locale": "en-US",
      "image_url": "https://images.mubicdn.net/images/artworks/883162/cache-883162-1762772243/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    },
    {
      "format": "cover_artwork_vertical",
      "locale": "en-US",
      "image_url": "https://images.mubicdn.net/images/artworks/883171/cache-883171-1762772287/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    },
    {
      "format": "cover_artwork_box",
      "locale": "en-US",
      "image_url": "https://images.mubicdn.net/images/artworks/883180/cache-883180-1762772320/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    },
    {
      "format": "tvos_cover_artwork",
      "locale": "en-US",
      "image_url": "https://images.mubicdn.net/images/artworks/883189/cache-883189-1762772353/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    },
    {
      "format": "cover_artwork_box_series",
      "locale": "en-US",
      "image_url": "https://images.mubicdn.net/images/artworks/883198/cache-883198-1762772361/images-original.png",
      "focal_point": {
        "x": 0.5,
        "y": 0.0
      }
    }
  ],
  "highlighted_industry_event_entry": null
}
```
