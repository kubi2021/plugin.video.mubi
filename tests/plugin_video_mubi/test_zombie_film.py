import unittest
from unittest.mock import MagicMock, patch
import sys
from unittest.mock import MagicMock

# Mock Kodi modules
sys.modules["xbmc"] = MagicMock()
sys.modules["xbmcgui"] = MagicMock()
sys.modules["xbmcaddon"] = MagicMock()

from plugin_video_mubi.resources.lib.library import Library
from plugin_video_mubi.resources.lib.film import Film

class TestZombieFilm(unittest.TestCase):
    def test_film_without_availability_should_be_invalid(self):
        # Create a film with empty available_countries
        metadata = MagicMock()
        film = Film(
            mubi_id="97363",
            title="No",
            artwork="",
            web_url="",
            metadata=metadata,
            available_countries={}
        )
        
        library = Library()
        is_valid = library.is_film_valid(film)
        
        # We want it to be False, and now it should be
        print(f"Film valid? {bool(is_valid)}")
        self.assertFalse(bool(is_valid))
        
if __name__ == '__main__':
    unittest.main()
