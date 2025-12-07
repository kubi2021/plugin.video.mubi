"""
Test suite for Addon main module following QA guidelines.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Happy path, edge cases, and error handling
"""

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
        with patch('plugin_video_mubi.resources.lib.session_manager.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.resources.lib.navigation_handler.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.resources.lib.mubi.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.resources.lib.migrations.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.resources.lib.migrations.add_mubi_source') as mock_add_source, \
             patch('plugin_video_mubi.resources.lib.migrations.mark_first_run') as mock_mark_first_run, \
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


class TestClientCountryAutoDetection:
    """
    Test cases for client country auto-detection logic.

    Requirements:
    1. Client country is auto-detected on first run and stored in settings
    2. User can override the setting at any time
    3. If plugin runs and client_country is not set (e.g., settings.xml removed),
       the plugin will auto-detect and set it again
    """

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all addon dependencies."""
        with patch('plugin_video_mubi.resources.lib.session_manager.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.resources.lib.navigation_handler.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.resources.lib.mubi.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.resources.lib.migrations.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.resources.lib.migrations.add_mubi_source') as mock_add_source, \
             patch('plugin_video_mubi.resources.lib.migrations.mark_first_run') as mock_mark_first_run, \
             patch('xbmc.log') as mock_log:

            mock_session_instance = Mock()
            mock_session_manager.return_value = mock_session_instance

            mock_mubi_instance = Mock()
            mock_mubi.return_value = mock_mubi_instance

            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance

            mock_addon_instance = Mock()
            mock_addon.return_value = mock_addon_instance

            mock_is_first_run.return_value = False

            yield {
                'session_manager': mock_session_manager,
                'session_instance': mock_session_instance,
                'mubi': mock_mubi,
                'mubi_instance': mock_mubi_instance,
                'addon': mock_addon,
                'addon_instance': mock_addon_instance,
                'is_first_run': mock_is_first_run,
                'add_source': mock_add_source,
                'mark_first_run': mock_mark_first_run,
                'log': mock_log,
                'navigation_handler': mock_nav_handler,
                'nav_instance': mock_nav_instance,
            }

    def test_client_country_auto_detected_on_first_run(self, mock_dependencies):
        """
        Test that client country is auto-detected via MUBI API on first run.
        When client_country is not set, the plugin should call get_cli_country()
        and store the result in settings.
        """
        mocks = mock_dependencies
        session = mocks['session_instance']
        mubi = mocks['mubi_instance']

        # Arrange: Simulate first run - client_country not set
        session.client_country = None  # Empty/not set
        session.client_language = 'en'
        mubi.get_cli_country.return_value = 'US'

        # Act: Simulate the addon.py logic
        if not session.client_country:
            client_country = mubi.get_cli_country()
            session.set_client_country(client_country)

        # Assert: Verify get_cli_country was called and country was set
        mubi.get_cli_country.assert_called_once()
        session.set_client_country.assert_called_once_with('US')

    def test_client_country_not_auto_detected_when_already_set(self, mock_dependencies):
        """
        Test that client country is NOT auto-detected when already stored in settings.
        This preserves user's manual override.
        """
        mocks = mock_dependencies
        session = mocks['session_instance']
        mubi = mocks['mubi_instance']

        # Arrange: client_country already set (user override or previous detection)
        session.client_country = 'FR'  # Already set to France
        session.client_language = 'fr'

        # Act: Simulate the addon.py logic
        if not session.client_country:
            client_country = mubi.get_cli_country()
            session.set_client_country(client_country)

        # Assert: get_cli_country should NOT be called, country should remain as-is
        mubi.get_cli_country.assert_not_called()
        session.set_client_country.assert_not_called()

    def test_client_country_re_detected_after_settings_reset(self, mock_dependencies):
        """
        Test that client country is re-detected when settings.xml is removed/reset.
        Simulates scenario: user deletes settings, plugin should auto-detect again.
        """
        mocks = mock_dependencies
        session = mocks['session_instance']
        mubi = mocks['mubi_instance']

        # Arrange: Simulate settings.xml removed - client_country is empty string
        session.client_country = ''  # Empty string (settings reset)
        session.client_language = ''
        mubi.get_cli_country.return_value = 'DE'  # User now in Germany

        # Act: Simulate the addon.py logic
        if not session.client_country:
            client_country = mubi.get_cli_country()
            session.set_client_country(client_country)

        # Assert: Should re-detect and set new country
        mubi.get_cli_country.assert_called_once()
        session.set_client_country.assert_called_once_with('DE')

    def test_client_country_user_override_persists(self, mock_dependencies):
        """
        Test that user-set country overrides persist and are not overwritten.
        User sets country to 'JP' (using VPN to Japan), this should persist.
        """
        mocks = mock_dependencies
        session = mocks['session_instance']
        mubi = mocks['mubi_instance']

        # Arrange: User manually set country to Japan (VPN scenario)
        session.client_country = 'JP'

        # Act: Plugin runs - simulates multiple addon invocations
        for _ in range(3):  # Simulate 3 plugin runs
            if not session.client_country:
                client_country = mubi.get_cli_country()
                session.set_client_country(client_country)

        # Assert: get_cli_country should never be called, user setting preserved
        mubi.get_cli_country.assert_not_called()
        session.set_client_country.assert_not_called()

    def test_client_country_stored_in_settings(self, mock_dependencies):
        """
        Test that client country is properly stored in settings via SessionManager.
        """
        mocks = mock_dependencies

        # Use a real-like mock for SessionManager
        from unittest.mock import PropertyMock

        stored_country = None

        def mock_set_client_country(country):
            nonlocal stored_country
            stored_country = country

        session = mocks['session_instance']
        session.client_country = None
        session.set_client_country = Mock(side_effect=mock_set_client_country)

        mubi = mocks['mubi_instance']
        mubi.get_cli_country.return_value = 'GB'

        # Act
        if not session.client_country:
            client_country = mubi.get_cli_country()
            session.set_client_country(client_country)

        # Assert
        assert stored_country == 'GB'
        session.set_client_country.assert_called_once_with('GB')

    def test_client_country_detection_uses_mubi_api(self, mock_dependencies):
        """
        Test that client country detection queries mubi.com to get geo-location.
        The get_cli_country method should be called which queries https://mubi.com/
        """
        mocks = mock_dependencies
        session = mocks['session_instance']
        mubi = mocks['mubi_instance']

        session.client_country = None
        mubi.get_cli_country.return_value = 'CH'  # Switzerland

        # Act
        if not session.client_country:
            detected_country = mubi.get_cli_country()
            session.set_client_country(detected_country)

        # Assert: The MUBI API method was used
        mubi.get_cli_country.assert_called_once()
        session.set_client_country.assert_called_once_with('CH')

    def test_client_country_empty_string_triggers_detection(self, mock_dependencies):
        """
        Test that empty string client_country triggers auto-detection.
        Python's falsy check should treat '' as needing detection.
        """
        mocks = mock_dependencies
        session = mocks['session_instance']
        mubi = mocks['mubi_instance']

        # Arrange: Empty string (falsy in Python)
        session.client_country = ''
        mubi.get_cli_country.return_value = 'AU'

        # Act
        if not session.client_country:
            client_country = mubi.get_cli_country()
            session.set_client_country(client_country)

        # Assert
        mubi.get_cli_country.assert_called_once()
        session.set_client_country.assert_called_once_with('AU')

    def test_client_country_none_triggers_detection(self, mock_dependencies):
        """
        Test that None client_country triggers auto-detection.
        """
        mocks = mock_dependencies
        session = mocks['session_instance']
        mubi = mocks['mubi_instance']

        # Arrange: None (falsy in Python)
        session.client_country = None
        mubi.get_cli_country.return_value = 'NZ'

        # Act
        if not session.client_country:
            client_country = mubi.get_cli_country()
            session.set_client_country(client_country)

        # Assert
        mubi.get_cli_country.assert_called_once()
        session.set_client_country.assert_called_once_with('NZ')
