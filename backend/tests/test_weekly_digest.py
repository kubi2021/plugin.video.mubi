import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path to import script
sys.path.append(str(Path(__file__).parent.parent))

from generate_weekly_digest import (
    generate_digest,
    get_bayesian_score,
    get_earliest_availability,
    get_first_available,
    get_latest_expiration,
)

# Mock Data. first_available_at (when the film first became playable) is the
# digest's inclusion signal; available_at only drives the expiration display now.
MOCK_FILM_1 = {
    "mubi_id": 1,
    "title": "High Rating Film",
    "ratings": [{"source": "bayesian", "score_over_10": 9.5}],
    "first_available_at": "2025-01-01T00:00:00+00:00",
    "available_countries": {"US": {"available_at": "2025-01-01T00:00:00Z", "expires_at": "2025-01-31T00:00:00Z"}},
}

MOCK_FILM_2 = {
    "mubi_id": 2,
    "title": "Low Rating Film",
    "ratings": [{"source": "bayesian", "score_over_10": 5.0}],
    "first_available_at": "2025-01-05T00:00:00+00:00",
    "available_countries": {"UK": {"available_at": "2025-01-05T00:00:00Z"}},
}

MOCK_FILM_OLD = {
    "mubi_id": 3,
    "title": "Old Film",
    "ratings": [{"source": "bayesian", "score_over_10": 8.0}],
    # Rotated back into a country recently (recent available_at), but it first
    # became available long ago -> first_available_at is old -> not featured.
    "first_available_at": "2020-01-01T00:00:00+00:00",
    "available_countries": {"US": {"available_at": "2025-01-06T00:00:00Z"}},
}


def test_get_bayesian_score():
    assert get_bayesian_score(MOCK_FILM_1) == 9.5
    assert get_bayesian_score(MOCK_FILM_2) == 5.0
    assert get_bayesian_score({"ratings": []}) == 0
    assert get_bayesian_score({}) == 0


def test_get_earliest_availability():
    dt = get_earliest_availability(MOCK_FILM_1)
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 1
    assert dt.day == 1

    # Test multiple countries
    film_multi = {
        "available_countries": {
            "US": {"available_at": "2025-01-10T00:00:00Z"},
            "UK": {"available_at": "2025-01-01T00:00:00Z"},  # Earliest
        }
    }
    dt_multi = get_earliest_availability(film_multi)
    assert dt_multi.day == 1

    # Test None
    assert get_earliest_availability({}) is None


def test_get_latest_expiration():
    dt = get_latest_expiration(MOCK_FILM_1)
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 1
    assert dt.day == 31

    assert get_latest_expiration(MOCK_FILM_2) is None


def test_earliest_availability_naive_timestamp_is_utc():
    """Regression (hostile-audit F2): a tz-less available_at must be treated as
    aware (UTC), not returned naive."""
    film = {"available_countries": {"US": {"available_at": "2025-01-01T00:00:00"}}}  # no Z / offset
    dt = get_earliest_availability(film)
    assert dt is not None
    assert dt.tzinfo is not None  # aware, so it compares against the aware cutoff


def test_generate_digest_survives_naive_available_at(tmp_path):
    """Regression (hostile-audit F2): a naive expires_at must not crash the digest
    with 'can't compare offset-naive and offset-aware datetimes'. Inclusion keys
    on first_available_at, so the film is featured via that and its naive
    availability dates still flow through the 'Available until' display path."""
    mock_now = datetime(2025, 1, 7, tzinfo=timezone.utc)
    input_file = tmp_path / "films.json"
    output_file = tmp_path / "digest.md"

    film = {
        "mubi_id": 7,
        "title": "Naive Date Film",
        "ratings": [{"source": "bayesian", "score_over_10": 7.0}],
        "first_available_at": "2025-01-05T00:00:00+00:00",  # featured this run
        # Naive (no tz) availability dates must not crash get_latest_expiration.
        "available_countries": {"US": {"available_at": "2025-01-05T00:00:00", "expires_at": "2025-02-01T00:00:00"}},
    }
    input_file.write_text(json.dumps({"items": [film]}), encoding="utf-8")

    generate_digest(input_file, output_file, now_override=mock_now)  # must not raise

    assert output_file.exists()
    assert "Naive Date Film" in output_file.read_text()


def test_generate_digest_filtering(tmp_path):
    """Test that only newly-available movies are included and sorted by rating."""
    # Set "Now" to Jan 7th 2025
    mock_now = datetime(2025, 1, 7, tzinfo=timezone.utc)

    # 7 days ago = Jan 1st 2025
    # MOCK_FILM_1 first available Jan 1st -> Should include (borderline)
    # MOCK_FILM_2 first available Jan 5th -> Should include
    # MOCK_FILM_OLD first available 2020 -> Should exclude
    input_file = tmp_path / "films.json"
    output_file = tmp_path / "digest.md"

    data = {"items": [MOCK_FILM_2, MOCK_FILM_OLD, MOCK_FILM_1]}  # Mixed order

    with open(input_file, "w") as f:
        json.dump(data, f)

    generate_digest(input_file, output_file, now_override=mock_now)

    assert output_file.exists()
    content = output_file.read_text()

    # Verify filtering
    assert "High Rating Film" in content
    assert "Low Rating Film" in content
    assert "Old Film" not in content

    # Verify Sorting (High rated comes first in text)
    pos_high = content.find("High Rating Film")
    pos_low = content.find("Low Rating Film")
    assert pos_high < pos_low

    # Verify JSON output
    json_out = output_file.with_suffix(".json")
    assert json_out.exists()
    json_content = json.loads(json_out.read_text())
    assert len(json_content["newArrivals"]) == 2
    assert json_content["newArrivals"][0]["title"] == "High Rating Film"


def test_get_first_available_parsing():
    assert get_first_available({"first_available_at": "2025-01-01T00:00:00+00:00"}).year == 2025
    # Z suffix normalised to aware datetime
    assert get_first_available({"first_available_at": "2025-01-01T00:00:00Z"}).tzinfo is not None
    # Null / absent / unparseable -> None
    assert get_first_available({"first_available_at": None}) is None
    assert get_first_available({}) is None
    assert get_first_available({"first_available_at": "not-a-date"}) is None


def test_get_first_available_naive_is_utc():
    """Regression (hostile-audit F1): a first_available_at with no tz offset parses
    successfully as a NAIVE datetime, which then raises TypeError when compared
    against the aware cutoff. get_first_available must normalise naive -> UTC,
    exactly like get_earliest_availability does, so the value is comparable."""
    dt = get_first_available({"first_available_at": "2025-01-05T00:00:00"})  # no offset
    assert dt is not None
    assert dt.tzinfo is not None


def test_naive_first_available_does_not_crash_digest(tmp_path):
    """Regression (hostile-audit F1): a single film carrying a tz-naive
    first_available_at must not abort the entire digest with
    'can't compare offset-naive and offset-aware datetimes'."""
    mock_now = datetime(2025, 1, 7, tzinfo=timezone.utc)
    input_file = tmp_path / "films.json"
    output_file = tmp_path / "digest.md"

    film = {
        "mubi_id": 1,
        "title": "Naive First Available",
        "ratings": [{"source": "bayesian", "score_over_10": 7.0}],
        "first_available_at": "2025-01-05T00:00:00",  # naive, within lookback window
        "available_countries": {"US": {"available_at": "2025-01-05T00:00:00Z"}},
    }
    input_file.write_text(json.dumps({"items": [film]}), encoding="utf-8")

    generate_digest(input_file, output_file, now_override=mock_now)

    json_content = json.loads(output_file.with_suffix(".json").read_text())
    # Naive value is treated as UTC -> the film is featured, no crash.
    assert [m["id"] for m in json_content["newArrivals"]] == [1]


def test_rotated_old_film_is_not_featured(tmp_path):
    """Regression: a film with a recent available_at but an OLD first_available_at
    (rotated back into a country) must NOT be featured — this is the churn bug."""
    mock_now = datetime(2025, 1, 7, tzinfo=timezone.utc)
    input_file = tmp_path / "films.json"
    output_file = tmp_path / "digest.md"

    with open(input_file, "w") as f:
        json.dump({"items": [MOCK_FILM_OLD]}, f)  # available_at 2025-01-06, first_available 2020

    generate_digest(input_file, output_file, now_override=mock_now)

    json_content = json.loads(output_file.with_suffix(".json").read_text())
    assert json_content["newArrivals"] == []


def test_null_first_available_is_excluded(tmp_path):
    """A null first_available_at covers both pre-existing items and UPCOMING films
    (not playable yet). Neither must be featured, even with a recent available_at."""
    mock_now = datetime(2025, 1, 7, tzinfo=timezone.utc)
    input_file = tmp_path / "films.json"
    output_file = tmp_path / "digest.md"

    upcoming = {
        "mubi_id": 99,
        "title": "Upcoming Film",
        "first_available_at": None,
        # Available in the future (or simply not yet observed live).
        "available_countries": {"US": {"available_at": "2025-02-20T00:00:00Z"}},
    }
    with open(input_file, "w") as f:
        json.dump({"items": [upcoming]}, f)

    generate_digest(input_file, output_file, now_override=mock_now)

    json_content = json.loads(output_file.with_suffix(".json").read_text())
    assert json_content["newArrivals"] == []


def test_returning_film_is_featured_again(tmp_path):
    """A film that fully left the catalogue and later returned is re-created by
    the scraper and re-stamped with a fresh first_available_at, so it must appear
    in the digest again — long-absent films coming back are what we want."""
    mock_now = datetime(2025, 1, 7, tzinfo=timezone.utc)
    input_file = tmp_path / "films.json"
    output_file = tmp_path / "digest.md"

    returning = {
        "mubi_id": 42,
        "title": "Back After A Year",
        "ratings": [{"source": "bayesian", "score_over_10": 8.0}],
        # Pruned while gone, re-created and re-stamped on return.
        "first_available_at": "2025-01-06T00:00:00+00:00",
        "available_countries": {"US": {"available_at": "2025-01-06T00:00:00Z"}},
    }
    with open(input_file, "w") as f:
        json.dump({"items": [returning]}, f)

    generate_digest(input_file, output_file, now_override=mock_now)

    json_content = json.loads(output_file.with_suffix(".json").read_text())
    assert [m["id"] for m in json_content["newArrivals"]] == [42]
