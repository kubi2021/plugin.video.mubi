"""
Test suite for FilmFilter class.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Filtering logic based on addon settings
"""

from unittest.mock import Mock, patch
from plugin_video_mubi.resources.lib.filters import FilmFilter
import pytest

class TestFilmFilter:
    """Test cases for the FilmFilter class."""

    @patch('plugin_video_mubi.resources.lib.filters.xbmcaddon.Addon')
    def test_filter_films_by_genre(self, mock_addon_cls):
        """Test filtering films by genre based on addon settings."""
        # Arrange
        addon_mock = mock_addon_cls.return_value
        # Setup settings: skip_genre_horror is True, others False
        addon_mock.getSettingBool.side_effect = lambda key: key == 'skip_genre_horror'
        
        filter_instance = FilmFilter()

        # Create dummy film data (dictionaries, as expected by FilmFilter)
        # Film 1: Horror
        film_horror = {
            'id': 999,
            'title': 'Scary Movie',
            'genres': ['Horror', 'Thriller']
        }
        
        # Film 2: Drama
        film_drama = {
            'id': 1000,
            'title': 'Dramatic Movie',
            'genres': ['Drama']
        }
        
        # Film 3: Mixed (Horror + Drama) - should be skipped if ANY genre matches?
        # The logic in filter says: if any(genre.lower() in skip_genres for genre in genres)
        film_mixed = {
            'id': 1001,
            'title': 'Scary Drama',
            'genres': ['Drama', 'Horror']
        }

        # Input map can be a list or dict depending on what get_all_films passes
        # wait, FilmFilter expects a LIST of dicts in current implementation?
        # Let's check filter_films signature in filters.py:
        # def filter_films(self, films_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # It takes a LIST.
        
        raw_films_list = [film_horror, film_drama, film_mixed]

        # Act
        filtered_list = filter_instance.filter_films(raw_films_list)
        
        # Convert back to ids for easy assertion
        filtered_ids = [f['id'] for f in filtered_list]

        # Assert
        assert 1000 in filtered_ids, "Drama film should remain."
        assert 999 not in filtered_ids, "Horror film should be filtered out."
        assert 1001 not in filtered_ids, "Mixed film with Horror should be filtered out."
        assert len(filtered_list) == 1

    @patch('plugin_video_mubi.resources.lib.filters.xbmcaddon.Addon')
    def test_filter_films_no_settings(self, mock_addon_cls):
        """Test that no films are filtered when no settings are enabled."""
        # Arrange
        addon_mock = mock_addon_cls.return_value
        addon_mock.getSettingBool.return_value = False
        
        filter_instance = FilmFilter()

        film_horror = {'id': 999, 'genres': ['Horror']}
        film_drama = {'id': 1000, 'genres': ['Drama']}
        
        raw_films_list = [film_horror, film_drama]

        # Act
        filtered_list = filter_instance.filter_films(raw_films_list)

        # Assert
        assert len(filtered_list) == 2
        filtered_ids = [f['id'] for f in filtered_list]
        assert 999 in filtered_ids
        assert 1000 in filtered_ids

    @patch('plugin_video_mubi.resources.lib.filters.xbmcaddon.Addon')
    def test_filter_films_missing_genres(self, mock_addon_cls):
        """Test handling of films with missing genres."""
        # Arrange
        addon_mock = mock_addon_cls.return_value
        # Let's say we filter Horror
        addon_mock.getSettingBool.side_effect = lambda key: key == 'skip_genre_horror'
        
        filter_instance = FilmFilter()

        film_no_genre = {'id': 1, 'title': 'Mystery'} # No 'genres' key
        film_empty_genre = {'id': 2, 'genres': []}
        film_horror = {'id': 3, 'genres': ['Horror']}

        raw_films_list = [film_no_genre, film_empty_genre, film_horror]

        # Act
        filtered_list = filter_instance.filter_films(raw_films_list)
        filtered_ids = [f['id'] for f in filtered_list]

        # Assert
        assert 1 in filtered_ids, "Film with missing genres should be kept."
        assert 2 in filtered_ids, "Film with empty genres should be kept."
        assert 3 not in filtered_ids, "Horror film should be filtered."
