"""
Integration tests that test real component interactions.
These tests use minimal mocking and test actual workflows.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import sys
import json


# Import real components (not mocked)
from resources.lib.session_manager import SessionManager
from resources.lib.library import Library
from resources.lib.film import Film
from resources.lib.metadata import Metadata
from resources.lib.navigation_handler import NavigationHandler
from resources.lib.mubi import Mubi


@pytest.mark.integration
class TestRealComponentIntegration:
    """Test real component interactions with minimal mocking."""

    @pytest.fixture
    def real_session_manager(self):
        """Create a real SessionManager with mocked addon."""
        mock_addon = Mock()
        mock_addon.getSetting.return_value = ""
        mock_addon.setSetting.return_value = None
        mock_addon.getAddonInfo.return_value = "/fake/path"
        return SessionManager(mock_addon)

    @pytest.fixture
    def real_film_library(self):
        """Create a real Library instance."""
        return Library()

    @pytest.fixture
    def sample_film_metadata(self):
        """Create real Metadata instance."""
        return Metadata(
            title="Integration Test Movie",
            director=["Test Director"],
            year=2023,
            duration=120,
            country=["USA"],
            plot="A test movie for integration testing",
            plotoutline="Short plot outline",
            genre=["Drama"],
            originaltitle="Integration Test Movie",
            rating=7.5,
            votes=1000
        )

    @pytest.fixture
    def sample_film(self, sample_film_metadata):
        """Create a real Film instance."""
        return Film(
            mubi_id="integration_123",
            title="Integration Test Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/movie",
            category="Drama",
            metadata=sample_film_metadata
        )

    def test_session_manager_device_id_persistence(self, real_session_manager):
        """Test that device ID is generated and persisted correctly."""
        # Mock the plugin to return consistent values
        real_session_manager.plugin.getSetting.return_value = ""  # No existing device ID

        # First call should generate a device ID
        device_id_1 = real_session_manager.get_or_generate_device_id()
        assert device_id_1 is not None
        assert len(device_id_1) > 0

        # Mock the plugin to return the generated device ID
        real_session_manager.plugin.getSetting.return_value = device_id_1

        # Second call should return the same device ID
        device_id_2 = real_session_manager.get_or_generate_device_id()
        assert device_id_1 == device_id_2

    def test_library_add_and_retrieve(self, real_film_library, sample_film):
        """Test adding films to library and retrieving them."""
        # Initially empty
        assert len(real_film_library) == 0
        assert real_film_library.films == []

        # Add a film
        real_film_library.add_film(sample_film)
        assert len(real_film_library) == 1
        assert sample_film in real_film_library.films

        # Add duplicate (should not increase count)
        real_film_library.add_film(sample_film)
        assert len(real_film_library) == 1

    def test_film_metadata_to_dict_conversion(self, sample_film_metadata):
        """Test that metadata can be converted to dict correctly."""
        metadata_dict = sample_film_metadata.as_dict()
        
        assert isinstance(metadata_dict, dict)
        assert metadata_dict['title'] == "Integration Test Movie"
        assert metadata_dict['year'] == 2023
        assert metadata_dict['director'] == ["Test Director"]
        assert metadata_dict['genre'] == ["Drama"]

    def test_film_nfo_generation_with_real_metadata(self, sample_film):
        """Test NFO generation with real metadata using private method."""
        # Test the private _get_nfo_tree method directly
        nfo_tree = sample_film._get_nfo_tree(
            metadata=sample_film.metadata,
            categories=sample_film.categories,
            kodi_trailer_url="http://test.com/trailer",
            imdb_url="http://imdb.com/title/tt1234567"
        )

        assert nfo_tree is not None
        assert isinstance(nfo_tree, bytes)

        # Parse the XML to verify structure
        import xml.etree.ElementTree as ET
        root = ET.fromstring(nfo_tree)

        assert root.tag == "movie"

        # Check for required elements
        title_elem = root.find("title")
        assert title_elem is not None
        assert title_elem.text == "Integration Test Movie"

        year_elem = root.find("year")
        assert year_elem is not None
        assert year_elem.text == "2023"



    @patch('requests.get')
    def test_film_imdb_integration(self, mock_get, sample_film):
        """Test IMDB URL retrieval with realistic API response using private method."""
        # Mock a realistic OMDB API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'Title': 'Integration Test Movie',
            'Year': '2023',
            'imdbID': 'tt1234567',
            'Type': 'movie',
            'Response': 'True'
        }
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Test the private _get_imdb_url method directly
        imdb_url = sample_film._get_imdb_url(
            original_title="Integration Test Movie",
            english_title="Integration Test Movie",
            year="2023",
            omdb_api_key="real_api_key"
        )

        assert imdb_url == "https://www.imdb.com/title/tt1234567/"

        # Verify the API was called with correct parameters
        mock_get.assert_called()
        call_args = mock_get.call_args
        assert call_args[1]['params']['apikey'] == "real_api_key"
        assert call_args[1]['params']['t'] == "Integration Test Movie"

    def test_library_file_operations_integration(self, real_film_library, sample_film):
        """Test library file operations with real filesystem."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_userdata_path = Path(temp_dir)
            
            # Add film to library
            real_film_library.add_film(sample_film)
            
            # Mock the file creation methods to actually create files
            with patch.object(sample_film, 'create_nfo_file') as mock_nfo, \
                 patch.object(sample_film, 'create_strm_file') as mock_strm:
                
                def create_nfo_side_effect(film_path, base_url, api_key):
                    film_path.mkdir(parents=True, exist_ok=True)
                    nfo_file = film_path / f"{sample_film.get_sanitized_folder_name()}.nfo"
                    nfo_file.touch()
                
                def create_strm_side_effect(film_path, base_url):
                    strm_file = film_path / f"{sample_film.get_sanitized_folder_name()}.strm"
                    strm_file.touch()
                
                mock_nfo.side_effect = create_nfo_side_effect
                mock_strm.side_effect = create_strm_side_effect
                
                # Test file preparation
                result = real_film_library.prepare_files_for_film(
                    sample_film, 
                    "plugin://test/", 
                    plugin_userdata_path, 
                    "test_api_key"
                )
                
                assert result is True
                
                # Verify files were created in correct structure
                expected_folder = plugin_userdata_path / sample_film.get_sanitized_folder_name()
                assert expected_folder.exists()

                expected_nfo = expected_folder / f"{sample_film.get_sanitized_folder_name()}.nfo"
                expected_strm = expected_folder / f"{sample_film.get_sanitized_folder_name()}.strm"
                assert expected_nfo.exists()
                assert expected_strm.exists()

    def test_obsolete_file_removal_integration(self, real_film_library, sample_film):
        """Test obsolete file removal with real filesystem."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_userdata_path = Path(temp_dir)

            # Create some obsolete folders directly in plugin_userdata_path
            obsolete1 = plugin_userdata_path / "Old Movie (2020)"
            obsolete2 = plugin_userdata_path / "Another Old Movie (2021)"
            obsolete1.mkdir()
            obsolete2.mkdir()

            # Add current film to library
            real_film_library.add_film(sample_film)

            # Create current film folder directly in plugin_userdata_path
            current_folder = plugin_userdata_path / sample_film.get_sanitized_folder_name()
            current_folder.mkdir()

            # Remove obsolete files
            removed_count = real_film_library.remove_obsolete_files(plugin_userdata_path)
            
            # Verify obsolete folders were removed
            assert not obsolete1.exists()
            assert not obsolete2.exists()
            assert current_folder.exists()  # Current film should remain
            assert removed_count == 2

    @patch('xbmc.log')
    def test_session_manager_logging_integration(self, mock_log, real_session_manager):
        """Test that session manager properly logs operations."""
        # Trigger some operations that should log
        real_session_manager.get_or_generate_device_id()
        real_session_manager.set_logged_in("test_token", "test_user")
        real_session_manager.set_logged_out()
        
        # Verify logging occurred (at least some calls)
        assert mock_log.call_count >= 2

    def test_mubi_initialization_with_real_session(self, real_session_manager):
        """Test Mubi initialization with real SessionManager."""
        mubi = Mubi(real_session_manager)
        
        assert mubi.session_manager == real_session_manager
        assert isinstance(mubi.library, Library)
        assert mubi.apiURL == "https://api.mubi.com/v3/"
        
        # Test that libraries are properly initialized
        assert len(mubi.library) == 0
        assert mubi.library.films == []


@pytest.mark.integration
class TestWorkflowIntegration:
    """Test complete user workflows with minimal mocking."""
    
    @pytest.fixture
    def workflow_setup(self):
        """Setup for workflow testing."""
        mock_addon = Mock()
        mock_addon.getSetting.return_value = ""
        mock_addon.setSetting.return_value = None
        mock_addon.getAddonInfo.return_value = "/fake/path"
        
        session = SessionManager(mock_addon)
        mubi = Mubi(session)
        
        return {
            'addon': mock_addon,
            'session': session,
            'mubi': mubi
        }

    def test_first_run_workflow(self, workflow_setup):
        """Test the complete first-run workflow."""
        setup = workflow_setup
        
        # Simulate first run
        setup['addon'].getSettingBool.return_value = False  # first_run_completed = false

        # Test first run detection
        from resources.lib.migrations import is_first_run
        assert is_first_run(setup['addon']) is True
        
        # Test device ID generation during first run
        device_id = setup['session'].get_or_generate_device_id()
        assert device_id is not None
        assert len(device_id) > 0

    @patch('requests.Session')
    @patch('time.time')
    def test_country_language_detection_workflow(self, mock_time, mock_session_class, workflow_setup):
        """Test country and language detection workflow."""
        setup = workflow_setup

        # Mock time to avoid rate limiting issues
        mock_time.return_value = 1000.0

        # Initialize call history to avoid rate limiting
        setup['mubi']._call_history = []

        # Mock the session instance and its request method
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock API responses with proper response objects
        mock_response_country = Mock()
        mock_response_country.text = '"Client-Country":"US"'
        mock_response_country.status_code = 200

        mock_response_language = Mock()
        mock_response_language.text = '"Client-Language":"en"'
        mock_response_language.status_code = 200

        # Create a side effect function that returns the appropriate mock response
        def mock_request_side_effect(*args, **kwargs):
            url = args[1] if len(args) > 1 else kwargs.get('url', '')
            if 'mubi.com' in str(url):
                return mock_response_country
            else:
                return mock_response_language

        mock_session.request.side_effect = mock_request_side_effect

        # Test country detection
        country = setup['mubi'].get_cli_country()
        setup['session'].set_client_country(country)

        # Test language detection
        language = setup['mubi'].get_cli_language()
        setup['session'].set_client_language(language)

        # Verify workflow completed
        assert setup['session'].client_country == "US"
        assert setup['session'].client_language == "en"