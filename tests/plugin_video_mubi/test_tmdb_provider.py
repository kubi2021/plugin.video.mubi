
import pytest
from unittest.mock import Mock, patch
from plugin_video_mubi.resources.lib.external_metadata import (
    TMDBProvider,

    ExternalMetadataResult,
)

class TestTMDBProvider:
    """Test cases for TMDBProvider class."""

    def test_provider_initialization(self):
        """Test TMDB provider initializes correctly."""
        # Arrange
        api_key = "test_tmdb_key"
        config = {"max_retries": 3}

        # Act
        provider = TMDBProvider(api_key, config)

        # Assert
        assert provider.api_key == api_key
        assert provider.config == config
        assert provider.provider_name == "TMDB"
        assert provider.BASE_URL == "https://api.themoviedb.org/3"

    @patch('plugin_video_mubi.resources.lib.external_metadata.tmdb_provider.requests.get')
    def test_search_movie_success(self, mock_get):
        """Test successful movie search."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": 12345, "title": "Test Movie", "release_date": "2023-01-01"}
            ]
        }
        mock_get.return_value = mock_response

        provider = TMDBProvider("test_key")
        
        # Act
        tmdb_id = provider._search_movie("Test Movie", 2023)

        # Assert
        assert tmdb_id == 12345
        mock_get.assert_called_with(
            "https://api.themoviedb.org/3/search/movie",
            params={
                "api_key": "test_key",
                "query": "Test Movie",
                "include_adult": "false",
                "page": 1,
                "year": "2023"
            },
            timeout=10
        )

    @patch('plugin_video_mubi.resources.lib.external_metadata.tmdb_provider.requests.get')
    def test_search_movie_no_results(self, mock_get):
        """Test movie search returns None when no results."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        provider = TMDBProvider("test_key")

        # Act
        tmdb_id = provider._search_movie("Nonexistent Movie", 2023)

        # Assert
        assert tmdb_id is None
        
    @patch('plugin_video_mubi.resources.lib.external_metadata.tmdb_provider.requests.get')
    def test_search_movie_fuzzy_year(self, mock_get):
        """Test fuzzy year matching."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": 101, "title": "Miss", "release_date": "1990-01-01"}, # Way off
                {"id": 102, "title": "Hit", "release_date": "2024-01-01"},  # Target + 1
                {"id": 103, "title": "Miss", "release_date": "2020-01-01"}, # Way off
            ]
        }
        mock_get.return_value = mock_response
        
        provider = TMDBProvider("test_key")
        
        # Act
        # Target 2023. 2024 is within +/- 1
        tmdb_id = provider._search_movie("Movie", year=None, target_year=2023)
        
        # Assert
        assert tmdb_id == 102
        # Verify year param was NOT sent
        args, kwargs = mock_get.call_args
        assert "year" not in kwargs['params']

    @patch('plugin_video_mubi.resources.lib.external_metadata.tmdb_provider.requests.get')
    def test_get_movie_details_success(self, mock_get):
        """Test fetching movie details including IMDB ID."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "id": 12345,
            "external_ids": {
                "imdb_id": "tt9876543"
            }
        }
        mock_get.return_value = mock_response

        provider = TMDBProvider("test_key")

        # Act
        result = provider._get_movie_details(12345)

        # Assert
        assert result.success is True
        assert result.tmdb_id == "12345"
        assert result.imdb_id == "tt9876543"
        assert result.imdb_url == "https://www.imdb.com/title/tt9876543/"
        assert result.source_provider == "TMDB"

    @patch('plugin_video_mubi.resources.lib.external_metadata.tmdb_provider.requests.get')
    def test_get_imdb_id_integration(self, mock_get):
        """Test full flow of get_imdb_id."""
        # Arrange
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "results": [{"id": 100, "title": "The Movie"}]
        }
        
        # Mock details response
        mock_details_response = Mock()
        mock_details_response.raise_for_status.return_value = None
        mock_details_response.json.return_value = {
            "id": 100,
            "external_ids": {"imdb_id": "tt100"}
        }

        mock_get.side_effect = [mock_search_response, mock_details_response]

        provider = TMDBProvider("test_key")

        # Act
        result = provider.get_imdb_id("The Movie", year=2023)

        # Assert
        assert result.success is True
        assert result.tmdb_id == "100"
        assert result.imdb_id == "tt100"

    @patch('plugin_video_mubi.resources.lib.external_metadata.tmdb_provider.requests.get')
    def test_get_imdb_id_fallback_original_title(self, mock_get):
        """Test fallback to original title if primary title search fails."""
        # Arrange
        # 1. Search for English title -> No results
        mock_search_fail = Mock()
        mock_search_fail.status_code = 200
        mock_search_fail.json.return_value = {"results": []}

        # 2. Search for English title (Fuzzy) -> No results
        # NOTE: New logic tries fuzzy search for each candidate if strict fails
        
        # 3. Search for Original title (Strict) -> Success
        mock_search_success = Mock()
        mock_search_success.status_code = 200
        mock_search_success.json.return_value = {
            "results": [{"id": 200, "title": "Original Title"}]
        }

        # 4. Details -> Success
        mock_details = Mock()
        mock_details.raise_for_status.return_value = None
        mock_details.json.return_value = {
            "id": 200,
            "external_ids": {"imdb_id": "tt200"}
        }

        # Sequence: English Strict -> English Fuzzy -> Original Strict -> Details
        mock_get.side_effect = [mock_search_fail, mock_search_fail, mock_search_success, mock_details]

        provider = TMDBProvider("test_key")

        # Act
        result = provider.get_imdb_id("English Title", original_title="Original Title", year=2023)

        # Assert
        assert result.imdb_id == "tt200"
        # Search calls: English Strict, English Fuzzy, Original Strict
        assert mock_get.call_count == 4

    @patch('plugin_video_mubi.resources.lib.external_metadata.tmdb_provider.requests.get')
    def test_get_imdb_id_fallback_fuzzy_year(self, mock_get):
        """Test fallback to fuzzy year search if strict search fails."""
        # Arrange
        # 1. Strict search (with year) -> Fail
        mock_strict_fail = Mock()
        mock_strict_fail.status_code = 200
        mock_strict_fail.json.return_value = {"results": []}

        # 2. Fuzzy search (without year) -> Success (found with different year)
        mock_fuzzy_success = Mock()
        mock_fuzzy_success.status_code = 200
        mock_fuzzy_success.json.return_value = {
            "results": [
                {"id": 300, "title": "Movie", "release_date": "2022-01-01"} # 2023 - 1
            ]
        }

        # 3. Details -> Success
        mock_details = Mock()
        mock_details.raise_for_status.return_value = None
        mock_details.json.return_value = {
            "id": 300,
            "external_ids": {"imdb_id": "tt300"}
        }

        # Sequence of calls: strict -> fuzzy -> details
        mock_get.side_effect = [mock_strict_fail, mock_fuzzy_success, mock_details]

        provider = TMDBProvider("test_key")

        # Act
        result = provider.get_imdb_id("Movie", year=2023)

        # Assert
        assert result.success is True
        assert result.tmdb_id == "300"
        
        # Verify call arguments
        # Call 1: Strict
        args1, kwargs1 = mock_get.call_args_list[0]
        assert kwargs1['params']['year'] == "2023"
        
        # Call 2: Fuzzy
        args2, kwargs2 = mock_get.call_args_list[1]
        assert "year" not in kwargs2['params']
