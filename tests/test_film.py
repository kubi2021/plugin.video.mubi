import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import xml.etree.ElementTree as ET
from resources.lib.film import Film
from resources.lib.metadata import Metadata


class TestFilm:
    """Test cases for the Film class."""

    def test_film_initialization_valid(self, mock_metadata):
        """Test successful film initialization with valid data."""
        film = Film(
            mubi_id="12345",
            title="Test Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/movie",
            category="Drama",
            metadata=mock_metadata
        )
        
        assert film.mubi_id == "12345"
        assert film.title == "Test Movie"
        assert film.artwork == "http://example.com/art.jpg"
        assert film.web_url == "http://example.com/movie"
        assert film.categories == ["Drama"]
        assert film.metadata == mock_metadata

    def test_film_initialization_missing_required_fields(self):
        """Test film initialization fails with missing required fields."""
        with pytest.raises(ValueError, match="Film must have a mubi_id, title, and metadata"):
            Film(mubi_id="", title="Test", artwork="", web_url="", category="", metadata=None)
        
        with pytest.raises(ValueError, match="Film must have a mubi_id, title, and metadata"):
            Film(mubi_id="123", title="", artwork="", web_url="", category="", metadata=Mock())
        
        with pytest.raises(ValueError, match="Film must have a mubi_id, title, and metadata"):
            Film(mubi_id="123", title="Test", artwork="", web_url="", category="", metadata=None)

    def test_film_equality(self, mock_metadata):
        """Test film equality based on mubi_id."""
        film1 = Film("123", "Movie 1", "", "", "Drama", mock_metadata)
        film2 = Film("123", "Movie 2", "", "", "Comedy", mock_metadata)  # Different title, same ID
        film3 = Film("456", "Movie 1", "", "", "Drama", mock_metadata)  # Same title, different ID
        
        assert film1 == film2  # Same mubi_id
        assert film1 != film3  # Different mubi_id
        assert film1 != "not a film"  # Different type

    def test_film_hash(self, mock_metadata):
        """Test film hash is based on mubi_id."""
        film1 = Film("123", "Movie 1", "", "", "Drama", mock_metadata)
        film2 = Film("123", "Movie 2", "", "", "Comedy", mock_metadata)
        
        assert hash(film1) == hash(film2)
        
        # Test films can be used in sets
        film_set = {film1, film2}
        assert len(film_set) == 1  # Should only contain one film due to same mubi_id

    def test_add_category(self, mock_metadata):
        """Test adding categories to a film."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)
        
        # Add new category
        film.add_category("Comedy")
        assert "Comedy" in film.categories
        assert len(film.categories) == 2
        
        # Try to add duplicate category
        film.add_category("Drama")
        assert film.categories.count("Drama") == 1  # Should not duplicate
        
        # Try to add empty category
        film.add_category("")
        assert "" not in film.categories

    def test_get_sanitized_folder_name(self, mock_metadata):
        """Test folder name sanitization."""
        # Test with special characters
        film = Film("123", "Test/Movie: Special*Characters?", "", "", "Drama", mock_metadata)
        mock_metadata.year = 2023
        
        sanitized = film.get_sanitized_folder_name()
        assert "/" not in sanitized
        assert ":" not in sanitized
        assert "*" not in sanitized
        assert "?" not in sanitized
        assert "2023" in sanitized
        
        # Test with normal title
        film2 = Film("456", "Normal Movie", "", "", "Drama", mock_metadata)
        sanitized2 = film2.get_sanitized_folder_name()
        assert sanitized2 == "Normal Movie (2023)"

    @patch('resources.lib.film.requests.get')
    def test_get_imdb_url_success(self, mock_get, mock_metadata):
        """Test successful IMDB URL retrieval."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Response': 'True',
            'imdbID': 'tt1234567'
        }
        mock_get.return_value = mock_response
        
        imdb_url = film._get_imdb_url("Test Movie", "Test Movie", 2023, "fake_api_key")
        assert imdb_url == "https://www.imdb.com/title/tt1234567/"
        
        # Verify API was called with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "fake_api_key" in call_args[1]['params']['apikey']

    @patch('resources.lib.film.requests.get')
    def test_get_imdb_url_not_found(self, mock_get, mock_metadata):
        """Test IMDB URL retrieval when movie not found."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)
        
        # Mock API response with no results
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'Response': 'False'}
        mock_get.return_value = mock_response
        
        imdb_url = film._get_imdb_url("Test Movie", "Test Movie", 2023, "fake_api_key")
        assert imdb_url == ""

    @patch('resources.lib.film.requests.get')
    def test_get_imdb_url_api_error(self, mock_get, mock_metadata):
        """Test IMDB URL retrieval with API error."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)

        # Import the mock exception class
        from requests.exceptions import RequestException

        # Mock API error with the correct exception type
        mock_get.side_effect = RequestException("API Error")

        imdb_url = film._get_imdb_url("Test Movie", "Test Movie", 2023, "fake_api_key")
        assert imdb_url == ""

    def test_get_nfo_tree(self, mock_metadata):
        """Test NFO XML tree generation."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)
        
        nfo_tree = film._get_nfo_tree(
            mock_metadata, 
            ["Drama"], 
            "http://example.com/trailer", 
            "http://imdb.com/title/tt123"
        )
        
        # Parse the XML to verify structure
        root = ET.fromstring(nfo_tree)
        assert root.tag == "movie"
        
        # Check required elements exist
        assert root.find("title").text == "Test Movie"
        assert root.find("year").text == "2023"
        assert root.find("plot").text == "Test plot"
        
        # Check genre
        genre_elem = root.find("genre")
        assert genre_elem is not None
        assert "Drama" in genre_elem.text

    def test_create_strm_file(self, mock_metadata):
        """Test STRM file creation."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            film_path = Path(tmpdir)
            base_url = "plugin://plugin.video.mubi/"
            
            film.create_strm_file(film_path, base_url)
            
            strm_file = film_path / f"{film.get_sanitized_folder_name()}.strm"
            assert strm_file.exists()
            
            # Check content
            content = strm_file.read_text()
            assert base_url in content
            assert film.mubi_id in content

    @patch('resources.lib.film.time.sleep')
    @patch.object(Film, '_get_imdb_url')
    def test_create_nfo_file_success(self, mock_get_imdb, mock_sleep, mock_metadata):
        """Test successful NFO file creation."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)
        mock_get_imdb.return_value = "http://imdb.com/title/tt123"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            film_path = Path(tmpdir)
            base_url = "plugin://plugin.video.mubi/"
            
            film.create_nfo_file(film_path, base_url, "fake_api_key")
            
            nfo_file = film_path / f"{film.get_sanitized_folder_name()}.nfo"
            assert nfo_file.exists()
            
            # Verify it's valid XML
            content = nfo_file.read_text()
            root = ET.fromstring(content)
            assert root.tag == "movie"

    @patch.object(Film, '_get_imdb_url')
    def test_create_nfo_file_no_api_key(self, mock_get_imdb, mock_metadata):
        """Test NFO file creation without API key."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            film_path = Path(tmpdir)
            base_url = "plugin://plugin.video.mubi/"
            
            film.create_nfo_file(film_path, base_url, None)
            
            nfo_file = film_path / f"{film.get_sanitized_folder_name()}.nfo"
            assert nfo_file.exists()
            
            # Should not have called IMDB API
            mock_get_imdb.assert_not_called()

    @patch.object(Film, '_get_imdb_url')
    def test_create_nfo_file_imdb_error(self, mock_get_imdb, mock_metadata):
        """Test NFO file creation when IMDB lookup fails."""
        film = Film("123", "Test Movie", "", "", "Drama", mock_metadata)
        mock_get_imdb.return_value = None  # Simulate API error
        
        with tempfile.TemporaryDirectory() as tmpdir:
            film_path = Path(tmpdir)
            base_url = "plugin://plugin.video.mubi/"
            
            # Should not create NFO file when IMDB lookup fails
            film.create_nfo_file(film_path, base_url, "fake_api_key")
            
            nfo_file = film_path / f"{film.get_sanitized_folder_name()}.nfo"
            assert not nfo_file.exists()
