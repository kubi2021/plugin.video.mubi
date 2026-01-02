import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, mock_open
import sys

# Add backend to path to import script
sys.path.append(str(Path(__file__).parent.parent))

from generate_weekly_digest import (
    get_bayesian_score,
    get_earliest_availability,
    get_latest_expiration,
    generate_digest
)

# Mock Data
MOCK_FILM_1 = {
    "title": "High Rating Film",
    "ratings": [{"source": "bayesian", "score_over_10": 9.5}],
    "available_countries": {
        "US": {"available_at": "2025-01-01T00:00:00Z", "expires_at": "2025-01-31T00:00:00Z"}
    }
}

MOCK_FILM_2 = {
    "title": "Low Rating Film",
    "ratings": [{"source": "bayesian", "score_over_10": 5.0}],
    "available_countries": {
        "UK": {"available_at": "2025-01-05T00:00:00Z"}
    }
}

MOCK_FILM_OLD = {
    "title": "Old Film",
    "ratings": [{"source": "bayesian", "score_over_10": 8.0}],
    "available_countries": {
        "US": {"available_at": "2020-01-01T00:00:00Z"}
    }
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
            "UK": {"available_at": "2025-01-01T00:00:00Z"} # Earliest
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


def test_generate_digest_filtering(tmp_path):
    """Test that only new movies are included and sorted by rating."""
    # Set "Now" to Jan 7th 2025
    mock_now = datetime(2025, 1, 7, tzinfo=timezone.utc)
    
    # 7 days ago = Jan 1st 2025
    # MOCK_FILM_1 available Jan 1st -> Should include (borderline)
    # MOCK_FILM_2 available Jan 5th -> Should include
    # MOCK_FILM_OLD available 2020 -> Should exclude
    
    input_file = tmp_path / "films.json"
    output_file = tmp_path / "digest.md"
    
    data = {"items": [MOCK_FILM_2, MOCK_FILM_OLD, MOCK_FILM_1]} # Mixed order
    
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
    json_out = output_file.with_suffix('.json')
    assert json_out.exists()
    json_content = json.loads(json_out.read_text())
    assert len(json_content['newArrivals']) == 2
    assert json_content['newArrivals'][0]['title'] == "High Rating Film"
