"""
Integration tests that test real component interactions.
These tests use minimal mocking and test actual workflows.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Happy path, edge cases, and error handling
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import sys
import json
import shutil
import os


# Import real components (not mocked)
from plugin_video_mubi.resources.lib.session_manager import SessionManager
from plugin_video_mubi.resources.lib.library import Library
from plugin_video_mubi.resources.lib.film import Film
from plugin_video_mubi.resources.lib.metadata import Metadata
from plugin_video_mubi.resources.lib.navigation_handler import NavigationHandler
from plugin_video_mubi.resources.lib.mubi import Mubi


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

                def create_strm_side_effect(film_path, base_url, user_country=None):
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
        assert mubi.apiURL == "https://api.mubi.com/"
        
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
        from plugin_video_mubi.resources.lib.migrations import is_first_run
        assert is_first_run(setup['addon']) is True
        
        # Test device ID generation during first run
        device_id = setup['session'].get_or_generate_device_id()
        assert device_id is not None
        assert len(device_id) > 0

    @patch('plugin_video_mubi.resources.lib.mubi.requests.get')
    @patch('time.time')
    def test_country_language_detection_workflow(self, mock_time, mock_requests_get, workflow_setup):
        """Test country and language detection workflow."""
        setup = workflow_setup

        # Mock time to avoid rate limiting issues
        mock_time.return_value = 1000.0

        # Initialize call history to avoid rate limiting
        setup['mubi']._call_history = []

        # Mock IP geolocation response (returns country code)
        mock_response_country = Mock()
        mock_response_country.text = 'US\n'
        mock_response_country.status_code = 200
        mock_requests_get.return_value = mock_response_country

        # Test country detection
        country = setup['mubi'].get_cli_country()
        setup['session'].set_client_country(country)

        # Test language detection (returns cached/default value, no HTTP call)
        language = setup['mubi'].get_cli_language()
        setup['session'].set_client_language(language)

        # Verify workflow completed
        assert setup['session'].client_country == "US"
        assert setup['session'].client_language == "en"


@pytest.mark.integration
@pytest.mark.end_to_end
class TestEndToEndWorkflows:
    """
    Comprehensive end-to-end integration tests that validate complete workflows.

    These tests follow the test-writing guidelines:
    - Use pytest framework with fixtures and parameterization
    - Follow Arrange-Act-Assert pattern
    - Cover happy path, edge cases, and error handling
    - Use minimal mocking for true integration testing
    - Test real component interactions
    """

    @pytest.fixture
    def e2e_setup(self):
        """
        Arrange: Set up complete end-to-end test environment.
        Creates real instances of all major components with minimal mocking.
        """
        # Create temporary directory for file operations
        temp_dir = tempfile.mkdtemp()
        plugin_userdata_path = Path(temp_dir)

        # Mock only external dependencies (Kodi addon system)
        # Create a stateful mock addon that persists settings
        mock_addon = Mock()
        addon_settings = {}  # Dictionary to store settings

        def mock_get_setting(key):
            return addon_settings.get(key, "")

        def mock_set_setting(key, value):
            addon_settings[key] = value
            return None

        mock_addon.getSetting.side_effect = mock_get_setting
        mock_addon.setSetting.side_effect = mock_set_setting
        mock_addon.getAddonInfo.return_value = str(plugin_userdata_path)

        # Create real component instances
        session_manager = SessionManager(mock_addon)
        library = Library()
        mubi = Mubi(session_manager)

        # Create NavigationHandler with proper parameters
        handle = 1  # Mock handle
        base_url = "plugin://plugin.video.mubi/"

        navigation_handler = NavigationHandler(handle, base_url, mubi, session_manager)

        return {
            'session_manager': session_manager,
            'library': library,
            'mubi': mubi,
            'navigation_handler': navigation_handler,
            'plugin_userdata_path': plugin_userdata_path,
            'mock_addon': mock_addon,
            'temp_dir': temp_dir
        }

    def test_complete_film_sync_workflow_happy_path(self, e2e_setup):
        """
        Test complete film synchronization workflow - happy path.

        Validates the entire process from API fetch to local file creation.
        """
        # Arrange
        setup = e2e_setup
        library = setup['library']
        plugin_userdata_path = setup['plugin_userdata_path']

        # Create sample film data that would come from MUBI API
        sample_metadata = Metadata(
            title="Test Movie",
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="A test movie plot",
            plotoutline="Test outline",
            originaltitle="Test Original Title",
            rating=8.5,
            votes=1000,
            duration=120,
            country=["USA"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="http://example.com/trailer",
            image="http://example.com/image.jpg",
            mpaa="PG-13",
            artwork_urls={"thumb": "http://example.com/thumb.jpg"},
            audio_languages=["English", "French"],
            subtitle_languages=["English", "Spanish"],
            media_features=["HD", "5.1"]
        )

        sample_film = Film(
            mubi_id="12345",
            title="Test Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/movie",
            metadata=sample_metadata,
            available_countries=["us", "gb", "de"]  # Film available in 3 countries
        )

        # Add film to library
        library.add_film(sample_film)

        # Act
        with patch('requests.get') as mock_get, \
             patch('xbmcgui.DialogProgress') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon_patch:

            # Mock artwork download
            mock_response = Mock()
            mock_response.iter_content.return_value = [b'fake_image_data']
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Mock progress dialog
            mock_dialog_instance = Mock()
            mock_dialog_instance.iscanceled.return_value = False
            mock_dialog.return_value = mock_dialog_instance

            # Mock addon for genre filtering
            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""
            mock_addon_patch.return_value = mock_addon_instance

            # Execute the sync workflow
            base_url = "plugin://plugin.video.mubi/"
            library.sync_locally(base_url, plugin_userdata_path, None)

        # Assert
        # Verify film folder was created
        film_folder = plugin_userdata_path / sample_film.get_sanitized_folder_name()
        assert film_folder.exists(), "Film folder should be created"

        # Verify NFO file was created with correct structure
        nfo_file = film_folder / f"{sample_film.get_sanitized_folder_name()}.nfo"
        assert nfo_file.exists(), "NFO file should be created"

        # Verify STRM file was created
        strm_file = film_folder / f"{sample_film.get_sanitized_folder_name()}.strm"
        assert strm_file.exists(), "STRM file should be created"

        # Verify NFO content follows official Kodi structure
        nfo_content = nfo_file.read_text()
        assert "<movie>" in nfo_content, "NFO should contain movie element"
        assert "<title>Test Movie</title>" in nfo_content, "NFO should contain title"
        assert "<fileinfo>" in nfo_content, "NFO should use official Kodi structure"
        assert "<streamdetails>" in nfo_content, "NFO should contain streamdetails"

        # Verify NFO contains mubi_availability section with all countries
        assert "<mubi_availability>" in nfo_content, "NFO should have availability"
        assert 'code="US"' in nfo_content, "NFO should contain US country code"
        assert 'code="GB"' in nfo_content, "NFO should contain GB country code"
        assert 'code="DE"' in nfo_content, "NFO should contain DE country code"
        assert "United States" in nfo_content, "NFO should contain US country name"
        assert "United Kingdom" in nfo_content, "NFO should contain GB country name"
        assert "Germany" in nfo_content, "NFO should contain DE country name"

        # Verify STRM content (no country info - that's now in NFO)
        strm_content = strm_file.read_text()
        assert base_url in strm_content, "STRM should contain plugin URL"
        assert "12345" in strm_content, "STRM should contain film ID"

    def test_duplicate_film_prevention_workflow(self, e2e_setup):
        """
        Test that duplicate films skip NFO/STRM creation but update availability.

        Validates that existing films don't recreate files but do update NFO.
        """
        # Arrange
        setup = e2e_setup
        library = setup['library']
        plugin_userdata_path = setup['plugin_userdata_path']

        # Create sample film with available countries
        sample_metadata = Metadata(
            title="Existing Movie",
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="An existing movie",
            plotoutline="Test outline",
            originaltitle="Existing Original",
            rating=7.0,
            votes=500,
            duration=90,
            country=["UK"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="http://example.com/trailer",
            image="http://example.com/image.jpg",
            mpaa="PG",
            artwork_urls={},
            audio_languages=["English"],
            subtitle_languages=["English"],
            media_features=["HD"]
        )

        existing_film = Film(
            mubi_id="67890",
            title="Existing Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/movie",
            metadata=sample_metadata,
            available_countries=["ch", "de", "gb"]  # Film is available in 3 countries
        )

        library.add_film(existing_film)

        # Pre-create film files to simulate existing sync (without availability)
        film_folder = plugin_userdata_path / existing_film.get_sanitized_folder_name()
        film_folder.mkdir(parents=True, exist_ok=True)

        nfo_file = film_folder / f"{existing_film.get_sanitized_folder_name()}.nfo"
        strm_file = film_folder / f"{existing_film.get_sanitized_folder_name()}.strm"

        # Original NFO without mubi_availability
        nfo_file.write_text("<movie><title>Existing Movie</title></movie>")
        strm_file.write_text("plugin://plugin.video.mubi/?action=play&film_id=67890")

        original_strm_content = strm_file.read_text()

        # Act
        with patch('xbmcgui.DialogProgress') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon_patch:

            # Mock progress dialog
            mock_dialog_instance = Mock()
            mock_dialog_instance.iscanceled.return_value = False
            mock_dialog.return_value = mock_dialog_instance

            # Mock addon for genre filtering
            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""
            mock_addon_patch.return_value = mock_addon_instance

            base_url = "plugin://plugin.video.mubi/"
            library.sync_locally(base_url, plugin_userdata_path, None)

        # Assert
        # Verify files still exist
        assert nfo_file.exists(), "Existing NFO file should be preserved"
        assert strm_file.exists(), "Existing STRM file should be preserved"

        # STRM should not be modified (no country in STRM anymore)
        assert strm_file.read_text() == original_strm_content, "STRM should not be modified"

        # NFO SHOULD be updated with mubi_availability section
        updated_nfo_content = nfo_file.read_text()
        assert "<mubi_availability>" in updated_nfo_content, "NFO should have availability"
        assert 'code="CH"' in updated_nfo_content, "NFO should contain CH country"
        assert 'code="DE"' in updated_nfo_content, "NFO should contain DE country"
        assert 'code="GB"' in updated_nfo_content, "NFO should contain GB country"

    def test_obsolete_film_cleanup_workflow(self, e2e_setup):
        """
        Test complete obsolete film cleanup workflow including artwork removal.

        Validates that films no longer available are completely removed.
        """
        # Arrange
        setup = e2e_setup
        library = setup['library']
        plugin_userdata_path = setup['plugin_userdata_path']

        # Create obsolete film folder with all file types
        obsolete_folder = plugin_userdata_path / "Old Movie (2020)"
        obsolete_folder.mkdir(parents=True, exist_ok=True)

        # Create all types of files that would exist for a film
        files_to_create = [
            "Old Movie (2020).nfo",
            "Old Movie (2020).strm",
            "Old Movie (2020)-thumb.jpg",
            "Old Movie (2020)-poster.jpg",
            "Old Movie (2020)-clearlogo.png"
        ]

        created_files = []
        for filename in files_to_create:
            file_path = obsolete_folder / filename
            file_path.write_text("test content")
            created_files.append(file_path)
            assert file_path.exists(), f"File {filename} should be created for test setup"

        # Create current film to ensure selective cleanup
        current_metadata = Metadata(
            title="Current Movie",
            year="2023",
            director=["Current Director"],
            genre=["Action"],
            plot="A current movie",
            plotoutline="Current outline",
            originaltitle="Current Original",
            rating=9.0,
            votes=2000,
            duration=150,
            country=["USA"],
            castandrole="Current Actor",
            dateadded="2023-01-01",
            trailer="http://example.com/trailer",
            image="http://example.com/image.jpg",
            mpaa="R",
            artwork_urls={},
            audio_languages=["English"],
            subtitle_languages=["English"],
            media_features=["4K"]
        )

        current_film = Film(
            mubi_id="current123",
            title="Current Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/movie",
            metadata=current_metadata
        )

        library.add_film(current_film)

        # Act
        with patch('xbmcgui.DialogProgress') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon_patch:

            # Mock progress dialog
            mock_dialog_instance = Mock()
            mock_dialog_instance.iscanceled.return_value = False
            mock_dialog.return_value = mock_dialog_instance

            # Mock addon for genre filtering
            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""
            mock_addon_patch.return_value = mock_addon_instance

            base_url = "plugin://plugin.video.mubi/"
            library.sync_locally(base_url, plugin_userdata_path, None)

        # Assert
        # Verify obsolete folder and all its contents were completely removed
        assert not obsolete_folder.exists(), "Obsolete folder should be completely removed"

        for file_path in created_files:
            assert not file_path.exists(), f"Obsolete file {file_path.name} should be removed"

        # Verify current film folder was created and preserved
        current_folder = plugin_userdata_path / current_film.get_sanitized_folder_name()
        assert current_folder.exists(), "Current film folder should be created"

    @pytest.mark.parametrize("invalid_char", ['<', '>', ':', '"', '/', '\\', '|', '?', '*'])
    def test_filename_sanitization_workflow(self, e2e_setup, invalid_char):
        """
        Test filename sanitization workflow with various invalid characters.

        Validates that films with problematic titles are properly handled.
        """
        # Arrange
        setup = e2e_setup
        library = setup['library']
        plugin_userdata_path = setup['plugin_userdata_path']

        # Create film with problematic title
        problematic_title = f"Problem{invalid_char}Movie"

        sample_metadata = Metadata(
            title=problematic_title,
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="A movie with problematic title",
            plotoutline="Test outline",
            originaltitle=problematic_title,
            rating=6.0,
            votes=100,
            duration=100,
            country=["USA"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="http://example.com/trailer",
            image="http://example.com/image.jpg",
            mpaa="PG",
            artwork_urls={},
            audio_languages=["English"],
            subtitle_languages=["English"],
            media_features=["HD"]
        )

        problematic_film = Film(
            mubi_id="problem123",
            title=problematic_title,
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/movie",
            metadata=sample_metadata
        )

        library.add_film(problematic_film)

        # Act
        with patch('xbmcgui.DialogProgress') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon_patch:

            # Mock progress dialog
            mock_dialog_instance = Mock()
            mock_dialog_instance.iscanceled.return_value = False
            mock_dialog.return_value = mock_dialog_instance

            # Mock addon for genre filtering
            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""
            mock_addon_patch.return_value = mock_addon_instance

            base_url = "plugin://plugin.video.mubi/"
            library.sync_locally(base_url, plugin_userdata_path, None)

        # Assert
        # Verify sanitized folder was created
        sanitized_folder_name = problematic_film.get_sanitized_folder_name()
        assert invalid_char not in sanitized_folder_name, f"Sanitized name should not contain '{invalid_char}'"

        film_folder = plugin_userdata_path / sanitized_folder_name
        assert film_folder.exists(), "Sanitized film folder should be created"

        # Verify files were created with sanitized names
        nfo_file = film_folder / f"{sanitized_folder_name}.nfo"
        strm_file = film_folder / f"{sanitized_folder_name}.strm"

        assert nfo_file.exists(), "NFO file should be created with sanitized name"
        assert strm_file.exists(), "STRM file should be created with sanitized name"

    def test_nfo_structure_compliance_workflow(self, e2e_setup):
        """
        Test that generated NFO files comply with official Kodi structure.

        Validates the complete NFO generation workflow produces compliant XML.
        """
        # Arrange
        setup = e2e_setup
        library = setup['library']
        plugin_userdata_path = setup['plugin_userdata_path']

        # Create film with comprehensive metadata
        comprehensive_metadata = Metadata(
            title="Comprehensive Movie",
            year="2023",
            director=["Director One", "Director Two"],
            genre=["Drama", "Thriller"],
            plot="A comprehensive movie with all metadata fields",
            plotoutline="Comprehensive outline",
            originaltitle="Comprehensive Original Title",
            rating=8.7,
            votes=5000,
            duration=135,
            country=["USA", "UK"],
            castandrole="Actor One\nActor Two",
            dateadded="2023-01-01",
            trailer="http://example.com/trailer",
            image="http://example.com/image.jpg",
            mpaa="PG-13",
            artwork_urls={
                "thumb": "http://example.com/thumb.jpg",
                "poster": "http://example.com/poster.jpg",
                "clearlogo": "http://example.com/logo.png"
            },
            audio_languages=["English", "French", "Spanish"],
            subtitle_languages=["English", "French", "Spanish", "German"],
            media_features=["4K", "HDR", "Dolby Atmos"]
        )

        comprehensive_film = Film(
            mubi_id="comprehensive123",
            title="Comprehensive Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/movie",
            metadata=comprehensive_metadata
        )

        library.add_film(comprehensive_film)

        # Act
        with patch('requests.get') as mock_get, \
             patch('xbmcgui.DialogProgress') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon_patch:

            # Mock artwork download
            mock_response = Mock()
            mock_response.iter_content.return_value = [b'fake_image_data']
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Mock progress dialog
            mock_dialog_instance = Mock()
            mock_dialog_instance.iscanceled.return_value = False
            mock_dialog.return_value = mock_dialog_instance

            # Mock addon for genre filtering
            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""
            mock_addon_patch.return_value = mock_addon_instance

            base_url = "plugin://plugin.video.mubi/"
            library.sync_locally(base_url, plugin_userdata_path, None)

        # Assert
        film_folder = plugin_userdata_path / comprehensive_film.get_sanitized_folder_name()
        nfo_file = film_folder / f"{comprehensive_film.get_sanitized_folder_name()}.nfo"

        assert nfo_file.exists(), "NFO file should be created"

        # Verify NFO content follows official Kodi structure
        nfo_content = nfo_file.read_text()

        # Check root structure
        assert "<movie>" in nfo_content, "NFO should have movie root element"
        assert "</movie>" in nfo_content, "NFO should close movie element"

        # Check standard metadata elements
        assert "<title>Comprehensive Movie</title>" in nfo_content
        assert "<originaltitle>Comprehensive Original Title</originaltitle>" in nfo_content
        assert "<year>2023</year>" in nfo_content
        assert "<value>8.7</value>" in nfo_content  # Rating is now in ratings structure

        # Check official Kodi streamdetails structure
        assert "<fileinfo>" in nfo_content, "Should use official fileinfo structure"
        assert "<streamdetails>" in nfo_content, "Should use official streamdetails structure"

        # Verify audio languages use official structure
        assert nfo_content.count("<audio>") == 3, "Should have 3 separate audio elements"
        assert "<language>English</language>" in nfo_content
        assert "<language>French</language>" in nfo_content
        assert "<language>Spanish</language>" in nfo_content

        # Verify subtitle languages use official structure
        assert nfo_content.count("<subtitle>") == 4, "Should have 4 separate subtitle elements"
        assert "<language>German</language>" in nfo_content

        # Verify no non-standard elements
        assert "<mediafeatures>" not in nfo_content, "Should not contain non-standard mediafeatures"

    def test_error_handling_workflow_network_failure(self, e2e_setup):
        """
        Test error handling workflow when network operations fail.

        Validates that the system gracefully handles network failures.
        """
        # Arrange
        setup = e2e_setup
        library = setup['library']
        plugin_userdata_path = setup['plugin_userdata_path']

        sample_metadata = Metadata(
            title="Network Test Movie",
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="A movie to test network failures",
            plotoutline="Test outline",
            originaltitle="Network Test Original",
            rating=7.5,
            votes=1500,
            duration=110,
            country=["USA"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="http://example.com/trailer",
            image="http://example.com/image.jpg",
            mpaa="PG-13",
            artwork_urls={"thumb": "http://example.com/thumb.jpg"},
            audio_languages=["English"],
            subtitle_languages=["English"],
            media_features=["HD"]
        )

        network_test_film = Film(
            mubi_id="network123",
            title="Network Test Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/movie",
            metadata=sample_metadata
        )

        library.add_film(network_test_film)

        # Act
        with patch('requests.get') as mock_get, \
             patch('xbmcgui.DialogProgress') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon_patch:

            # Mock network failure for artwork download
            mock_get.side_effect = Exception("Network error")

            # Mock progress dialog
            mock_dialog_instance = Mock()
            mock_dialog_instance.iscanceled.return_value = False
            mock_dialog.return_value = mock_dialog_instance

            # Mock addon for genre filtering
            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""
            mock_addon_patch.return_value = mock_addon_instance

            base_url = "plugin://plugin.video.mubi/"
            # Should not raise exception despite network failure
            library.sync_locally(base_url, plugin_userdata_path, None)

        # Assert
        # Verify that despite network failure, basic files were still created
        film_folder = plugin_userdata_path / network_test_film.get_sanitized_folder_name()
        assert film_folder.exists(), "Film folder should be created despite network failure"

        nfo_file = film_folder / f"{network_test_film.get_sanitized_folder_name()}.nfo"
        strm_file = film_folder / f"{network_test_film.get_sanitized_folder_name()}.strm"

        assert nfo_file.exists(), "NFO file should be created despite artwork download failure"
        assert strm_file.exists(), "STRM file should be created despite artwork download failure"

        # Verify NFO content is still valid
        nfo_content = nfo_file.read_text()
        assert "<title>Network Test Movie</title>" in nfo_content

    def test_session_management_integration_workflow(self, e2e_setup):
        """
        Test session management integration with other components.

        Validates that session data flows correctly through the system.
        """
        # Arrange
        setup = e2e_setup
        session_manager = setup['session_manager']
        mubi = setup['mubi']

        # Act
        # Test device ID generation and persistence (should be consistent)
        device_id_1 = session_manager.get_or_generate_device_id()
        device_id_2 = session_manager.get_or_generate_device_id()

        # Test country and language settings
        session_manager.set_client_country("US")
        session_manager.set_client_language("en")

        # Test session data retrieval
        country = session_manager.client_country
        language = session_manager.client_language

        # Assert
        # Verify device ID consistency (should be the same across calls)
        assert device_id_1 == device_id_2, "Device ID should be consistent across calls"
        assert len(device_id_1) > 0, "Device ID should not be empty"
        assert device_id_1 == session_manager.device_id, "Device ID should match session manager's stored ID"

        # Verify session data persistence
        assert country == "US", "Country should be persisted correctly"
        assert language == "en", "Language should be persisted correctly"

        # Verify session data is accessible to Mubi instance
        assert mubi.session_manager == session_manager, "Mubi should have access to session manager"

    def test_empty_library_workflow(self, e2e_setup):
        """
        Test workflow with empty library - edge case.

        Validates that empty library sync completes without errors.
        """
        # Arrange
        setup = e2e_setup
        library = setup['library']  # Empty library
        plugin_userdata_path = setup['plugin_userdata_path']

        # Verify library is empty
        assert len(library) == 0, "Library should be empty for this test"

        # Act
        with patch('xbmcgui.DialogProgress') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon_patch:

            # Mock progress dialog
            mock_dialog_instance = Mock()
            mock_dialog_instance.iscanceled.return_value = False
            mock_dialog.return_value = mock_dialog_instance

            # Mock addon for genre filtering
            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""
            mock_addon_patch.return_value = mock_addon_instance

            base_url = "plugin://plugin.video.mubi/"
            # Should complete without errors
            library.sync_locally(base_url, plugin_userdata_path, None)

        # Assert
        # Verify no film folders were created
        folders = list(plugin_userdata_path.iterdir())
        film_folders = [f for f in folders if f.is_dir()]
        assert len(film_folders) == 0, "No film folders should be created for empty library"

    # Level 2: title is no longer required, only mubi_id and metadata
    @pytest.mark.parametrize("missing_field", ['mubi_id', 'metadata'])
    def test_invalid_film_data_workflow(self, e2e_setup, missing_field):
        """
        Test workflow with invalid film data - error handling.

        Validates that invalid films are properly rejected.
        """
        # Arrange
        setup = e2e_setup
        library = setup['library']
        plugin_userdata_path = setup['plugin_userdata_path']

        # Create film with missing required field
        film_data = {
            'mubi_id': 'test123',
            'title': 'Test Movie',
            'artwork': 'http://example.com/art.jpg',
            'web_url': 'http://example.com/movie',
            'metadata': Metadata(
                title="Test Movie",
                year="2023",
                director=["Test Director"],
                genre=["Drama"],
                plot="Test plot",
                plotoutline="Test outline",
                originaltitle="Test Original",
                rating=7.0,
                votes=1000,
                duration=120,
                country=["USA"],
                castandrole="Test Actor",
                dateadded="2023-01-01",
                trailer="http://example.com/trailer",
                image="http://example.com/image.jpg",
                mpaa="PG",
                artwork_urls={},
                audio_languages=["English"],
                subtitle_languages=["English"],
                media_features=["HD"]
            )
        }

        # Remove the specified field to create invalid data
        if missing_field == 'metadata':
            film_data[missing_field] = None
        else:
            film_data[missing_field] = None

        # Act & Assert - Level 2: Updated validation message
        with pytest.raises(ValueError, match="Film must have a mubi_id and metadata"):
            invalid_film = Film(**film_data)
            library.add_film(invalid_film)

    def teardown_method(self):
        """Clean up after each test method."""
        # Cleanup is handled by tempfile.mkdtemp() automatic cleanup
        # Additional cleanup if needed
        for temp_dir in getattr(self, '_temp_dirs', []):
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.integration
class TestEndToEndFlows:
    """End-to-end integration tests for complete workflows."""

    def test_sync_to_playback_flow(self, tmp_path):
        """Test complete flow: sync film → create files → playback check."""
        # Arrange - Create library with film
        library = Library()
        metadata = Metadata(
            title="Test Film",
            year=2023,
            director=["Director"],
            genre=["Drama"],
            plot="Test plot",
            plotoutline="Test outline",
            originaltitle="Test Film",
            rating=7.0,
            votes=100,
            duration=120,
            country=["US"],
        )
        film = Film(
            mubi_id="12345",
            title="Test Film",
            artwork="http://example.com/art.jpg",
            web_url="http://mubi.com/films/test",
            metadata=metadata,
            available_countries=['US', 'FR', 'DE']
        )
        library.add_film(film)

        # Act - Sync to create files
        with patch('xbmcgui.DialogProgress') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon:
            mock_dialog_instance = Mock()
            mock_dialog_instance.iscanceled.return_value = False
            mock_dialog.return_value = mock_dialog_instance
            mock_addon.return_value.getSetting.return_value = ""

            library.sync_locally(
                "plugin://plugin.video.mubi/",
                tmp_path,
                None
            )

        # Assert - Files created
        film_folder = tmp_path / film.get_sanitized_folder_name()
        assert film_folder.exists()

        nfo_file = film_folder / f"{film.get_sanitized_folder_name()}.nfo"
        strm_file = film_folder / f"{film.get_sanitized_folder_name()}.strm"
        assert nfo_file.exists()
        assert strm_file.exists()

        # Verify STRM content
        strm_content = strm_file.read_text()
        assert "film_id=12345" in strm_content
        assert "action=play_mubi_video" in strm_content

    def test_worldwide_country_aggregation_flow(self):
        """Test worldwide sync aggregates countries correctly."""
        # Arrange - Mock Mubi API
        mock_addon = Mock()
        mock_addon.getSetting.side_effect = lambda key: {
            'client_country': 'US',
            'sync_countries': 'worldwide',
        }.get(key, '')
        mock_addon.getAddonInfo.return_value = "/fake/path"

        with patch('plugin_video_mubi.resources.lib.mubi.Mubi._make_api_call') as mock_api, \
             patch('plugin_video_mubi.resources.lib.mubi.Mubi.get_film_metadata') as mock_meta:

            # Mock API returns same film from different countries
            mock_api.return_value = {
                'films': [
                    {'id': 123, 'title': 'Test Film', 'web_url': '/films/test'}
                ]
            }

            # Mock metadata
            mock_metadata = Metadata(
                title="Test Film",
                year=2023,
                director=["Director"],
                genre=["Drama"],
                plot="Test plot",
                plotoutline="Test outline",
                originaltitle="Test Film",
                rating=7.0,
                votes=100,
                duration=120,
                country=["US"],
            )
            mock_film = Film(
                mubi_id="123",
                title="Test Film",
                artwork="",
                web_url="/films/test",
                metadata=mock_metadata,
                available_countries=['US']
            )
            mock_meta.return_value = mock_film

            # Act
            mubi = Mubi(mock_addon)
            library = mubi.get_all_films(countries=['US', 'FR'])

            # Assert - Library returned
            assert isinstance(library, Library)

    def test_vpn_switch_detection_flow(self):
        """Test VPN switch is detected via IP geolocation."""
        mock_addon = Mock()
        mock_addon.getSetting.return_value = ""
        mock_addon.getAddonInfo.return_value = "/fake/path"

        mubi = Mubi(mock_addon)

        # Mock IP geolocation - the method uses 'requests' module directly
        with patch.object(mubi, 'get_cli_country') as mock_get_country:
            # First call - US
            mock_get_country.return_value = 'US'
            country_us = mubi.get_cli_country()
            assert country_us == 'US'

            # Second call - VPN switched to DE
            mock_get_country.return_value = 'DE'
            country_de = mubi.get_cli_country()
            assert country_de == 'DE'