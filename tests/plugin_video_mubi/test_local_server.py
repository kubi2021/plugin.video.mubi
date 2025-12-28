
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock modules before import
if 'xbmcvfs' not in sys.modules:
    sys.modules['xbmcvfs'] = Mock()
    sys.modules['xbmcvfs'].__file__ = None
if 'xbmc' not in sys.modules:
    sys.modules['xbmc'] = Mock()
    sys.modules['xbmc'].__file__ = None

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
        instance1 = LocalServer.get_instance()
        instance2 = LocalServer.get_instance()
        self.assertIs(instance1, instance2)
        
    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    @patch('threading.Thread')
    def test_get_url_starts_server_and_returns_url(self, mock_thread_cls, mock_server_cls):
        # Setup mocks
        mock_server_instance = Mock()
        mock_server_instance.server_address = ('127.0.0.1', 54321) # Mock bound port
        mock_server_cls.return_value = mock_server_instance
        
        mock_thread_instance = Mock()
        mock_thread_cls.return_value = mock_thread_instance
        
        server = LocalServer.get_instance()
        
        # Test get_url
        file_path = "special://temp/test_manifest.mpd"
        url = server.get_url(file_path)
        
        # Assertions
        # 1. Server should be started
        mock_server_cls.assert_called_once()
        mock_thread_cls.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        
        # 2. URL should contain correct port and filename
        self.assertEqual(url, "http://127.0.0.1:54321/test_manifest.mpd")
        
        # 3. Requesting empty/repeat lookup shouldn't restart server
        url2 = server.get_url("/some/other/path/file2.mpd")
        mock_server_cls.assert_called_once() # Still only once
        self.assertEqual(url2, "http://127.0.0.1:54321/file2.mpd")

    @patch('plugin_video_mubi.resources.lib.local_server.ThreadingTCPServer')
    def test_stop_server(self, mock_server_cls):
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

if __name__ == '__main__':
    unittest.main()
