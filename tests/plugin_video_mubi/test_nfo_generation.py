import pytest
import xml.etree.ElementTree as ET
from plugin_video_mubi.resources.lib.film import Film

class MockMetadata:
    def __init__(self, title="Test Film", originaltitle="Original Test Film", 
                 plot="Plot", plotoutline="Outline", rating=8.0, votes=100, 
                 duration=120, mpaa={'US': "PG"}, country=None, genre=None, director=None, 
                 year=2023, dateadded="2023-01-01", image="http://image.com"):
        self.title = title
        self.originaltitle = originaltitle
        self.plot = plot
        self.plotoutline = plotoutline
        self.rating = rating
        self.votes = votes
        self.duration = duration
        self.mpaa = mpaa
        self.country = country or ["US"]
        self.genre = genre or ["Drama"]
        self.director = director or ["Director"]
        self.year = year
        self.dateadded = dateadded
        self.image = image
        self.trailer = "http://trailer.com"

def test_nfo_contains_mubi_uniqueid_default():
    metadata = MockMetadata()
    film = Film(mubi_id="12345", title="Test", artwork="art", web_url="url", metadata=metadata)
    
    # Generate NFO tree
    # Arguments: metadata, kodi_trailer_url, imdb_id, tmdb_id, artwork_paths
    nfo_xml = film._get_nfo_tree(metadata, "plugin://trailer", "tt1234567", "98765", {})
    
    root = ET.fromstring(nfo_xml)
    
    # Check for Mubi uniqueid
    mubi_id_node = None
    imdb_id_node = None
    tmdb_id_node = None
    
    for uniqueid in root.findall("uniqueid"):
        uid_type = uniqueid.get("type")
        if uid_type == "mubi":
            mubi_id_node = uniqueid
        elif uid_type == "imdb":
            imdb_id_node = uniqueid
        elif uid_type == "tmdb":
            tmdb_id_node = uniqueid
            
    assert mubi_id_node is not None, "Mubi uniqueid node missing"
    assert mubi_id_node.text == "12345", "Mubi uniqueid value mismatch"
    assert mubi_id_node.get("default") == "true", "Mubi uniqueid should be default"
    
    if imdb_id_node is not None:
        assert imdb_id_node.get("default") != "true", "IMDb uniqueid should NOT be default"
        
    if tmdb_id_node is not None:
        assert tmdb_id_node.get("default") != "true", "TMDB uniqueid should NOT be default"

def test_nfo_mubi_id_only():
    metadata = MockMetadata()
    film = Film(mubi_id="12345", title="Test", artwork="art", web_url="url", metadata=metadata)
    
    # Generate NFO tree without external IDs
    nfo_xml = film._get_nfo_tree(metadata, "plugin://trailer", "", "", {})
    
    root = ET.fromstring(nfo_xml)
    
    mubi_id_node = None
    for uniqueid in root.findall("uniqueid"):
        if uniqueid.get("type") == "mubi":
            mubi_id_node = uniqueid
            
    assert mubi_id_node is not None
    assert mubi_id_node.text == "12345"
    assert mubi_id_node.get("default") == "true"
