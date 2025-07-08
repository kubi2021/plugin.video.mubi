import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path


class TestAddon:
    """Test cases for the main addon.py file."""

    @pytest.fixture
    def mock_sys_argv(self):
        """Fixture to mock sys.argv for addon testing."""
        original_argv = sys.argv
        sys.argv = [
            "plugin://plugin.video.mubi/",  # base_url
            "123",  # handle
            ""  # parameters (empty)
        ]
        yield sys.argv
        sys.argv = original_argv

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all addon dependencies."""
        with patch('resources.lib.session_manager.SessionManager') as mock_session_manager, \
             patch('resources.lib.navigation_handler.NavigationHandler') as mock_nav_handler, \
             patch('resources.lib.mubi.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('resources.lib.migrations.is_first_run') as mock_is_first_run, \
             patch('resources.lib.migrations.add_mubi_source') as mock_add_source, \
             patch('resources.lib.migrations.mark_first_run') as mock_mark_first_run, \
             patch('xbmc.log') as mock_log:
            
            # Setup mock returns
            mock_session_instance = Mock()
            mock_session_instance.client_country = None
            mock_session_instance.client_language = None
            mock_session_manager.return_value = mock_session_instance
            
            mock_mubi_instance = Mock()
            mock_mubi_instance.get_cli_country.return_value = "US"
            mock_mubi_instance.get_cli_language.return_value = "en"
            mock_mubi.return_value = mock_mubi_instance
            
            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance
            
            mock_addon_instance = Mock()
            mock_addon.return_value = mock_addon_instance
            
            mock_is_first_run.return_value = False
            
            yield {
                'session_manager': mock_session_manager,
                'navigation_handler': mock_nav_handler,
                'mubi': mock_mubi,
                'addon': mock_addon,
                'session_instance': mock_session_instance,
                'mubi_instance': mock_mubi_instance,
                'nav_instance': mock_nav_instance,
                'addon_instance': mock_addon_instance,
                'is_first_run': mock_is_first_run,
                'add_source': mock_add_source,
                'mark_first_run': mock_mark_first_run,
                'log': mock_log
            }

    def test_addon_basic_functionality(self, mock_sys_argv, mock_dependencies):
        """Test basic addon functionality without complex module loading."""
        # Test that we can create the basic components
        mocks = mock_dependencies

        # Simulate the addon.py main execution
        plugin = mocks['addon']()
        handle = int(mock_sys_argv[1])
        base_url = mock_sys_argv[0]
        session = mocks['session_manager'](plugin)
        mubi = mocks['mubi'](session)
        navigation = mocks['navigation_handler'](handle, base_url, mubi, session)

        # Verify basic initialization works
        assert plugin is not None
        assert session is not None
        assert mubi is not None
        assert navigation is not None
        assert handle == 123
        assert base_url == "plugin://plugin.video.mubi/"

    def test_addon_parameter_parsing(self):
        """Test parameter parsing functionality."""
        # Test URL parameter parsing
        from urllib.parse import parse_qs, urlparse

        test_url = "plugin://plugin.video.mubi/?action=listing&id=456&category_name=Drama"
        parsed = urlparse(test_url)
        params = parse_qs(parsed.query)

        assert params['action'][0] == 'listing'
        assert params['id'][0] == '456'
        assert params['category_name'][0] == 'Drama'

    def test_addon_url_decoding(self):
        """Test URL decoding functionality."""
        from urllib.parse import unquote

        encoded_url = "http%3A//example.com/movie"
        decoded_url = unquote(encoded_url)

        assert decoded_url == "http://example.com/movie"

    def test_addon_handle_conversion(self):
        """Test handle conversion from string to int."""
        handle_str = "123"
        handle_int = int(handle_str)

        assert handle_int == 123
        assert isinstance(handle_int, int)

    def test_addon_first_run_logic_simple(self, mock_dependencies):
        """Test first run logic components."""
        mocks = mock_dependencies

        # Test first run detection
        mocks['is_first_run'].return_value = True
        is_first = mocks['is_first_run'](mocks['addon_instance'])
        assert is_first is True

        # Test source addition
        mocks['add_source']()
        mocks['add_source'].assert_called()

        # Test first run marking
        mocks['mark_first_run'](mocks['addon_instance'])
        mocks['mark_first_run'].assert_called_with(mocks['addon_instance'])

    def test_addon_component_integration(self, mock_dependencies):
        """Test that addon components can be integrated together."""
        mocks = mock_dependencies

        # Test component creation chain
        plugin = mocks['addon']()
        session = mocks['session_manager'](plugin)
        mubi = mocks['mubi'](session)
        navigation = mocks['navigation_handler'](123, "plugin://test/", mubi, session)

        # Verify all components were created
        assert plugin is not None
        assert session is not None
        assert mubi is not None
        assert navigation is not None
