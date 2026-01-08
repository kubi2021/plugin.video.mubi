"""
Strict Schema Validation Tests for Mubi JSON v1.

PROTECTED FILE: This file is protected by CODEOWNERS.
Any changes require human review from @kubi2021.

These tests validate:
1. Required fields are always present
2. Optional fields have correct types when present
3. Nested objects follow expected structure
4. Golden file (production data) passes validation
"""

import pytest
import json
import os
import sys
from pathlib import Path

# Add backend to path for imports
BACKEND_PATH = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH))

try:
    import jsonschema
except ImportError:
    pytest.skip("jsonschema not installed", allow_module_level=True)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def v1_schema():
    """Load the v1 JSON schema."""
    schema_path = BACKEND_PATH / "schemas" / "v1_schema.json"
    with open(schema_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def minimal_valid_film():
    """Minimal film that should pass validation (only required fields)."""
    return {
        "mubi_id": 123456,
        "title": "Test Film"
    }


@pytest.fixture
def full_valid_film():
    """Fully populated film with all optional fields."""
    return {
        "mubi_id": 123456,
        "tmdb_id": 789012,
        "imdb_id": "tt1234567",
        "title": "Test Film",
        "original_title": "Film Test",
        "year": 2024,
        "duration": 120,
        "genres": ["Drama", "Thriller"],
        "directors": ["Director One", "Director Two"],
        "short_synopsis": "A short description.",
        "default_editorial": "A longer editorial description.",
        "historic_countries": ["France", "Italy"],
        "popularity": 500,
        "average_rating_out_of_ten": 7.5,
        "number_of_ratings": 1234,
        "hd": True,
        "critic_review_rating": 8.0,
        "content_rating": {
            "label": "caution",
            "rating_code": "CAUTION",
            "description": "Contains mature themes.",
            "icon_url": None
        },
        "mpaa": {
            "US": "PG-13"
        },
        "content_warnings": [
            {"id": 1, "name": "violence", "key": "violence"}
        ],
        "stills": {
            "small": "https://example.com/small.jpg",
            "medium": "https://example.com/medium.jpg",
            "standard": "https://example.com/standard.jpg",
            "retina": "https://example.com/retina.jpg",
            "small_overlaid": "https://example.com/small_overlaid.jpg",
            "large_overlaid": "https://example.com/large_overlaid.jpg",
            "standard_push": "https://example.com/standard_push.jpg"
        },
        "still_url": "https://example.com/still.jpg",
        "portrait_image": None,
        "artworks": [
            {"format": "tile_artwork", "locale": None, "image_url": "https://example.com/tile.png"},
            {"format": "cover_artwork_vertical", "locale": "en-US", "image_url": "https://example.com/cover.png"}
        ],
        "trailer_url": "https://example.com/trailer.mp4",
        "trailer_id": 99999,
        "optimised_trailers": None,
        "playback_languages": {
            "audio_options": ["English", "French"],
            "extended_audio_options": ["English (5.1)"],
            "subtitle_options": ["English", "Spanish"],
            "media_options": {"duration": 7200, "hd": True},
            "media_features": ["HD", "5.1"]
        },
        "available_countries": {
            "US": {
                "available_at": "2024-01-01T00:00:00Z",
                "availability": "live",
                "availability_ends_at": "2025-01-01T00:00:00Z",
                "expires_at": "2025-01-02T00:00:00Z"
            }
        },
        "award": {"name": "Cannes", "category": "Best Film", "year": 2024},
        "press_quote": "A masterpiece.",
        "episode": None,
        "series": None,
        "ratings": [
            {"source": "mubi", "score_over_10": 7.5, "voters": 1234},
            {"source": "imdb", "score_over_10": 7.0, "voters": 5000}
        ]
    }


# ─────────────────────────────────────────────
# Required Fields Tests
# ─────────────────────────────────────────────

class TestRequiredFields:
    """Tests for required field validation."""

    def test_minimal_valid_film_passes(self, v1_schema, minimal_valid_film):
        """Minimal film with only required fields should pass."""
        jsonschema.validate(minimal_valid_film, v1_schema)

    def test_missing_mubi_id_fails(self, v1_schema):
        """Film without mubi_id should fail."""
        film = {"title": "Test Film"}
        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(film, v1_schema)
        assert "'mubi_id' is a required property" in str(exc_info.value)

    def test_missing_title_fails(self, v1_schema):
        """Film without title should fail."""
        film = {"mubi_id": 123456}
        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(film, v1_schema)
        assert "'title' is a required property" in str(exc_info.value)

    def test_empty_object_fails(self, v1_schema):
        """Empty object should fail."""
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({}, v1_schema)


# ─────────────────────────────────────────────
# Type Validation Tests
# ─────────────────────────────────────────────

class TestTypeValidation:
    """Tests for field type validation."""

    def test_mubi_id_must_be_integer(self, v1_schema, minimal_valid_film):
        """mubi_id must be an integer."""
        minimal_valid_film["mubi_id"] = "not-an-int"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(minimal_valid_film, v1_schema)

    def test_title_must_be_string(self, v1_schema, minimal_valid_film):
        """title must be a string."""
        minimal_valid_film["title"] = 12345
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(minimal_valid_film, v1_schema)

    def test_genres_must_be_array_of_strings(self, v1_schema, minimal_valid_film):
        """genres must be an array of strings."""
        minimal_valid_film["genres"] = "Drama"  # string instead of array
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(minimal_valid_film, v1_schema)

        minimal_valid_film["genres"] = [1, 2, 3]  # array of ints
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(minimal_valid_film, v1_schema)

    def test_year_can_be_null(self, v1_schema, minimal_valid_film):
        """year can be null (optional field)."""
        minimal_valid_film["year"] = None
        jsonschema.validate(minimal_valid_film, v1_schema)


# ─────────────────────────────────────────────
# Nested Object Tests
# ─────────────────────────────────────────────

class TestNestedObjects:
    """Tests for nested object validation."""

    def test_content_rating_structure(self, v1_schema, minimal_valid_film):
        """content_rating must have correct structure."""
        minimal_valid_film["content_rating"] = {
            "label": "caution",
            "rating_code": "CAUTION",
            "description": "Test",
            "icon_url": None
        }
        jsonschema.validate(minimal_valid_film, v1_schema)

    def test_mpaa_structure(self, v1_schema, minimal_valid_film):
        """mpaa must have correct structure."""
        minimal_valid_film["mpaa"] = {
            "US": "R"
        }
        jsonschema.validate(minimal_valid_film, v1_schema)

        minimal_valid_film["mpaa"] = {
            "US": None
        }
        jsonschema.validate(minimal_valid_film, v1_schema)

        minimal_valid_film["mpaa"] = None
        jsonschema.validate(minimal_valid_film, v1_schema)

    def test_mpaa_rejects_extra_fields(self, v1_schema, minimal_valid_film):
        """mpaa should reject extra fields."""
        minimal_valid_film["mpaa"] = {
            "US": "R",
            "UK": "18" # UK not yet supported in schema
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(minimal_valid_film, v1_schema)

    def test_content_rating_rejects_extra_fields(self, v1_schema, minimal_valid_film):
        """content_rating should reject extra fields."""
        minimal_valid_film["content_rating"] = {
            "label": "caution",
            "unknown_field": "should fail"
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(minimal_valid_film, v1_schema)

    def test_stills_structure(self, v1_schema, minimal_valid_film):
        """stills must have correct structure."""
        minimal_valid_film["stills"] = {
            "small": "https://example.com/small.jpg",
            "medium": None,  # null is allowed
            "standard": "https://example.com/standard.jpg"
        }
        jsonschema.validate(minimal_valid_film, v1_schema)

    def test_artworks_requires_format_and_image_url(self, v1_schema, minimal_valid_film):
        """Each artwork must have format and image_url."""
        minimal_valid_film["artworks"] = [
            {"format": "tile", "locale": None}  # missing image_url
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(minimal_valid_film, v1_schema)

    def test_ratings_structure(self, v1_schema, minimal_valid_film):
        """ratings must be correct structure."""
        minimal_valid_film["ratings"] = [
            {"source": "mubi", "score_over_10": 7.5, "voters": 100},
            {"source": "bayesian", "score_over_10": 7.8, "voters": 999}
        ]
        jsonschema.validate(minimal_valid_film, v1_schema)

    def test_ratings_missing_required_field_fails(self, v1_schema, minimal_valid_film):
        """ratings entries must have all required fields."""
        minimal_valid_film["ratings"] = [
            {"source": "mubi", "score_over_10": 7.5}  # missing voters
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(minimal_valid_film, v1_schema)





# ─────────────────────────────────────────────
# Full Film Tests
# ─────────────────────────────────────────────

class TestFullFilm:
    """Tests for fully populated films."""

    def test_full_valid_film_passes(self, v1_schema, full_valid_film):
        """Fully populated film should pass validation."""
        jsonschema.validate(full_valid_film, v1_schema)


# ─────────────────────────────────────────────
# Golden File Tests
# ─────────────────────────────────────────────

class TestGoldenFile:
    """Tests using production data samples."""

    @pytest.fixture
    def golden_file_path(self):
        """Path to the golden file fixture."""
        return Path(__file__).parent.parent.parent / "tests" / "fixtures" / "golden_film_sample.json"

    def test_golden_file_validates(self, v1_schema, golden_file_path):
        """Production data must always pass schema validation."""
        if not golden_file_path.exists():
            pytest.skip("Golden file not found - run download_golden_sample.py first")

        with open(golden_file_path, 'r') as f:
            data = json.load(f)

        # Can be a single film or a list
        films = data if isinstance(data, list) else [data]

        errors = []
        for idx, film in enumerate(films):
            try:
                jsonschema.validate(film, v1_schema)
            except jsonschema.ValidationError as e:
                film_id = film.get("mubi_id", f"index_{idx}")
                errors.append(f"Film {film_id}: {e.message}")

        assert errors == [], f"Golden file validation failed:\n" + "\n".join(errors)
