import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from plugin_video_mubi.resources.lib.film import Film
from plugin_video_mubi.resources.lib.library import Library

class MockMetadata:
    def __init__(self):
        self.year = 2023
        self.title = "Test Movie"
        # minimal attributes needed for Film init
        pass

class TestAvailability(unittest.TestCase):

    def setUp(self):
        self.metadata = MockMetadata()
        self.now = datetime.now(timezone.utc)
        self.now_iso = self.now.isoformat().replace('+00:00', 'Z')
        
        self.future = (self.now + timedelta(days=365)).isoformat().replace('+00:00', 'Z')
        self.past = (self.now - timedelta(days=365)).isoformat().replace('+00:00', 'Z')
        self.far_future = (self.now + timedelta(days=730)).isoformat().replace('+00:00', 'Z')

    def create_film(self, countries_data):
        return Film(
            mubi_id="123",
            title="Test Film",
            artwork="",
            web_url="",
            metadata=self.metadata,
            available_countries=countries_data
        )

    def test_playable_live_content(self):
        """Test content that is currently available."""
        # Available since last year, expires next year
        countries = {
            'US': {
                'available_at': self.past,
                'availability_ends_at': self.future,
                'availability': 'live' # String status should be ignored, but providing for completeness
            }
        }
        film = self.create_film(countries)
        self.assertTrue(film.is_playable())

    def test_not_playable_upcoming_content(self):
        """Test content that is available in the future (upcoming)."""
        countries = {
            'US': {
                'available_at': self.future,
                'availability_ends_at': self.far_future,
                'availability': 'upcoming'
            }
        }
        film = self.create_film(countries)
        self.assertFalse(film.is_playable())

    def test_not_playable_expired_content(self):
        """Test content that has expired."""
        countries = {
            'US': {
                'available_at': (self.now - timedelta(days=730)).isoformat().replace('+00:00', 'Z'),
                'availability_ends_at': self.past,
                'availability': 'live' # Even if it says live, date rules
            }
        }
        film = self.create_film(countries)
        self.assertFalse(film.is_playable())

    def test_playable_mixed_countries(self):
        """Test film available in one country but upcoming/expired in others."""
        countries = {
            'US': { # Upcoming
                'available_at': self.future,
                'availability_ends_at': self.far_future
            },
            'GB': { # Live
                'available_at': self.past,
                'availability_ends_at': self.future
            },
            'FR': { # Expired
                'available_at': self.past, 
                'availability_ends_at': self.past
            }
        }
        film = self.create_film(countries)
        self.assertTrue(film.is_playable())

    def test_playable_no_end_date(self):
        """Test content with start date but no end date (indefinite)."""
        countries = {
            'US': {
                'available_at': self.past,
                'availability_ends_at': None
            }
        }
        film = self.create_film(countries)
        self.assertTrue(film.is_playable())

    def test_not_playable_missing_start_date(self):
        """Test content missing available_at (should default to not playable)."""
        countries = {
            'US': {
                'availability_ends_at': self.future
            }
        }
        film = self.create_film(countries)
        self.assertFalse(film.is_playable())

    def test_library_validation_integration(self):
        """Verify Library.is_film_valid uses logic correctly."""
        library = Library()
        
        # Valid film
        valid_film = self.create_film({'US': {'available_at': self.past, 'availability_ends_at': self.future}})
        self.assertTrue(library.is_film_valid(valid_film))
        
        # Invalid film
        invalid_film = self.create_film({'US': {'available_at': self.future, 'availability_ends_at': self.far_future}})
        self.assertFalse(library.is_film_valid(invalid_film))
