
import pytest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET
from plugin_video_mubi.resources.lib.library import Library
from plugin_video_mubi.resources.lib.film import Film
from plugin_video_mubi.resources.lib.metadata import Metadata

class TestMultiCountrySync:
    """
    Test suite for verifying that films available in multiple countries 
    are correctly processed and NFO files contain all availability info.
    """

    @pytest.fixture
    def mock_metadata(self):
        """Create a mock Metadata object."""
        metadata = Mock(spec=Metadata)
        metadata.title = "Test Movie"
        metadata.director = ["Director Name"]
        metadata.year = 2023
        metadata.duration = 120
        metadata.country = ["Country"]
        metadata.plot = "Test plot"
        metadata.plotoutline = "Test outline"
        metadata.genre = ["Drama"]
        metadata.rating = 8.0
        metadata.votes = 100
        metadata.image = "http://example.com/image.jpg"
        metadata.mpaa = {'US': "PG"}
        metadata.originaltitle = "Original Title"
        metadata.tagline = "This is a tagline"
        metadata.dateadded = "2025-12-19"
        metadata.audio_languages = []
        metadata.subtitle_languages = []
        return metadata

    def test_legacy_sync_multiple_countries_merge(self, mock_metadata):
        """
        Test the 'Legacy Sync' scenario where the scraper iterates through countries
        and adds the same film multiple times with different country data.
        The Library should merge these entries.
        """
        library = Library()
        mubi_id = "12345"
        
        # 1. Simulate finding film in Antarctica (AQ)
        film_aq = Film(
            mubi_id=mubi_id,
            title="The Wonders",
            artwork="",
            web_url="",
            metadata=mock_metadata,
            available_countries={
                "AQ": {"availability": "live", "available_at": "2025-01-01"}
            }
        )
        library.add_film(film_aq)
        
        assert len(library) == 1
        assert "AQ" in library.films[mubi_id].available_countries
        
        # 2. Simulate finding the SAME film in Italy (IT)
        film_it = Film(
            mubi_id=mubi_id,
            title="The Wonders",
            artwork="",
            web_url="",
            metadata=mock_metadata,
            available_countries={
                "IT": {"availability": "live", "available_at": "2025-01-02"}
            }
        )
        library.add_film(film_it)
        
        # Assertions
        assert len(library) == 1 # Should still be 1 film
        merged_film = library.films[mubi_id]
        
        # Verify both countries are present
        assert len(merged_film.available_countries) == 2
        assert "AQ" in merged_film.available_countries
        assert "IT" in merged_film.available_countries
        
        # Verify details preserved
        assert merged_film.available_countries["AQ"]["available_at"] == "2025-01-01"
        assert merged_film.available_countries["IT"]["available_at"] == "2025-01-02"

    def test_github_sync_pre_merged_data(self, mock_metadata):
        """
        Test the 'GitHub Sync' scenario where we load a JSON that already 
        has multiple countries populated in available_countries.
        """
        library = Library()
        mubi_id = "67890"
        
        # Simulate data loaded from films.json
        available_countries_data = {
            "US": {"availability": "live"},
            "FR": {"availability": "live"},
            "DE": {"availability": "upcoming"}
        }
        
        film = Film(
            mubi_id=mubi_id,
            title="Pre-Merged Movie",
            artwork="",
            web_url="",
            metadata=mock_metadata,
            available_countries=available_countries_data
        )
        library.add_film(film)
        
        assert len(library) == 1
        stored_film = library.films[mubi_id]
        
        assert len(stored_film.available_countries) == 3
        assert {"US", "FR", "DE"} == set(stored_film.available_countries.keys())

    def test_nfo_generation_has_all_countries(self, mock_metadata):
        """
        Test that the generated NFO XML actually contains all the country tags.
        """
        # Setup film with multiple countries
        film = Film(
            mubi_id="11111",
            title="Global Movie",
            artwork="",
            web_url="",
            metadata=mock_metadata,
            available_countries={
                "US": {"availability": "live"},
                "GB": {"availability": "live"},
                "JP": {"availability": "upcoming"}
            }
        )
        
        # Generate NFO tree
        nfo_tree = film._get_nfo_tree(
            mock_metadata,
            kodi_trailer_url="",
            imdb_id="",
            artwork_paths=None
        )
        
        # Parse XML
        root = ET.fromstring(nfo_tree)
        mubi_availability = root.find("mubi_availability")
        
        assert mubi_availability is not None
        
        # Find all country children
        country_elements = mubi_availability.findall("country")
        assert len(country_elements) == 3
        
        # Extract codes
        codes = {c.get("code") for c in country_elements}
        assert codes == {"US", "GB", "JP"}
