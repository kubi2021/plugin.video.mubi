import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock
from plugin_video_mubi.resources.lib.film import Film
from plugin_video_mubi.resources.lib.metadata import Metadata

class MockMetadata(Metadata):
    def __init__(self, title="Test Film", rating=8.0, votes=100, bayesian_rating=None, bayesian_votes=None):
        super().__init__(
            title=title,
            director=[], year=2023, duration=100, country=["US"],
            plot="Plot", plotoutline="Outline", genre=["Drama"], originaltitle=title,
            rating=rating, votes=votes,
            bayesian_rating=bayesian_rating, bayesian_votes=bayesian_votes,
            image="http://img.com/1.jpg"
        )

def test_nfo_uses_bayesian_rating_when_present():
    """Verify NFO uses 'bayesian' rating when available in metadata."""
    metadata = MockMetadata(rating=5.0, votes=10, bayesian_rating=7.5, bayesian_votes=1000)
    film = Film(mubi_id="123", title="Test", artwork="art", web_url="url", metadata=metadata)
    
    nfo_xml = film._get_nfo_tree(metadata, "url", "", "")
    root = ET.fromstring(nfo_xml)
    
    ratings_node = root.find("ratings")
    assert ratings_node is not None
    
    rating_node = ratings_node.find("rating")
    assert rating_node is not None
    assert rating_node.get("name") == "bayesian"
    assert rating_node.find("value").text == "7.5"
    assert rating_node.find("votes").text == "1000"
    
    # Ensure standard Mubi rating is suppressed
    names = [r.get("name") for r in ratings_node.findall("rating")]
    assert "MUBI" not in names

def test_nfo_uses_mubi_rating_fallback():
    """Verify NFO uses 'MUBI' rating when bayesian rating is missing."""
    metadata = MockMetadata(rating=5.0, votes=10, bayesian_rating=None)
    film = Film(mubi_id="123", title="Test", artwork="art", web_url="url", metadata=metadata)
    
    nfo_xml = film._get_nfo_tree(metadata, "url", "", "")
    root = ET.fromstring(nfo_xml)
    
    ratings_node = root.find("ratings")
    rating_node = ratings_node.find("rating")
    
    assert rating_node.get("name") == "MUBI"
    assert rating_node.find("value").text == "5.0"
    assert rating_node.find("votes").text == "10"


    
def test_is_rating_synced_with_tmp_path(tmp_path):
    """Real file test for sync logic."""
    # Case 1: Synced (Bayesian)
    metadata = MockMetadata(rating=5.0, bayesian_rating=7.5)
    film = Film(mubi_id="123", title="Test", artwork="art", web_url="url", metadata=metadata)
    
    nfo_file = tmp_path / "test.nfo"
    nfo_xml = film._get_nfo_tree(metadata, "url", "", "")
    nfo_file.write_bytes(nfo_xml)
    
    assert film.is_rating_synced(nfo_file) is True
    
    # Case 2: Mismatch (Metadata has new rating)
    metadata.bayesian_rating = 8.0 # Changed
    assert film.is_rating_synced(nfo_file) is False
    
    # Case 3: Switch from Mubi to Bayesian
    # NFO has Mubi 5.0
    metadata_old = MockMetadata(rating=5.0, bayesian_rating=None)
    film_old = Film(mubi_id="123", title="Test", artwork="art", web_url="url", metadata=metadata_old)
    nfo_xml_old = film_old._get_nfo_tree(metadata_old, "url", "", "")
    nfo_file.write_bytes(nfo_xml_old)
    
    # Metadata has Bayesian 7.5
    metadata_new = MockMetadata(rating=5.0, bayesian_rating=7.5)
    film_new = Film(mubi_id="123", title="Test", artwork="art", web_url="url", metadata=metadata_new)
    
    assert film_new.is_rating_synced(nfo_file) is False
