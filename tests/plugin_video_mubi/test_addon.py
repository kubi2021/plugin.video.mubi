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

# Constants for testing (avoid conftest import issues - pytest picks up wrong conftest.py)
MOCK_HANDLE = 123
MOCK_BASE_URL = "plugin://plugin.video.mubi/"


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
        # We must patch objects where them are USED (in plugin_video_mubi.addon namespace)
        # for objects imported via 'from ... import ...'
        with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.addon.add_mubi_source') as mock_add_source, \
             patch('plugin_video_mubi.addon.mark_first_run') as mock_mark_first_run, \
             patch('plugin_video_mubi.addon.migrate_genre_settings'), \
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
            mock_addon_instance.getSetting.return_value = ""  # Default to empty string
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
        """Test basic addon functionality by calling the real main() function."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = 'US'
        mocks['session_instance'].client_language = 'en'

        # Act: Call the real main function with no action (triggers main_navigation)
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert: Verify actual component initialization happened
        mocks['session_manager'].assert_called_once()
        mocks['mubi'].assert_called_once()
        mocks['navigation_handler'].assert_called_once()
        # Verify main_navigation was called (default action)
        mocks['nav_instance'].main_navigation.assert_called_once()



    def test_addon_first_run_logic_integration(self, mock_dependencies):
        """Test first run logic by calling addon.main() with is_first_run=True."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = 'US'
        mocks['session_instance'].client_language = 'en'

        # Arrange: Set first run to True
        mocks['is_first_run'].return_value = True

        # Act: Call the real main function
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert: Verify the first-run sequence was executed
        mocks['is_first_run'].assert_called_once()
        mocks['add_source'].assert_called_once()
        mocks['mark_first_run'].assert_called_once()


class TestErrorHandling:
    """
    Test cases for error handling paths in addon.main().

    The addon uses try/except blocks to prevent Kodi from crashing.
    These tests verify that exceptions are caught and failures are signaled.
    """

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all addon dependencies for error tests."""
        with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.addon.add_mubi_source'), \
             patch('plugin_video_mubi.addon.mark_first_run'), \
             patch('plugin_video_mubi.addon.migrate_genre_settings'), \
             patch('xbmc.log'), \
             patch('xbmcplugin.endOfDirectory') as mock_end_of_dir, \
             patch('xbmcplugin.setResolvedUrl') as mock_set_resolved:

            mock_session_instance = Mock()
            mock_session_instance.client_country = 'US'
            mock_session_instance.client_language = 'en'
            mock_session_manager.return_value = mock_session_instance

            mock_mubi_instance = Mock()
            mock_mubi.return_value = mock_mubi_instance

            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance

            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = 'US'
            mock_addon.return_value = mock_addon_instance

            mock_is_first_run.return_value = False

            yield {
                'nav_instance': mock_nav_instance,
                'end_of_directory': mock_end_of_dir,
                'set_resolved_url': mock_set_resolved,
            }

    def test_log_in_error_signals_failure(self, mock_dependencies):
        """Test that log_in errors are caught and signaled to Kodi."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['nav_instance'].log_in.side_effect = Exception("Network error")

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=log_in"]
        addon.main(argv)

        # Assert: endOfDirectory called with succeeded=False
        mocks['end_of_directory'].assert_called_with(123, succeeded=False)

    def test_log_out_error_signals_failure(self, mock_dependencies):
        """Test that log_out errors are caught and signaled to Kodi."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['nav_instance'].log_out.side_effect = Exception("Session expired")

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=log_out"]
        addon.main(argv)

        # Assert
        mocks['end_of_directory'].assert_called_with(123, succeeded=False)

    def test_play_ext_error_signals_failure(self, mock_dependencies):
        """Test that play_ext errors are caught and signaled to Kodi."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['nav_instance'].play_video_ext.side_effect = Exception("Invalid URL")

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=play_ext&web_url=http://example.com"]
        addon.main(argv)

        # Assert
        mocks['end_of_directory'].assert_called_with(123, succeeded=False)

    def test_play_trailer_error_signals_failure(self, mock_dependencies):
        """Test that play_trailer errors are caught and signaled to Kodi."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['nav_instance'].play_trailer.side_effect = Exception("Trailer not found")

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=play_trailer&url=http://example.com/trailer"]
        addon.main(argv)

        # Assert
        mocks['end_of_directory'].assert_called_with(123, succeeded=False)

    def test_play_mubi_video_error_signals_failure(self, mock_dependencies):
        """Test that play_mubi_video errors signal failure via setResolvedUrl."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['nav_instance'].play_mubi_video.side_effect = Exception("DRM error")

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=play_mubi_video&film_id=999"]
        addon.main(argv)

        # Assert: setResolvedUrl called with success=False
        mocks['set_resolved_url'].assert_called_once()
        call_args = mocks['set_resolved_url'].call_args
        assert call_args[0][0] == 123  # handle
        assert call_args[0][1] is False  # success=False


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
        with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.addon.add_mubi_source') as mock_add_source, \
             patch('plugin_video_mubi.addon.mark_first_run') as mock_mark_first_run, \
             patch('plugin_video_mubi.addon.migrate_genre_settings'), \
             patch('xbmc.log') as mock_log:

            mock_session_instance = Mock()
            mock_session_manager.return_value = mock_session_instance

            mock_mubi_instance = Mock()
            mock_mubi.return_value = mock_mubi_instance

            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance

            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""  # Default to empty string
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
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = None
        mocks['session_instance'].client_language = 'en'
        mocks['mubi_instance'].get_cli_country.return_value = 'US'

        # Act: Call the real main function
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert: Verify get_cli_country was called and country was set
        mocks['mubi_instance'].get_cli_country.assert_called_once()
        mocks['session_instance'].set_client_country.assert_called_once_with('US')

    def test_client_country_not_auto_detected_when_already_set(self, mock_dependencies):
        """Test that client country is NOT auto-detected when already stored."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = 'FR'
        mocks['session_instance'].client_language = 'fr'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_country.assert_not_called()
        mocks['session_instance'].set_client_country.assert_not_called()

    def test_client_country_re_detected_after_settings_reset(self, mock_dependencies):
        """Test that client country is re-detected when settings.xml is removed/reset."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = ''
        mocks['mubi_instance'].get_cli_country.return_value = 'DE'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_country.assert_called_once()
        mocks['session_instance'].set_client_country.assert_called_once_with('DE')

    def test_client_country_user_override_persists(self, mock_dependencies):
        """Test that user-set country overrides persist and are not overwritten."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = 'JP'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_country.assert_not_called()
        mocks['session_instance'].set_client_country.assert_not_called()

    def test_client_country_stored_in_settings(self, mock_dependencies):
        """Test that client country is properly stored in settings via SessionManager."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        from unittest.mock import PropertyMock

        stored_country = None
        def mock_set_client_country(country):
            nonlocal stored_country
            stored_country = country

        mocks['session_instance'].client_country = None
        mocks['session_instance'].set_client_country = Mock(side_effect=mock_set_client_country)
        mocks['mubi_instance'].get_cli_country.return_value = 'GB'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        assert stored_country == 'GB'
        mocks['session_instance'].set_client_country.assert_called_once_with('GB')

    def test_client_country_detection_uses_mubi_api(self, mock_dependencies):
        """Test that client country detection queries mubi.com."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = None
        mocks['mubi_instance'].get_cli_country.return_value = 'CH'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_country.assert_called_once()
        mocks['session_instance'].set_client_country.assert_called_once_with('CH')

    def test_client_country_empty_string_triggers_detection(self, mock_dependencies):
        """
        Test that client country is auto-detected when empty.
        
        Note: Python treats '' as falsy, so `if not session.client_country:`
        will trigger detection. This is intentional to handle settings.xml 
        with empty values.
        """
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = ''
        mocks['mubi_instance'].get_cli_country.return_value = 'AU'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_country.assert_called_once()
        mocks['session_instance'].set_client_country.assert_called_once_with('AU')

    def test_client_country_none_triggers_detection(self, mock_dependencies):
        """Test that None client_country triggers auto-detection."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = None
        mocks['mubi_instance'].get_cli_country.return_value = 'NZ'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_country.assert_called_once()
        mocks['session_instance'].set_client_country.assert_called_once_with('NZ')


class TestSyncLocally:
    """
    Test cases for local sync action.

    The sync_locally action should:
    1. Sync only the user's configured country
    2. Show a notification error if no country is configured
    """

    @pytest.fixture
    def mock_sync_dependencies(self):
        """Fixture to mock sync-related dependencies."""
        with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.addon.add_mubi_source'), \
             patch('plugin_video_mubi.addon.mark_first_run'), \
             patch('plugin_video_mubi.addon.migrate_genre_settings'), \
             patch('xbmc.log'), \
             patch('xbmc.executebuiltin') as mock_executebuiltin, \
             patch('xbmcgui.Dialog') as mock_dialog:

            mock_session_instance = Mock()
            mock_session_instance.client_country = 'CH'
            mock_session_manager.return_value = mock_session_instance

            mock_mubi_instance = Mock()
            mock_mubi.return_value = mock_mubi_instance

            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance

            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = 'CH'
            mock_addon.return_value = mock_addon_instance

            mock_is_first_run.return_value = False

            mock_dialog_instance = Mock()
            mock_dialog.return_value = mock_dialog_instance

            yield {
                'nav_instance': mock_nav_instance,
                'addon_instance': mock_addon_instance,
                'executebuiltin': mock_executebuiltin,
                'dialog': mock_dialog,
                'dialog_instance': mock_dialog_instance,
            }

    def test_sync_locally_with_country_calls_sync_films(self, mock_sync_dependencies):
        """Test that sync_locally syncs the configured country."""
        from plugin_video_mubi import addon
        mocks = mock_sync_dependencies
        mocks['addon_instance'].getSetting.return_value = 'US'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=sync_locally"]
        addon.main(argv)

        # Assert
        mocks['nav_instance'].sync_films.assert_called_once()
        call_kwargs = mocks['nav_instance'].sync_films.call_args[1]
        assert call_kwargs['countries'] == ['US']

    def test_sync_locally_missing_country_shows_notification(self, mock_sync_dependencies):
        """Test that sync_locally shows error notification when no country is configured."""
        from plugin_video_mubi import addon
        mocks = mock_sync_dependencies
        mocks['addon_instance'].getSetting.return_value = ''

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=sync_locally"]
        addon.main(argv)

        # Assert: sync_films should NOT be called
        mocks['nav_instance'].sync_films.assert_not_called()
        # Assert: notification dialog should be shown
        mocks['dialog_instance'].notification.assert_called_once()
        call_args = mocks['dialog_instance'].notification.call_args
        assert 'MUBI' in call_args[0]
        assert 'country' in call_args[0][1].lower()


class TestSyncWorldwideOptimization:
    """
    Test cases for worldwide sync optimization using coverage optimizer.

    The sync_worldwide action should:
    1. Use the coverage optimizer to find optimal countries
    2. Fall back to all countries if JSON catalogue is missing
    3. Use the user's configured country as the starting point
    """

    @pytest.fixture
    def mock_sync_dependencies(self):
        """Fixture to mock sync-related dependencies."""
        with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.addon.add_mubi_source'), \
             patch('plugin_video_mubi.addon.mark_first_run'), \
             patch('plugin_video_mubi.addon.migrate_genre_settings'), \
             patch('xbmc.log') as mock_log, \
             patch('xbmc.executebuiltin') as mock_executebuiltin:

            # Setup basic mocks required by addon.main()
            mock_session_instance = Mock()
            mock_session_instance.client_country = 'CH' # Default to having a country set
            mock_session_manager.return_value = mock_session_instance
            
            mock_mubi_instance = Mock()
            mock_mubi.return_value = mock_mubi_instance
            
            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance

            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = 'CH' # Default country for sync tests
            mock_addon.return_value = mock_addon_instance
            
            mock_is_first_run.return_value = False

            yield {
                'navigation_handler': mock_nav_handler,
                'nav_instance': mock_nav_instance,
                'addon': mock_addon,
                'addon_instance': mock_addon_instance,
                'log': mock_log,
                'executebuiltin': mock_executebuiltin,
                'session_instance': mock_session_instance,
            }

    def test_sync_worldwide_uses_optimal_countries(self, mock_sync_dependencies):
        """Test that worldwide sync uses the coverage optimizer."""
        from plugin_video_mubi import addon
        mocks = mock_sync_dependencies
        
        with patch('resources.lib.coverage_optimizer.get_optimal_countries') as mock_optimizer:
            # Arrange
            mock_optimizer.return_value = ['CH', 'TR', 'US', 'MX', 'FR']
            
            # Act
            argv = ["plugin://plugin.video.mubi/", "123", "?action=sync_worldwide"]
            addon.main(argv)

            # Assert
            mock_optimizer.assert_called_once_with('CH')
            
            mocks['nav_instance'].sync_films.assert_called()
            call_args = mocks['nav_instance'].sync_films.call_args
            kwargs = call_args[1]
            assert 'countries' in kwargs
            assert len(kwargs['countries']) == 5


    def test_sync_worldwide_fallback_when_no_catalogue(self, mock_sync_dependencies):
        """Test that worldwide sync falls back to all countries."""
        from plugin_video_mubi import addon
        mocks = mock_sync_dependencies

        with patch('resources.lib.coverage_optimizer.get_optimal_countries') as mock_optimizer:
            mock_optimizer.return_value = []

            # Act
            argv = ["plugin://plugin.video.mubi/", "123", "?action=sync_worldwide"]
            addon.main(argv)

            # Assert: Fallback uses all countries from COUNTRIES dict
            from resources.lib.countries import COUNTRIES
            mocks['nav_instance'].sync_films.assert_called()
            kwargs = mocks['nav_instance'].sync_films.call_args[1]
            assert len(kwargs['countries']) == len(COUNTRIES)

    def test_sync_worldwide_uses_configured_country(self, mock_sync_dependencies):
        """Test that worldwide sync uses the user's configured country setting."""
        from plugin_video_mubi import addon
        mocks = mock_sync_dependencies
        mocks['addon_instance'].getSetting.return_value = 'US'
        mocks['session_instance'].client_country = 'US'

        with patch('resources.lib.coverage_optimizer.get_optimal_countries') as mock_optimizer:
            mock_optimizer.return_value = ['US', 'TR', 'CH']

            # Act
            argv = ["plugin://plugin.video.mubi/", "123", "?action=sync_worldwide"]
            addon.main(argv)

            # Assert
            mock_optimizer.assert_called_once_with('US')

    def test_sync_worldwide_defaults_to_ch_when_no_setting(self, mock_sync_dependencies):
        """Test that worldwide sync defaults to CH when no country is configured."""
        from plugin_video_mubi import addon
        mocks = mock_sync_dependencies
        mocks['addon_instance'].getSetting.return_value = ''
        mocks['session_instance'].client_country = None # Force fallback logic if used, though main logic uses getSetting("client_country") or "CH"

        with patch('resources.lib.coverage_optimizer.get_optimal_countries') as mock_optimizer:
            mock_optimizer.return_value = ['CH', 'TR', 'US']

            # Act
            argv = ["plugin://plugin.video.mubi/", "123", "?action=sync_worldwide"]
            addon.main(argv)

            # Assert
            mock_optimizer.assert_called_once_with('CH')


class TestMissingActions:
    """
    Test cases for actions that were previously untested.
    
    These actions are simpler navigation dispatches without try/except blocks,
    but should still be verified to ensure correct routing.
    """

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all addon dependencies."""
        with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.addon.add_mubi_source'), \
             patch('plugin_video_mubi.addon.mark_first_run'), \
             patch('plugin_video_mubi.addon.migrate_genre_settings'), \
             patch('xbmc.log'), \
             patch('xbmc.executebuiltin') as mock_executebuiltin:

            mock_session_instance = Mock()
            mock_session_instance.client_country = 'CH'
            mock_session_instance.client_language = 'en'
            mock_session_manager.return_value = mock_session_instance

            mock_mubi_instance = Mock()
            mock_mubi.return_value = mock_mubi_instance

            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance

            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = 'CH'
            mock_addon.return_value = mock_addon_instance

            mock_is_first_run.return_value = False

            yield {
                'nav_instance': mock_nav_instance,
                'executebuiltin': mock_executebuiltin,
            }

    def test_list_categories_action_calls_navigation_method(self, mock_dependencies):
        """Test that action=list_categories calls navigation.list_categories()."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=list_categories"]
        addon.main(argv)

        # Assert
        mocks['nav_instance'].list_categories.assert_called_once()

    def test_watchlist_action_calls_navigation_method(self, mock_dependencies):
        """Test that action=watchlist calls navigation.list_watchlist()."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=watchlist"]
        addon.main(argv)

        # Assert
        mocks['nav_instance'].list_watchlist.assert_called_once()

    def test_sync_github_action_calls_navigation_method(self, mock_dependencies):
        """Test that action=sync_github calls navigation.sync_from_github()."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=sync_github"]
        addon.main(argv)

        # Assert
        mocks['nav_instance'].sync_from_github.assert_called_once()
        mocks['executebuiltin'].assert_called_with('Container.Refresh')

    def test_sync_github_passes_country_parameter(self, mock_dependencies):
        """Test that sync_github forwards the country parameter correctly."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", "?action=sync_github&country=US"]
        addon.main(argv)

        # Assert
        mocks['nav_instance'].sync_from_github.assert_called_once()
        call_kwargs = mocks['nav_instance'].sync_from_github.call_args[1]
        assert call_kwargs['country'] == 'US'


class TestClientLanguageAutoDetection:
    """
    Test cases for client language auto-detection logic.
    
    Mirrors TestClientCountryAutoDetection to ensure language detection
    follows the same patterns as country detection.
    """

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all addon dependencies."""
        with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.addon.add_mubi_source'), \
             patch('plugin_video_mubi.addon.mark_first_run'), \
             patch('plugin_video_mubi.addon.migrate_genre_settings'), \
             patch('xbmc.log'):

            mock_session_instance = Mock()
            mock_session_manager.return_value = mock_session_instance

            mock_mubi_instance = Mock()
            mock_mubi.return_value = mock_mubi_instance

            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance

            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = ""
            mock_addon.return_value = mock_addon_instance

            mock_is_first_run.return_value = False

            yield {
                'session_instance': mock_session_instance,
                'mubi_instance': mock_mubi_instance,
            }

    def test_client_language_auto_detected_when_not_set(self, mock_dependencies):
        """Test that client language is auto-detected via MUBI API when not set."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = 'US'
        mocks['session_instance'].client_language = None
        mocks['mubi_instance'].get_cli_language.return_value = 'en'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_language.assert_called_once()
        mocks['session_instance'].set_client_language.assert_called_once_with('en')

    def test_client_language_not_auto_detected_when_already_set(self, mock_dependencies):
        """Test that client language is NOT auto-detected when already stored."""
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = 'FR'
        mocks['session_instance'].client_language = 'fr'

        # Act
        argv = ["plugin://plugin.video.mubi/", "123", ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_language.assert_not_called()
        mocks['session_instance'].set_client_language.assert_not_called()

    def test_client_language_empty_string_triggers_detection(self, mock_dependencies):
        """
        Test that client language is auto-detected when empty.
        
        Note: Python treats '' as falsy, so `if not session.client_language:`
        will trigger detection. This is intentional to handle settings.xml 
        with empty values.
        """
        from plugin_video_mubi import addon
        mocks = mock_dependencies
        mocks['session_instance'].client_country = 'DE'
        mocks['session_instance'].client_language = ''
        mocks['mubi_instance'].get_cli_language.return_value = 'de'

        # Act
        argv = [MOCK_BASE_URL, str(MOCK_HANDLE), ""]
        addon.main(argv)

        # Assert
        mocks['mubi_instance'].get_cli_language.assert_called_once()
        mocks['session_instance'].set_client_language.assert_called_once_with('de')


class TestPlayMubiVideoEdgeCases:
    """
    Test cases for edge cases in play_mubi_video action.
    
    These tests verify behavior for parameter combinations and URL encoding.
    """

    def test_play_mubi_video_with_film_id_only(self, addon_test_mocks):
        """Test play_mubi_video with only film_id parameter (no web_url)."""
        from plugin_video_mubi import addon
        mocks = addon_test_mocks

        # Act: Call with film_id only, no web_url
        argv = [MOCK_BASE_URL, str(MOCK_HANDLE), "?action=play_mubi_video&film_id=12345"]
        addon.main(argv)

        # Assert: play_mubi_video called with film_id and web_url=None
        mocks['nav_instance'].play_mubi_video.assert_called_once()
        call_args = mocks['nav_instance'].play_mubi_video.call_args[0]
        assert call_args[0] == '12345'  # film_id
        assert call_args[1] is None  # web_url should be None

    def test_play_mubi_video_with_encoded_web_url(self, addon_test_mocks):
        """Test play_mubi_video correctly decodes URL-encoded web_url parameter."""
        from plugin_video_mubi import addon
        from urllib.parse import quote_plus
        mocks = addon_test_mocks

        # Arrange: Create an encoded URL with special characters
        original_url = "https://mubi.com/films/test-movie?tracking=source&ref=homepage"
        encoded_url = quote_plus(original_url)

        # Act
        argv = [MOCK_BASE_URL, str(MOCK_HANDLE), f"?action=play_mubi_video&film_id=12345&web_url={encoded_url}"]
        addon.main(argv)

        # Assert: play_mubi_video received the decoded URL
        mocks['nav_instance'].play_mubi_video.assert_called_once()
        call_args = mocks['nav_instance'].play_mubi_video.call_args[0]
        assert call_args[0] == '12345'  # film_id
        assert call_args[1] == original_url  # web_url should be decoded

    def test_play_mubi_video_with_spaces_in_url(self, addon_test_mocks):
        """Test play_mubi_video correctly handles %20 encoded spaces in URL."""
        from plugin_video_mubi import addon
        from urllib.parse import quote_plus
        mocks = addon_test_mocks

        # Arrange: URL with spaces
        original_url = "https://mubi.com/films/the great movie"
        encoded_url = quote_plus(original_url)

        # Act
        argv = [MOCK_BASE_URL, str(MOCK_HANDLE), f"?action=play_mubi_video&film_id=999&web_url={encoded_url}"]
        addon.main(argv)

        # Assert
        call_args = mocks['nav_instance'].play_mubi_video.call_args[0]
        assert call_args[1] == original_url  # Spaces should be decoded
