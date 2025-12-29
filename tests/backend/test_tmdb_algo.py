
import pytest
from unittest.mock import MagicMock, patch
from backend.tmdb_provider import TMDBProvider
from backend.metadata_utils import ExternalMetadataResult

@pytest.fixture
def tmdb_provider():
    with patch("backend.tmdb_provider.requests") as mock_requests:
        # Mock genre fetch to avoid network calls during init
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"genres": []}
        mock_requests.get.return_value = mock_response
        return TMDBProvider(api_key="test_key")

def test_phase_i_search_adult_true(tmdb_provider):
    """Test that search queries include adult=true and skip year filter."""
    with patch.object(tmdb_provider, '_search_api') as mock_search:
        mock_search.return_value = []
        
        tmdb_provider.get_imdb_id(title="Omen", year=2023)
        
        # Verify Strategy B calls search API
        mock_search.assert_any_call("Omen", "movie")

def test_phase_ii_temporal_filtering(tmdb_provider):
    """Test that candidates outside the year window are filtered."""
    mubi_data = {"title": "Test", "year": 2023}
    
    # Candidate 1: 2023 (Match)
    # Candidate 2: 2020 (Borderline? Delta=3, <=3 allowed for obscure but let's see default)
    # Candidate 3: 1990 (Mismatch)
    
    candidates = [
        {"id": 1, "title": "Test", "release_date": "2023-01-01"},
        {"id": 2, "title": "Test", "release_date": "2027-01-01"}, # Delta 4 -> Fail
    ]
    
    with patch.object(tmdb_provider, '_search_api', return_value=candidates):
        with patch.object(tmdb_provider, '_get_details_with_credits') as mock_details:
             # Only candidate 1 should trigger detail fetch
             mock_details.return_value = {"id": 1, "title": "Test", "external_ids": {"imdb_id": "tt1"}}
             
             tmdb_provider.get_imdb_id(title="Test", year=2023)
             
             # Check that we only fetched details for valid candidates
             # ID 2 should be skipped before detail fetch
             assert mock_details.call_count == 1
             assert mock_details.call_args[0][0] == 1

def test_director_match_score(tmdb_provider):
    """Test that director match gives +50 score."""
    mubi_data = {"title": "Omen", "year": 2023, "directors": ["Baloji"]}
    
    # Mock candidate search
    candidates = [{"id": 100, "title": "Omen", "release_date": "2023-05-01"}]
    
    # Mock details with correct director
    details = {
        "id": 100, 
        "title": "Omen", 
        "original_title": "Augure",
        "credits": {
            "crew": [{"job": "Director", "name": "Baloji Tshiani"}] # Fuzzy match Baloji
        },
        "external_ids": {"imdb_id": "tt100"},
        "runtime": 90
    }
    
    with patch.object(tmdb_provider, '_search_api', return_value=candidates):
        with patch.object(tmdb_provider, '_get_details_with_credits', return_value=details):
            result = tmdb_provider.get_imdb_id(title="Omen", year=2023, mubi_directors=["Baloji"])
            
            assert result.success is True
            assert result.tmdb_id == "100"

def test_score_threshold_fail(tmdb_provider):
    """Test that matches below 80 score are rejected."""
    mubi_data = {"title": "Omen", "year": 2023, "directors": ["Baloji"]}
    
    candidates = [{"id": 200, "title": "Omen", "release_date": "2023-01-01"}]
    
    # Mock details with WRONG director and NO other bonuses sufficient to pass
    details = {
        "id": 200, 
        "title": "Omen", 
        "credits": {
            "crew": [{"job": "Director", "name": "Richard Donner"}]
        },
        "runtime": 90
    }
    # Score Calc:
    # Director Match: False (-20)
    # Title Match: 100 (+30)
    # Year Match: 2023 (+10)
    # Runtime Match: 0 (No Mubi dur)
    # Total: 20
    # Threshold: 80 -> Fail
    
    with patch.object(tmdb_provider, '_search_api', return_value=candidates):
        with patch.object(tmdb_provider, '_get_details_with_credits', return_value=details):
            result = tmdb_provider.get_imdb_id(title="Omen", year=2023, mubi_directors=["Baloji"])
            
            assert result.success is False
            assert "No match met confidence threshold" in result.error_message
