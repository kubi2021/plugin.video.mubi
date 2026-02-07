
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock modules before import
if 'xbmcvfs' not in sys.modules:
    sys.modules['xbmcvfs'] = Mock()
    sys.modules['xbmcvfs'].__file__ = None
    sys.modules['xbmcvfs'].__path__ = None
    sys.modules['xbmcvfs'].__spec__ = None
if 'xbmc' not in sys.modules:
    sys.modules['xbmc'] = Mock()
    sys.modules['xbmc'].__file__ = None
    sys.modules['xbmc'].__path__ = None
    sys.modules['xbmc'].__spec__ = None

from plugin_video_mubi.resources.lib.local_server import LocalServer

class TestLocalServer(unittest.TestCase):
    
    def setUp(self):
        # Reset singleton before each test
        LocalServer._instance = None
        
        # Mock translatePath
        self.mock_translate = patch('plugin_video_mubi.resources.lib.local_server.xbmcvfs.translatePath').start()
        self.mock_translate.return_value = "/tmp/kodi_temp"

    def tearDown(self):
        patch.stopall()
        # Clean up if server was started
        if LocalServer._instance and LocalServer._instance.server:
            LocalServer._instance.stop()

    def test_singleton_pattern(self):
        """Verify LocalServer implements singleton pattern correctly."""
        instance1 = LocalServer.get_instance()
        instance2 = LocalServer.get_instance()
        self.assertIs(instance1, instance2)
        
    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    @patch('threading.Thread')
    def test_get_url_starts_server_and_returns_url(self, mock_thread_cls, mock_server_cls):
        """Test that get_url() starts server and returns correct URL format."""
        # Setup mocks
        mock_server_instance = Mock()
        mock_server_instance.server_address = ('127.0.0.1', 54321)
        mock_server_cls.return_value = mock_server_instance
        
        mock_thread_instance = Mock()
        mock_thread_cls.return_value = mock_thread_instance
        
        server = LocalServer.get_instance()
        
        # Test get_url
        file_path = "special://temp/test_manifest.mpd"
        url = server.get_url(file_path)
        
        # Assertions
        mock_server_cls.assert_called_once()
        mock_thread_cls.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        self.assertEqual(url, "http://127.0.0.1:54321/test_manifest.mpd")
        
    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    @patch('threading.Thread')
    def test_get_url_extracts_filename_from_absolute_path(self, mock_thread_cls, mock_server_cls):
        """Verify URL only contains filename, not full path."""
        mock_server_instance = Mock()
        mock_server_instance.server_address = ('127.0.0.1', 12345)
        mock_server_cls.return_value = mock_server_instance
        mock_thread_cls.return_value = Mock()
        
        server = LocalServer.get_instance()
        
        # Absolute path should be stripped to filename only
        url = server.get_url("/some/deep/path/manifest.mpd")
        self.assertEqual(url, "http://127.0.0.1:12345/manifest.mpd")

    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    @patch('threading.Thread')
    def test_multiple_get_url_calls_reuse_server(self, mock_thread_cls, mock_server_cls):
        """Verify server is started only once for multiple requests."""
        mock_server_instance = Mock()
        mock_server_instance.server_address = ('127.0.0.1', 54321)
        mock_server_cls.return_value = mock_server_instance
        mock_thread_cls.return_value = Mock()
        
        server = LocalServer.get_instance()
        
        server.get_url("file1.mpd")
        server.get_url("file2.mpd")
        server.get_url("file3.mpd")
        
        # Server should be created only once
        mock_server_cls.assert_called_once()

    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    def test_stop_server(self, mock_server_cls):
        """Test that stop() properly shuts down the server."""
        mock_server_instance = Mock()
        mock_server_instance.server_address = ('127.0.0.1', 12345)
        mock_server_cls.return_value = mock_server_instance
        
        server = LocalServer.get_instance()
        server.start()
        
        self.assertIsNotNone(server.server)
        self.assertIsNotNone(server.thread)
        
        server.stop()
        
        mock_server_instance.shutdown.assert_called_once()
        mock_server_instance.server_close.assert_called_once()
        self.assertIsNone(server.server)
        self.assertIsNone(server.thread)


class TestLocalServerHealthCheck(unittest.TestCase):
    """Tests for the is_healthy() method."""
    
    def setUp(self):
        LocalServer._instance = None
        self.mock_translate = patch('plugin_video_mubi.resources.lib.local_server.xbmcvfs.translatePath').start()
        self.mock_translate.return_value = "/tmp/kodi_temp"

    def tearDown(self):
        patch.stopall()
        if LocalServer._instance and LocalServer._instance.server:
            LocalServer._instance.stop()

    def test_is_healthy_returns_false_when_server_not_started(self):
        """Health check should return False if server hasn't been started."""
        server = LocalServer.get_instance()
        # Don't call start() or get_url()
        self.assertFalse(server.is_healthy())

    @patch('urllib.request.urlopen')
    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    @patch('threading.Thread')
    def test_is_healthy_returns_true_when_server_responds(self, mock_thread_cls, mock_server_cls, mock_urlopen):
        """Health check should return True when server responds to HTTP request."""
        # Setup server mock
        mock_server_instance = Mock()
        mock_server_instance.server_address = ('127.0.0.1', 12345)
        mock_server_cls.return_value = mock_server_instance
        mock_thread_cls.return_value = Mock()
        
        # Setup urlopen mock - server responds
        mock_response = MagicMock()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        server = LocalServer.get_instance()
        server.start()
        
        result = server.is_healthy()
        
        self.assertTrue(result)
        mock_urlopen.assert_called_once()

    @patch('urllib.request.urlopen')
    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    @patch('threading.Thread')
    def test_is_healthy_returns_false_on_connection_error(self, mock_thread_cls, mock_server_cls, mock_urlopen):
        """Health check should return False when connection fails."""
        mock_server_instance = Mock()
        mock_server_instance.server_address = ('127.0.0.1', 12345)
        mock_server_cls.return_value = mock_server_instance
        mock_thread_cls.return_value = Mock()
        
        # Simulate connection error
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        
        server = LocalServer.get_instance()
        server.start()
        
        result = server.is_healthy()
        
        self.assertFalse(result)

    @patch('urllib.request.urlopen')
    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    @patch('threading.Thread')
    def test_is_healthy_returns_false_on_timeout(self, mock_thread_cls, mock_server_cls, mock_urlopen):
        """Health check should return False on timeout."""
        mock_server_instance = Mock()
        mock_server_instance.server_address = ('127.0.0.1', 12345)
        mock_server_cls.return_value = mock_server_instance
        mock_thread_cls.return_value = Mock()
        
        # Simulate timeout
        import socket
        mock_urlopen.side_effect = socket.timeout("timed out")
        
        server = LocalServer.get_instance()
        server.start()
        
        result = server.is_healthy()
        
        self.assertFalse(result)


class TestLocalServerIntegration(unittest.TestCase):
    """Integration tests that use a real HTTP server (no mocking of server itself)."""
    
    def setUp(self):
        LocalServer._instance = None
        # Use real temp directory path for integration test
        self.mock_translate = patch('plugin_video_mubi.resources.lib.local_server.xbmcvfs.translatePath').start()
        import tempfile
        self.temp_dir = tempfile.gettempdir()
        self.mock_translate.return_value = self.temp_dir

    def tearDown(self):
        patch.stopall()
        if LocalServer._instance and LocalServer._instance.server:
            LocalServer._instance.stop()

    def test_real_server_responds_to_health_check(self):
        """Integration test: verify a real server passes health check."""
        server = LocalServer.get_instance()
        server.start()
        
        # Give server a moment to fully start
        import time
        time.sleep(0.1)
        
        # Real health check against real server
        result = server.is_healthy()
        
        self.assertTrue(result)
        self.assertGreater(server.port, 0)

    def test_real_server_can_serve_file(self):
        """Integration test: verify server can actually serve a file."""
        import tempfile
        import urllib.request
        import os
        
        # Create a test file in temp directory
        test_content = b"<?xml version='1.0'?><MPD></MPD>"
        test_file = os.path.join(self.temp_dir, "test_integration.mpd")
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        try:
            server = LocalServer.get_instance()
            url = server.get_url(test_file)
            
            # Actually fetch the file via HTTP
            import time
            time.sleep(0.1)
            
            with urllib.request.urlopen(url, timeout=5) as response:
                content = response.read()
                self.assertEqual(content, test_content)
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)


if __name__ == '__main__':
    unittest.main()
