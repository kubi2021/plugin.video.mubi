import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from plugin_video_mubi.resources.lib.film import Film
from plugin_video_mubi.resources.lib.library import Library
from plugin_video_mubi.resources.lib.availability import is_country_available

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

    def test_not_playable_missing_start_date_with_future_end(self):
        """End date in the future but no start date and no 'live' status: not playable.

        Availability on the dates requires a start date in the past; a missing
        available_at means 'not started yet'. Without a start date and without a
        'live' status to fall back on, the film must not be playable. (A film that
        IS marked 'live' with a future end and no start stays playable via the
        status fallback — see test_live_status_with_future_end_no_start.)
        """
        countries = {
            'US': {
                'availability_ends_at': self.future
            }
        }
        film = self.create_film(countries)
        self.assertFalse(film.is_playable())

    def test_live_status_with_future_end_no_start(self):
        """A 'live' film with a future end but no start date stays playable.

        The strict start-date rule applies to the date logic only; an explicit
        'live' status is still honoured as a fallback when there is no usable
        start date and the film has not expired.
        """
        film = self.create_film({'US': {'availability_ends_at': self.future,
                                         'availability': 'live'}})
        self.assertTrue(film.is_playable())

    def test_not_playable_expired_even_when_live_without_start(self):
        """A past end date means expired even with 'live' status and no start."""
        film = self.create_film({'US': {'availability_ends_at': self.past,
                                        'availability': 'live'}})
        self.assertFalse(film.is_playable())

    def test_not_playable_no_dates_and_not_live(self):
        """No dates at all falls back to the availability status string."""
        self.assertFalse(self.create_film({'US': {'availability': 'upcoming'}}).is_playable())
        self.assertFalse(self.create_film({'US': {}}).is_playable())

    def test_playable_no_dates_but_live(self):
        """No dates but availability == 'live' is playable (status fallback)."""
        film = self.create_film({'US': {'availability': 'live'}})
        self.assertTrue(film.is_playable())

    def test_library_validation_integration(self):
        """Verify Library.is_film_valid uses logic correctly."""
        library = Library()

        # Valid film
        valid_film = self.create_film({'US': {'available_at': self.past, 'availability_ends_at': self.future}})
        self.assertTrue(library.is_film_valid(valid_film))

        # Invalid film
        invalid_film = self.create_film({'US': {'available_at': self.future, 'availability_ends_at': self.far_future}})
        self.assertFalse(library.is_film_valid(invalid_film))


class TestAvailabilityTimestampParsing(unittest.TestCase):
    """Issue #52: timestamps must be compared as parsed aware datetimes, not as
    ISO strings, and the availability paths must agree on the same inputs."""

    def setUp(self):
        self.metadata = MockMetadata()

    def make_film(self, details):
        return Film(
            mubi_id="123", title="T", artwork="", web_url="",
            metadata=self.metadata, available_countries={'US': details},
        )

    def test_offset_timestamp_in_past_is_playable_where_string_compare_fails(self):
        """A +02:00 available_at that is already in the past reads as playable.

        This is the exact bug from issue #52. We pin fixed instants so the test
        is deterministic and prove that the previous lexical string comparison
        would have wrongly skipped this film.
        """
        now = datetime(2026, 6, 1, 6, 53, 51, tzinfo=timezone.utc)
        # Same instant as 05:53:51Z (one hour ago), written with a +02:00 offset.
        available_at = "2026-06-01T07:53:51+02:00"
        now_iso = now.isoformat().replace('+00:00', 'Z')  # '2026-06-01T06:53:51Z'

        # The old code did `now_iso < available_at` as strings. Prove it mis-orders:
        self.assertTrue(now_iso < available_at,
                        "Precondition: lexical string compare wrongly says not-yet-available")

        # The fixed instant-based comparison gets it right.
        self.assertTrue(is_country_available({'available_at': available_at}, now))

    def test_offset_timestamp_expired_is_not_playable(self):
        """A +02:00 expires_at already in the past reads as expired."""
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        details = {
            'available_at': "2026-05-01T00:00:00Z",
            'expires_at': "2026-06-01T13:00:00+02:00",  # == 11:00Z, one hour ago
        }
        self.assertFalse(is_country_available(details, now))

    def test_z_and_plus_zero_are_equivalent(self):
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        z = is_country_available({'available_at': "2026-06-01T11:00:00Z"}, now)
        plus_zero = is_country_available({'available_at': "2026-06-01T11:00:00+00:00"}, now)
        self.assertTrue(z)
        self.assertEqual(z, plus_zero)

    def test_differing_subsecond_precision(self):
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        # available_at 1 microsecond in the future -> not yet available.
        self.assertFalse(is_country_available(
            {'available_at': "2026-06-01T12:00:00.000001Z"}, now))
        # available_at with coarse precision, safely in the past -> available.
        self.assertTrue(is_country_available(
            {'available_at': "2026-06-01T11:59:59Z"}, now))

    def test_naive_timestamp_assumed_utc(self):
        """A timestamp with no offset is treated as UTC (mirrors data_source)."""
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(is_country_available({'available_at': "2026-06-01T11:00:00"}, now))
        self.assertFalse(is_country_available({'available_at': "2026-06-01T13:00:00"}, now))

    def test_expires_at_alias_respected_by_film(self):
        """Film.is_playable must honour `expires_at`, not only `availability_ends_at`.

        Before issue #52, film.py only read `availability_ends_at`, so an
        expired film described with `expires_at` (the field data_source and
        navigation_handler use) leaked through as playable.
        """
        now = datetime.now(timezone.utc)
        past = (now - timedelta(days=1)).isoformat().replace('+00:00', 'Z')
        older = (now - timedelta(days=2)).isoformat().replace('+00:00', 'Z')
        film = self.make_film({'available_at': older, 'expires_at': past})
        self.assertFalse(film.is_playable())

    def test_unparseable_timestamp_falls_back_to_status(self):
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(is_country_available(
            {'available_at': "not-a-date", 'availability': 'live'}, now))
        self.assertFalse(is_country_available(
            {'available_at': "not-a-date", 'availability': 'upcoming'}, now))

    def test_agreement_across_paths_on_offset_input(self):
        """film.is_playable and navigation_handler._is_country_available agree."""
        from plugin_video_mubi.resources.lib.navigation_handler import NavigationHandler
        now = datetime(2026, 6, 1, 6, 53, 51, tzinfo=timezone.utc)
        details = {'available_at': "2026-06-01T07:53:51+02:00"}  # past, playable

        nav = NavigationHandler.__new__(NavigationHandler)  # no Kodi setup needed
        with patch('plugin_video_mubi.resources.lib.availability.datetime') as mock_dt:
            mock_dt.now.return_value = now
            self.assertTrue(nav._is_country_available(details))
            self.assertTrue(self.make_film(details).is_playable())
