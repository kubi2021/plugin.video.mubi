"""
Test suite for SessionManager class following QA guidelines.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Happy path, edge cases, and error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from plugin_video_mubi.resources.lib.session_manager import SessionManager


class TestSessionManager:
    """Test cases for the SessionManager class."""

    def test_session_manager_initialization(self, mock_addon):
        """Test SessionManager initialization with existing settings."""
        # Arrange
        mock_addon.getSetting.side_effect = lambda key: {
            'deviceID': 'existing-device-id',
            'client_country': 'US',
            'accept-language': 'en',
            'token': 'existing-token',
            'userID': 'user123'
        }.get(key, '')

        # Act
        session = SessionManager(mock_addon)

        # Assert
        assert session.plugin == mock_addon
        assert session.device_id == 'existing-device-id'
        assert session.client_country == 'US'
        assert session.client_language == 'en'
        assert session.token == 'existing-token'
        assert session.user_id == 'user123'
        assert session.is_logged_in is True

    def test_session_manager_initialization_no_existing_settings(self, mock_addon):
        """Test SessionManager initialization without existing settings."""
        # Arrange
        mock_addon.getSetting.return_value = ''

        # Act
        with patch.object(SessionManager, 'generate_device_id', return_value='new-device-id'):
            session = SessionManager(mock_addon)

        # Assert
        assert session.device_id == 'new-device-id'
        assert session.client_country == ''
        assert session.client_language == ''
        assert session.token == ''
        assert session.user_id == ''
        assert session.is_logged_in is False

    def test_get_or_generate_device_id_existing(self, mock_addon):
        """Test retrieving existing device ID."""
        mock_addon.getSetting.side_effect = lambda key: {
            'deviceID': 'existing-device-123'
        }.get(key, '')
        
        session = SessionManager(mock_addon)
        device_id = session.get_or_generate_device_id()
        
        assert device_id == 'existing-device-123'
        # Should not call setSetting since device ID already exists
        mock_addon.setSetting.assert_not_called()

    @patch('xbmc.log')
    def test_get_or_generate_device_id_new(self, mock_log, mock_addon):
        """Test generating new device ID when none exists."""
        mock_addon.getSetting.return_value = ''  # No existing device ID
        
        with patch.object(SessionManager, 'generate_device_id', return_value='new-device-456'):
            session = SessionManager(mock_addon)
            device_id = session.get_or_generate_device_id()
        
        assert device_id == 'new-device-456'
        mock_addon.setSetting.assert_called_with('deviceID', 'new-device-456')
        mock_log.assert_called()

    @patch('xbmc.log')
    def test_get_or_generate_device_id_exception(self, mock_log, mock_addon):
        """Test device ID generation handles exceptions."""
        session = SessionManager(mock_addon)

        # Mock the entire get_or_generate_device_id method to raise an exception
        with patch.object(session, '_get_plugin_setting', side_effect=Exception("Settings error")):
            with patch.object(session, 'generate_device_id', side_effect=Exception("Generation error")):
                device_id = session.get_or_generate_device_id()

        assert device_id == ''
        mock_log.assert_called()

    def test_generate_device_id_format(self, mock_addon):
        """Test device ID generation format."""
        session = SessionManager(mock_addon)
        
        with patch.object(session, '_code_gen', side_effect=['12345678', '1234', '5678', '9abc', '123456789012']):
            device_id = session.generate_device_id()
        
        assert device_id == '12345678-1234-5678-9abc-123456789012'

    @patch('xbmc.log')
    def test_generate_device_id_exception(self, mock_log, mock_addon):
        """Test device ID generation handles exceptions."""
        session = SessionManager(mock_addon)
        
        with patch.object(session, '_code_gen', side_effect=Exception("Random generation error")):
            device_id = session.generate_device_id()
        
        assert device_id == ''
        mock_log.assert_called()

    def test_code_gen_length(self, mock_addon):
        """Test random code generation with different lengths."""
        session = SessionManager(mock_addon)
        
        # Test different lengths
        code_4 = session._code_gen(4)
        code_8 = session._code_gen(8)
        code_12 = session._code_gen(12)
        
        assert len(code_4) == 4
        assert len(code_8) == 8
        assert len(code_12) == 12
        
        # Test that generated codes contain only valid hex characters
        valid_chars = set('0123456789abcdef')
        assert all(c in valid_chars for c in code_4)
        assert all(c in valid_chars for c in code_8)
        assert all(c in valid_chars for c in code_12)

    def test_code_gen_randomness(self, mock_addon):
        """Test that code generation produces different results."""
        session = SessionManager(mock_addon)
        
        # Generate multiple codes and ensure they're different
        codes = [session._code_gen(8) for _ in range(10)]
        unique_codes = set(codes)
        
        # Should have generated different codes (very unlikely to be all the same)
        assert len(unique_codes) > 1

    @patch('xbmc.log')
    def test_code_gen_exception(self, mock_log, mock_addon):
        """Test code generation handles exceptions."""
        session = SessionManager(mock_addon)
        
        with patch('random.choice', side_effect=Exception("Random error")):
            code = session._code_gen(8)
        
        assert code == ''
        mock_log.assert_called()

    @patch('xbmc.log')
    def test_set_logged_in_success(self, mock_log, mock_addon):
        """Test successful login state setting."""
        session = SessionManager(mock_addon)
        
        session.set_logged_in('test-token-123', 'user-456')
        
        assert session.token == 'test-token-123'
        assert session.user_id == 'user-456'
        assert session.is_logged_in is True
        
        # Verify settings were saved
        mock_addon.setSetting.assert_any_call('token', 'test-token-123')
        mock_addon.setSetting.assert_any_call('userID', 'user-456')
        mock_addon.setSettingBool.assert_called_with('logged', True)
        
        mock_log.assert_called()

    @patch('xbmc.log')
    def test_set_logged_in_exception(self, mock_log, mock_addon):
        """Test login state setting handles exceptions with atomic rollback."""
        mock_addon.setSetting.side_effect = Exception("Settings error")

        session = SessionManager(mock_addon)

        # BUG #8 FIX: Method should now raise exception for atomic behavior
        with pytest.raises(Exception, match="Settings error"):
            session.set_logged_in('test-token', 'user-id')

        # Verify state was rolled back atomically (empty string is the original state from mock)
        assert session.token == ""  # Original state from mock_addon
        assert session.user_id == ""  # Original state from mock_addon
        assert session.is_logged_in is False

        mock_log.assert_called()

    @patch('xbmc.log')
    def test_set_logged_out_success(self, mock_log, mock_addon):
        """Test successful logout state setting."""
        # Start with logged in state
        mock_addon.getSetting.side_effect = lambda key: {
            'token': 'existing-token',
            'userID': 'existing-user'
        }.get(key, '')
        
        session = SessionManager(mock_addon)
        session.set_logged_out()
        
        assert session.token is None
        assert session.user_id is None
        assert session.is_logged_in is False
        
        # Verify settings were cleared
        mock_addon.setSetting.assert_any_call('token', '')
        mock_addon.setSetting.assert_any_call('userID', '')
        mock_addon.setSettingBool.assert_called_with('logged', False)
        
        mock_log.assert_called()

    @patch('xbmc.log')
    def test_set_logged_out_exception(self, mock_log, mock_addon):
        """Test logout state setting handles exceptions."""
        mock_addon.setSetting.side_effect = Exception("Settings error")
        
        session = SessionManager(mock_addon)
        session.set_logged_out()
        
        mock_log.assert_called()

    def test_set_client_country(self, mock_addon):
        """Test setting client country."""
        session = SessionManager(mock_addon)
        
        session.set_client_country('FR')
        
        assert session.client_country == 'FR'
        mock_addon.setSetting.assert_called_with('client_country', 'FR')

    def test_set_client_language(self, mock_addon):
        """Test setting client language."""
        session = SessionManager(mock_addon)
        
        session.set_client_language('fr-FR')
        
        assert session.client_language == 'fr-FR'
        mock_addon.setSetting.assert_called_with('accept-language', 'fr-FR')

    def test_get_plugin_setting_private_method(self, mock_addon):
        """Test the private _get_plugin_setting method."""
        mock_addon.getSetting.return_value = 'test-value'
        
        session = SessionManager(mock_addon)
        value = session._get_plugin_setting('test-key')
        
        assert value == 'test-value'
        mock_addon.getSetting.assert_called_with('test-key')

    def test_session_manager_state_consistency(self, mock_addon):
        """Test that session manager maintains consistent state."""
        # Start with no token
        mock_addon.getSetting.return_value = ''
        
        session = SessionManager(mock_addon)
        assert session.is_logged_in is False
        
        # Log in
        session.set_logged_in('new-token', 'new-user')
        assert session.is_logged_in is True
        assert session.token == 'new-token'
        assert session.user_id == 'new-user'
        
        # Log out
        session.set_logged_out()
        assert session.is_logged_in is False
        assert session.token is None
        assert session.user_id is None

    def test_session_manager_with_empty_values(self, mock_addon):
        """Test session manager handles empty/None values gracefully."""
        session = SessionManager(mock_addon)
        
        # Test with empty values
        session.set_logged_in('', '')
        assert session.token == ''
        assert session.user_id == ''
        assert session.is_logged_in is True  # Still True because method was called
        
        session.set_client_country('')
        assert session.client_country == ''
        
        session.set_client_language('')
        assert session.client_language == ''
