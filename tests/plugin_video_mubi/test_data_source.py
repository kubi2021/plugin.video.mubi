"""
Test suite for MubiApiDataSource class.

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
