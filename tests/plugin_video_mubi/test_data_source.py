"""
Test suite for Data Source classes.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
"""

from unittest.mock import Mock, patch, call
from plugin_video_mubi.resources.lib.data_source import MubiApiDataSource
import pytest

class TestMubiApiDataSource:
    """Test cases for the MubiApiDataSource class."""

    def test_get_all_films_success(self):
        """Test successful retrieval of films from API."""
        # Arrange
        mubi_mock = Mock()
        countries = ['US', 'UK']
        data_source = MubiApiDataSource(mubi_mock)

        # Mock _fetch_films_for_country to return different films for different countries
        def fetch_side_effect(country_code, progress_callback=None, playable_only=True, page_callback=None, global_film_ids=None):
            if country_code == 'US':
                return ({1, 2}, {
                    1: {'id': 1, 'title': 'US Movie'},
                    2: {'id': 2, 'title': 'Shared Movie'}
                }, 2, 1)
            elif country_code == 'UK':
                return ({2, 3}, {
                    2: {'id': 2, 'title': 'Shared Movie'},
                    3: {'id': 3, 'title': 'UK Movie'}
                }, 2, 1)
            return (set(), {}, 0, 0)

        mubi_mock._fetch_films_for_country.side_effect = fetch_side_effect

        progress_callback = Mock()

        # Act
        films = data_source.get_films(progress_callback=progress_callback, countries=countries)

        # Assert
        # get_films returns a list of dictionaries
        assert len(films) == 3
        
        # Verify mubi._fetch_films_for_country was called for each country
        assert mubi_mock._fetch_films_for_country.call_count == 2
        
        # Verify progress callback was updated
        progress_callback.assert_any_call(current_films=0, total_films=0, current_country=1, total_countries=2, country_code='US')


    def test_get_all_films_empty_countries(self):
        """Test behavior with empty country list."""
        mubi_mock = Mock()
        data_source = MubiApiDataSource(mubi_mock)

        # If we pass empty list, it should return empty list
        films = data_source.get_films(countries=[])

        assert films == []
        mubi_mock._fetch_films_for_country.assert_not_called()

    def test_get_all_films_fetch_error(self):
        """Test error handling during fetch (should continue or fail gracefully)."""
        mubi_mock = Mock()
        countries = ['US']
        data_source = MubiApiDataSource(mubi_mock)

        # Simulate exception
        mubi_mock._fetch_films_for_country.side_effect = Exception("API Error")

        # Expecting exception to propagate
        with pytest.raises(Exception, match="API Error"):
            data_source.get_films(countries=countries)


class TestGithubDataSource:
    """Test cases for the GithubDataSource class."""
    
    @pytest.fixture
    def mock_gzip_data(self):
        """Create mock gzip-compressed JSON data."""
        import gzip
        import json
        import io
        
        data = {
            "meta": {"version": 1, "version_label": "test"},
            "items": [
                {
                    "id": 1,
                    "title": "Test Movie",
                    "directors": ["John Doe"],  # String list (needs normalization)
                    "available_countries": {
                        "US": {"availability": "live"},
                        "GB": {"availability": "live"}
                    }
                },
                {
                    "id": 2,
                    "title": "Another Movie",
                    "directors": [{"name": "Jane Doe"}],  # Already normalized
                    "available_countries": {
                        "US": {"availability": "live"}
                    }
                }
            ]
        }
        
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
            gz.write(json.dumps(data).encode('utf-8'))
        return buffer.getvalue()
    
    def test_github_data_source_successful_download(self, mock_gzip_data):
        """Test successful download and parsing of GitHub data."""
        import hashlib
        from plugin_video_mubi.resources.lib.data_source import GithubDataSource
        
        expected_md5 = hashlib.md5(mock_gzip_data).hexdigest()
        
        # Mock at the requests module level since it's imported inside get_films()
        with patch('requests.Session') as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance
            
            # Mock MD5 response
            md5_response = Mock()
            md5_response.text = expected_md5
            md5_response.raise_for_status = Mock()
            
            # Mock gzip response
            gzip_response = Mock()
            gzip_response.content = mock_gzip_data
            gzip_response.raise_for_status = Mock()
            
            session_instance.get.side_effect = [md5_response, gzip_response]
            session_instance.mount = Mock()  # For HTTPAdapter mounting
            session_instance.close = Mock()
            
            data_source = GithubDataSource()
            films = data_source.get_films()
        
        assert len(films) == 2
        assert films[0]['title'] == 'Test Movie'
        # Directors should be normalized to list of dicts
        assert films[0]['directors'] == [{'name': 'John Doe'}]
    
    def test_github_data_source_md5_verification_failure(self, mock_gzip_data):
        """Test that MD5 mismatch raises ValueError."""
        from plugin_video_mubi.resources.lib.data_source import GithubDataSource
        
        with patch('requests.Session') as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance
            
            # Mock MD5 response with wrong hash
            md5_response = Mock()
            md5_response.text = "wrong_md5_hash"
            md5_response.raise_for_status = Mock()
            
            # Mock gzip response
            gzip_response = Mock()
            gzip_response.content = mock_gzip_data
            gzip_response.raise_for_status = Mock()
            
            session_instance.get.side_effect = [md5_response, gzip_response]
            session_instance.mount = Mock()
            session_instance.close = Mock()
            
            data_source = GithubDataSource()
            
            with pytest.raises(ValueError, match="MD5 verification failed"):
                data_source.get_films()
    
    def test_github_data_source_network_error(self):
        """Test handling of network errors with proper exception propagation."""
        import requests
        from plugin_video_mubi.resources.lib.data_source import GithubDataSource
        
        with patch('requests.Session') as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance
            session_instance.mount = Mock()
            session_instance.close = Mock()
            session_instance.get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
            
            data_source = GithubDataSource()
            
            with pytest.raises(requests.exceptions.ConnectionError):
                data_source.get_films()
    
    def test_github_data_source_country_filtering(self, mock_gzip_data):
        """Test that country filtering correctly filters films."""
        import hashlib
        from plugin_video_mubi.resources.lib.data_source import GithubDataSource
        
        expected_md5 = hashlib.md5(mock_gzip_data).hexdigest()
        
        with patch('requests.Session') as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance
            
            md5_response = Mock()
            md5_response.text = expected_md5
            md5_response.raise_for_status = Mock()
            
            gzip_response = Mock()
            gzip_response.content = mock_gzip_data
            gzip_response.raise_for_status = Mock()
            
            session_instance.get.side_effect = [md5_response, gzip_response]
            session_instance.mount = Mock()
            session_instance.close = Mock()
            
            data_source = GithubDataSource()
            
            # Filter for GB - should only return film 1 (available in GB)
            films = data_source.get_films(countries=["GB"])
        
        assert len(films) == 1
        assert films[0]['title'] == 'Test Movie'
    
    def test_github_data_source_bad_gzip(self):
        """Test handling of corrupted gzip data."""
        import gzip
        import hashlib
        from plugin_video_mubi.resources.lib.data_source import GithubDataSource
        
        bad_data = b"this is not gzip data"
        expected_md5 = hashlib.md5(bad_data).hexdigest()
        
        with patch('requests.Session') as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance
            
            md5_response = Mock()
            md5_response.text = expected_md5
            md5_response.raise_for_status = Mock()
            
            gzip_response = Mock()
            gzip_response.content = bad_data
            gzip_response.raise_for_status = Mock()
            
            session_instance.get.side_effect = [md5_response, gzip_response]
            session_instance.mount = Mock()
            session_instance.close = Mock()
            
            data_source = GithubDataSource()
            
            with pytest.raises(gzip.BadGzipFile):
                data_source.get_films()
    
    def test_github_data_source_expired_film_filtered(self):
        """Test that expired films are filtered out when country filtering is applied."""
        import gzip
        import json
        import io
        import hashlib
        from plugin_video_mubi.resources.lib.data_source import GithubDataSource
        
        # Create data with one expired film
        data = {
            "meta": {"version": 1},
            "items": [
                {
                    "id": 1,
                    "title": "Available Movie",
                    "available_countries": {
                        "US": {"availability": "live", "expires_at": "2099-12-31T23:59:59Z"}
                    }
                },
                {
                    "id": 2,
                    "title": "Expired Movie",
                    "available_countries": {
                        "US": {"availability": "live", "expires_at": "2020-01-01T00:00:00Z"}
                    }
                }
            ]
        }
        
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
            gz.write(json.dumps(data).encode('utf-8'))
        gzip_data = buffer.getvalue()
        expected_md5 = hashlib.md5(gzip_data).hexdigest()
        
        with patch('requests.Session') as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance
            
            md5_response = Mock()
            md5_response.text = expected_md5
            md5_response.raise_for_status = Mock()
            
            gzip_response = Mock()
            gzip_response.content = gzip_data
            gzip_response.raise_for_status = Mock()
            
            session_instance.get.side_effect = [md5_response, gzip_response]
            session_instance.mount = Mock()
            session_instance.close = Mock()
            
            data_source = GithubDataSource()
            films = data_source.get_films(countries=["US"])
        
        # Only the non-expired film should be returned
        assert len(films) == 1
        assert films[0]['title'] == 'Available Movie'
