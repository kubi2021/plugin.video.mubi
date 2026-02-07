"""
Test configuration and fixtures for MUBI plugin tests following QA guidelines.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Happy path, edge cases, and error handling
"""

import sys
import pytest
from unittest.mock import MagicMock, Mock, patch
from pathlib import Path

# Add the repo directory to Python path so we can import from repo.plugin.video.mubi
repo_path = Path(__file__).parent.parent.parent / "repo"
sys.path.insert(0, str(repo_path))

# -----------------------------------------------------------------------------
# TEST CONSTANTS
# These constants are used across addon tests for consistency.
# -----------------------------------------------------------------------------
from tests.plugin_video_mubi.test_constants import MOCK_HANDLE, MOCK_BASE_URL



# -----------------------------------------------------------------------------
# GLOBAL MOCKS (Import-Time)
# Required for test collection because these modules are imported at top-level
# by the plugin code, but don't exist in the test environment.
# -----------------------------------------------------------------------------

# Mock requests globally by default for SPEED and SAFETY
# We will opt-out in integration tests.
requests_mock = MagicMock()
requests_mock.__file__ = None

# Create proper exception classes
class MockRequestException(Exception): pass
class MockConnectionError(MockRequestException): pass
class MockTimeout(MockRequestException): pass
class MockHTTPError(MockRequestException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.response = Mock()
        self.response.status_code = kwargs.get('status_code', 500)

requests_mock.exceptions = MagicMock()
requests_mock.exceptions.__file__ = None
requests_mock.exceptions.HTTPError = MockHTTPError
requests_mock.exceptions.RequestException = MockRequestException
requests_mock.exceptions.ConnectionError = MockConnectionError
requests_mock.exceptions.Timeout = MockTimeout


# Alias exceptions at top level too, matching requests API
requests_mock.RequestException = MockRequestException
requests_mock.ConnectionError = MockConnectionError
requests_mock.Timeout = MockTimeout
requests_mock.HTTPError = MockHTTPError

requests_mock.adapters = MagicMock()
requests_mock.adapters.__file__ = None
requests_mock.packages = MagicMock()
requests_mock.packages.__file__ = None
requests_mock.packages.urllib3 = MagicMock()
requests_mock.packages.urllib3.__file__ = None
requests_mock.packages.urllib3.util = MagicMock()
requests_mock.packages.urllib3.util.__file__ = None
requests_mock.packages.urllib3.util.retry = MagicMock()
requests_mock.packages.urllib3.util.retry.__file__ = None

# Apply to sys.modules immediately
sys.modules['requests'] = requests_mock
sys.modules['requests.exceptions'] = requests_mock.exceptions
sys.modules['requests.adapters'] = requests_mock.adapters
sys.modules['requests.packages'] = requests_mock.packages
sys.modules['requests.packages.urllib3'] = requests_mock.packages.urllib3
sys.modules['requests.packages.urllib3.util'] = requests_mock.packages.urllib3.util
sys.modules['requests.packages.urllib3.util.retry'] = requests_mock.packages.urllib3.util.retry

# Use REAL dateutil.parser for date parsing tests to work correctly
# Only mock the top-level module for import resolution
import dateutil
import dateutil.parser
sys.modules['dateutil'] = dateutil
sys.modules['dateutil.parser'] = dateutil.parser
sys.modules['webbrowser'] = MagicMock()
sys.modules['webbrowser'].__file__ = None
sys.modules['webbrowser'].__path__ = None
sys.modules['webbrowser'].__spec__ = None
# Removed sys.modules['time'] to avoid coverage/sqlite crash.
# Instead, we will patch time.sleep using a fixture to ensure tests remain fast.

@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """
    Globally mock time.sleep to avoid real waits during tests.
    This replaces the unsafe sys.modules['time'] = MagicMock().
    """
    return mocker.patch('time.sleep')

# Mock xbmc and related modules
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmc'].__file__ = None
sys.modules['xbmc'].__path__ = None
sys.modules['xbmc'].__spec__ = None
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcaddon'].__file__ = None
sys.modules['xbmcaddon'].__path__ = None
sys.modules['xbmcaddon'].__spec__ = None
sys.modules['xbmcaddon'].Addon.return_value.getAddonInfo.return_value = "/tmp/mock_addon_path"
sys.modules['xbmcaddon'].Addon.return_value.getSetting.return_value = ""
sys.modules['xbmcgui'] = MagicMock()
sys.modules['xbmcgui'].__file__ = None
sys.modules['xbmcgui'].__path__ = None
sys.modules['xbmcgui'].__spec__ = None
sys.modules['xbmcplugin'] = MagicMock()
sys.modules['xbmcplugin'].__file__ = None
sys.modules['xbmcplugin'].__path__ = None
sys.modules['xbmcplugin'].__spec__ = None

# Mock xbmcvfs
class MockFile:
    def __init__(self, path, mode):
        self.path = path
        self.mode = mode
        self.content = ""
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): return None
    def read(self): return self.content
    def write(self, content): self.content = content

xbmcvfs_mock = MagicMock()
xbmcvfs_mock.__file__ = None
xbmcvfs_mock.File = MockFile
xbmcvfs_mock.translatePath.return_value = "/tmp/mock_kodi"
xbmcvfs_mock.exists.return_value = True
xbmcvfs_mock.mkdirs.return_value = True
sys.modules['xbmcvfs'] = xbmcvfs_mock

# Mock inputstreamhelper
sys.modules['inputstreamhelper'] = MagicMock()
sys.modules['inputstreamhelper'].__file__ = None
sys.modules['inputstreamhelper'].__path__ = None
sys.modules['inputstreamhelper'].__spec__ = None

# Configure xbmc constants
xbmc_mock = sys.modules['xbmc']
xbmc_mock.LOGDEBUG = 0
xbmc_mock.LOGINFO = 1
xbmc_mock.LOGWARNING = 2
xbmc_mock.LOGERROR = 3
xbmc_mock.NOTIFICATION_INFO = 'info'
xbmc_mock.NOTIFICATION_WARNING = 'warning'
xbmc_mock.NOTIFICATION_ERROR = 'error'

# Configure xbmcplugin constants
xbmcplugin_mock = sys.modules['xbmcplugin']
xbmcplugin_mock.SORT_METHOD_NONE = 0


# -----------------------------------------------------------------------------
# REQUESTS MOCKS (Fixture-Based)
# Mocking requests safely during tests without polluting global state
# for integration tests that need real requests.
# -----------------------------------------------------------------------------

@pytest.fixture(scope="package", autouse=True)
def mock_requests_patching():
    """
    Forcefully RELOAD modules to ensure they pick up the mocked requests.
    Attribute patching is flaky with 'from X import Y'.
    """
    import sys
    import importlib
    
    # List of modules to reload
    # We must reload them if they are already in sys.modules
    target_modules = [
        'resources.lib.mubi',
        'resources.lib.data_source',
        'plugin_video_mubi.resources.lib.mubi',
        'plugin_video_mubi.resources.lib.data_source'
    ]
    
    reloaded_modules = []
    
    for tm in target_modules:
        if tm in sys.modules:
            try:
                # Reloading ensures that 'import requests' inside the module
                # picks up the MagicMock we installed in sys.modules['requests']
                # in the previous fixture.
                importlib.reload(sys.modules[tm])
                reloaded_modules.append(tm)
            except Exception as e:
                # If reload fails (e.g. partial initialization), just ignore
                print(f"Failed to reload {tm}: {e}")
            
    yield
    
    # Not strictly necessary to restore for unit tests, 
    # as we want them isolated. 
    # Integration tests will do their own environment setup/teardown.



@pytest.fixture
def mock_addon():
    """Fixture providing a mock addon instance."""
    addon = Mock()
    addon.getSetting.return_value = ""
    addon.setSetting.return_value = None
    addon.getSettingBool.return_value = False
    addon.setSettingBool.return_value = None
    addon.getAddonInfo.return_value = "/fake/path"
    return addon

@pytest.fixture
def mock_metadata():
    """Fixture providing a mock metadata instance."""
    metadata = Mock()
    metadata.title = "Test Movie"
    metadata.year = 2023
    metadata.director = ["Test Director"]
    metadata.genre = ["Drama"]
    metadata.plot = "Test plot"
    metadata.plotoutline = "Test outline"
    metadata.originaltitle = "Test Original Title"
    metadata.rating = 7.5
    metadata.votes = 1000
    metadata.duration = 120
    metadata.country = ["USA"]
    metadata.castandrole = ""
    metadata.dateadded = "2023-01-01"
    metadata.trailer = "http://example.com/trailer"
    metadata.image = "http://example.com/image.jpg"
    metadata.mpaa = {'US': "PG-13"}
    metadata.artwork_urls = {}
    metadata.audio_languages = ["English", "French"]
    metadata.subtitle_languages = ["English", "French", "Spanish"]
    metadata.media_features = ["HD", "stereo"]
    # New NFO fields
    metadata.premiered = "2023-01-15"
    metadata.content_warnings = ["violence", "language"]
    metadata.tagline = "A test movie tagline"
    metadata.audio_channels = ["5.1", "stereo"]
    return metadata

@pytest.fixture
def sample_film_data():
    """Fixture providing sample film data for testing.
    
    Uses far-future dates to ensure availability window is always valid.
    """
    return {
        'film': {
            'id': 12345,
            'title': 'Test Movie',
            'original_title': 'Test Original Movie',
            'year': 2023,
            'duration': 120,
            'short_synopsis': 'A test movie plot',
            'directors': [{'name': 'Test Director'}],
            'genres': ['Drama', 'Thriller'],
            'historic_countries': ['USA'],
            'average_rating': 7.5,
            'number_of_ratings': 1000,
            'still_url': 'http://example.com/still.jpg',
            'trailer_url': 'http://example.com/trailer.mp4',
            'web_url': 'http://mubi.com/films/test-movie',
            'consumable': {
                'available_at': '2020-01-01T00:00:00Z',
                'expires_at': '2099-12-31T23:59:59Z'  # Far future to ensure always available
            }
        }
    }

@pytest.fixture
def mock_film():
    """Fixture providing a mock Film instance."""
    from resources.lib.film import Film
    film = Mock(spec=Film)
    film.mubi_id = "12345"
    film.title = "Test Movie"
    film.artwork = "http://example.com/art.jpg"
    film.web_url = "http://example.com/movie"
    film.categories = ["Drama"]
    film.metadata = Mock()
    film.metadata.plot = "Test plot"
    film.metadata.year = 2023
    film.get_sanitized_folder_name.return_value = "Test Movie (2023)"
    return film

@pytest.fixture
def mock_library():
    """Fixture providing a mock Library instance."""
    from resources.lib.library import Library
    library = Mock(spec=Library)
    library.films = []
    library.__len__ = Mock(return_value=0)
    return library

@pytest.fixture(autouse=True)
def reset_modules():
    """Fixture to reset imported modules between tests."""
    import sys
    modules_to_remove = [
        'addon',
        'resources.lib.session_manager',
        'resources.lib.navigation_handler',
        'resources.lib.mubi',
        'resources.lib.migrations'
    ]

    for module in modules_to_remove:
        if module in sys.modules:
            del sys.modules[module]

    yield

    # Clean up after test
    for module in modules_to_remove:
        if module in sys.modules:
            del sys.modules[module]

@pytest.fixture
def temp_directory():
    """Fixture providing a temporary directory for testing."""
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def addon_test_mocks():
    """
    Shared fixture for addon.py tests with all common mocks.
    
    Consolidates the duplicate mocking patterns across TestAddon, TestErrorHandling,
    TestClientCountryAutoDetection, TestSyncLocally, TestSyncWorldwideOptimization,
    and TestMissingActions.
    
    Returns a dict with all mock instances for easy access in tests.
    """
    with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
         patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
         patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
         patch('xbmcaddon.Addon') as mock_addon, \
         patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
         patch('plugin_video_mubi.addon.add_mubi_source') as mock_add_source, \
         patch('plugin_video_mubi.addon.mark_first_run') as mock_mark_first_run, \
         patch('plugin_video_mubi.addon.migrate_genre_settings'), \
         patch('xbmc.log') as mock_log, \
         patch('xbmc.executebuiltin') as mock_executebuiltin, \
         patch('xbmcplugin.endOfDirectory') as mock_end_of_dir, \
         patch('xbmcplugin.setResolvedUrl') as mock_set_resolved, \
         patch('xbmcgui.Dialog') as mock_dialog, \
         patch('xbmcgui.ListItem') as mock_list_item:

        # Setup session instance
        mock_session_instance = Mock()
        mock_session_instance.client_country = 'CH'
        mock_session_instance.client_language = 'en'
        mock_session_manager.return_value = mock_session_instance

        # Setup mubi instance
        mock_mubi_instance = Mock()
        mock_mubi_instance.get_cli_country.return_value = 'US'
        mock_mubi_instance.get_cli_language.return_value = 'en'
        mock_mubi.return_value = mock_mubi_instance

        # Setup navigation instance
        mock_nav_instance = Mock()
        mock_nav_handler.return_value = mock_nav_instance

        # Setup addon instance
        mock_addon_instance = Mock()
        mock_addon_instance.getSetting.return_value = 'CH'
        mock_addon.return_value = mock_addon_instance

        # Setup dialog instance
        mock_dialog_instance = Mock()
        mock_dialog.return_value = mock_dialog_instance

        # Default: not first run
        mock_is_first_run.return_value = False

        yield {
            'session_manager': mock_session_manager,
            'session_instance': mock_session_instance,
            'navigation_handler': mock_nav_handler,
            'nav_instance': mock_nav_instance,
            'mubi': mock_mubi,
            'mubi_instance': mock_mubi_instance,
            'addon': mock_addon,
            'addon_instance': mock_addon_instance,
            'is_first_run': mock_is_first_run,
            'add_source': mock_add_source,
            'mark_first_run': mock_mark_first_run,
            'log': mock_log,
            'executebuiltin': mock_executebuiltin,
            'end_of_directory': mock_end_of_dir,
            'set_resolved_url': mock_set_resolved,
            'dialog': mock_dialog,
            'dialog_instance': mock_dialog_instance,
            'list_item': mock_list_item,
        }