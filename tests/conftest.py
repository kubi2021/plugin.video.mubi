import sys
import os
from unittest.mock import Mock, patch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../repo/plugin_video_mubi')))


def pytest_ignore_collect(collection_path):
    """Ignore files that cannot be stat'd due to macOS SIP or permission issues."""
    try:
        # Just try to stat the path - if it fails, ignore it
        collection_path.stat()
    except PermissionError:
        return True
    
    # Always ignore certain known problematic files
    ignored_patterns = ['.env', '.coverage', '.DS_Store', '.bak']
    name = str(collection_path.name)
    for pattern in ignored_patterns:
        if pattern in name:
            return True
    
    return None


@pytest.fixture
def addon_mocks():
    """
    Shared fixture for addon.py tests.
    
    Returns a factory function that creates mocks with customizable defaults.
    This reduces duplication across test classes while allowing flexibility.
    
    Usage:
        def test_something(self, addon_mocks):
            with addon_mocks() as mocks:
                mocks['session_instance'].client_country = 'FR'
                # ... test code
    """
    from contextlib import contextmanager
    
    @contextmanager
    def create_mocks(
        client_country='CH',
        client_language='en',
        is_first_run=False,
        get_setting_return='',
    ):
        with patch('plugin_video_mubi.addon.SessionManager') as mock_session_manager, \
             patch('plugin_video_mubi.addon.NavigationHandler') as mock_nav_handler, \
             patch('plugin_video_mubi.addon.Mubi') as mock_mubi, \
             patch('xbmcaddon.Addon') as mock_addon, \
             patch('plugin_video_mubi.addon.is_first_run') as mock_is_first_run, \
             patch('plugin_video_mubi.addon.add_mubi_source') as mock_add_source, \
             patch('plugin_video_mubi.addon.mark_first_run') as mock_mark_first_run, \
             patch('plugin_video_mubi.addon.migrate_genre_settings'), \
             patch('xbmc.log'), \
             patch('xbmc.executebuiltin') as mock_executebuiltin, \
             patch('xbmcplugin.endOfDirectory') as mock_end_of_dir, \
             patch('xbmcplugin.setResolvedUrl') as mock_set_resolved, \
             patch('xbmcgui.Dialog') as mock_dialog, \
             patch('xbmcgui.ListItem'):

            mock_session_instance = Mock()
            mock_session_instance.client_country = client_country
            mock_session_instance.client_language = client_language
            mock_session_manager.return_value = mock_session_instance

            mock_mubi_instance = Mock()
            mock_mubi_instance.get_cli_country.return_value = 'US'
            mock_mubi_instance.get_cli_language.return_value = 'en'
            mock_mubi.return_value = mock_mubi_instance

            mock_nav_instance = Mock()
            mock_nav_handler.return_value = mock_nav_instance

            mock_addon_instance = Mock()
            mock_addon_instance.getSetting.return_value = get_setting_return
            mock_addon.return_value = mock_addon_instance

            mock_is_first_run.return_value = is_first_run

            mock_dialog_instance = Mock()
            mock_dialog.return_value = mock_dialog_instance

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
                'executebuiltin': mock_executebuiltin,
                'end_of_directory': mock_end_of_dir,
                'set_resolved_url': mock_set_resolved,
                'dialog': mock_dialog,
                'dialog_instance': mock_dialog_instance,
            }
    
    return create_mocks
