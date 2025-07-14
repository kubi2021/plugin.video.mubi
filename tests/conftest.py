import sys
import pytest
from unittest.mock import MagicMock, Mock
from pathlib import Path

# Mock external dependencies before any imports
requests_mock = MagicMock()

# Create proper exception classes that inherit from BaseException
class MockHTTPError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.response = Mock()
        self.response.status_code = kwargs.get('status_code', 500)

class MockRequestException(Exception):
    pass

class MockConnectionError(MockRequestException):
    pass

class MockTimeout(MockRequestException):
    pass

# Set up the exceptions module
requests_mock.exceptions = MagicMock()
requests_mock.exceptions.HTTPError = MockHTTPError
requests_mock.exceptions.RequestException = MockRequestException
requests_mock.exceptions.ConnectionError = MockConnectionError
requests_mock.exceptions.Timeout = MockTimeout

requests_mock.adapters = MagicMock()
requests_mock.packages = MagicMock()
requests_mock.packages.urllib3 = MagicMock()
requests_mock.packages.urllib3.util = MagicMock()
requests_mock.packages.urllib3.util.retry = MagicMock()

sys.modules['requests'] = requests_mock
sys.modules['requests.exceptions'] = requests_mock.exceptions
sys.modules['requests.adapters'] = requests_mock.adapters
sys.modules['requests.packages'] = requests_mock.packages
sys.modules['requests.packages.urllib3'] = requests_mock.packages.urllib3
sys.modules['requests.packages.urllib3.util'] = requests_mock.packages.urllib3.util
sys.modules['requests.packages.urllib3.util.retry'] = requests_mock.packages.urllib3.util.retry

sys.modules['dateutil'] = MagicMock()
sys.modules['dateutil.parser'] = MagicMock()
sys.modules['webbrowser'] = MagicMock()
sys.modules['time'] = MagicMock()

# Mock xbmc and other related modules before any imports
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock()
sys.modules['xbmcplugin'] = MagicMock()

# Create a proper mock for xbmcvfs.File that supports context manager
class MockFile:
    def __init__(self, path, mode):
        self.path = path
        self.mode = mode
        self.content = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def read(self):
        return self.content

    def write(self, content):
        self.content = content

xbmcvfs_mock = MagicMock()
xbmcvfs_mock.File = MockFile
sys.modules['xbmcvfs'] = xbmcvfs_mock

sys.modules['inputstreamhelper'] = MagicMock()

# Configure xbmc module constants
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
    return metadata

@pytest.fixture
def sample_film_data():
    """Fixture providing sample film data for testing."""
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
                'available_at': '2023-01-01T00:00:00Z',
                'expires_at': '2023-12-31T23:59:59Z'
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
    from resources.lib.film_library import Film_Library
    library = Mock(spec=Film_Library)
    library.films = []
    library.__len__ = Mock(return_value=0)
    return library

@pytest.fixture
def real_film_library():
    """Fixture providing a REAL Film_Library instance for integration tests."""
    from resources.lib.film_library import Film_Library
    return Film_Library()

@pytest.fixture
def real_session_manager():
    """Fixture providing a REAL SessionManager for integration tests."""
    from resources.lib.session_manager import SessionManager
    mock_addon = Mock()
    mock_addon.getSetting.return_value = ""
    mock_addon.setSetting.return_value = None
    mock_addon.getAddonInfo.return_value = "/fake/path"
    return SessionManager(mock_addon)

@pytest.fixture
def isolated_test_environment():
    """Fixture that ensures complete test isolation."""
    import sys
    import tempfile

    # Store original state
    original_modules = sys.modules.copy()

    # Create isolated temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        yield {
            'temp_dir': temp_dir,
            'original_modules': original_modules
        }

    # Restore original state
    # Remove any modules that were imported during test
    modules_to_remove = []
    for module_name in sys.modules:
        if module_name not in original_modules:
            modules_to_remove.append(module_name)

    for module_name in modules_to_remove:
        if module_name in sys.modules:
            del sys.modules[module_name]

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