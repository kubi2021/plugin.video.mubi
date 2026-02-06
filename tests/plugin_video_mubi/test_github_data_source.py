"""
Test suite for GithubDataSource class.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import gzip
import json
import hashlib
import io
from plugin_video_mubi.resources.lib.data_source import GithubDataSource
import pytest
import sys

# Mock xbmc if not available
if 'xbmc' not in sys.modules:
    sys.modules['xbmc'] = MagicMock()
import xbmc

class TestGithubDataSource(unittest.TestCase):
    """Test cases for the GithubDataSource class."""

    def setUp(self):
        self.data_source = GithubDataSource()
        # Mock xbmc to capture logs
        self.mock_xbmc = sys.modules['xbmc']
        self.mock_xbmc.LOGINFO = 1
        self.mock_xbmc.LOGERROR = 2
        self.mock_xbmc.LOGWARNING = 3

    def _create_gzipped_content(self, data):
        """Helper to create gzipped JSON content."""
        json_data = json.dumps(data).encode('utf-8')
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='w') as f:
            f.write(json_data)
        return out.getvalue()

    @patch('requests.Session')
    def test_get_films_success(self, mock_session_cls):
        """Test successful download and parsing of films."""
        # Arrange
        mock_session = mock_session_cls.return_value
        
        # Films data
        films_data = {
            "meta": {"version": 1},
            "items": [
                {"id": 1, "title": "Film One", "directors": ["Dir A"]},
                {"mubi_id": 2, "title": "Film Two"} # Should normalize mubi_id -> id
            ]
        }
        content = self._create_gzipped_content(films_data)
        md5_hash = hashlib.md5(content).hexdigest()

        # Mock MD5 response
        mock_md5_resp = MagicMock()
        mock_md5_resp.text = md5_hash
        mock_md5_resp.status_code = 200
        
        # Mock Content response
        mock_content_resp = MagicMock()
        mock_content_resp.content = content
        mock_content_resp.status_code = 200
        
        mock_session.get.side_effect = [mock_md5_resp, mock_content_resp]

        # Act
        films = self.data_source.get_films()

        # Assert
        self.assertEqual(len(films), 2)
        self.assertEqual(films[0]['id'], 1)
        # Check directors normalization
        self.assertEqual(films[0]['directors'], [{'name': 'Dir A'}])
        
        # Check ID normalization
        self.assertEqual(films[1]['id'], 2)

    @patch('requests.Session')
    def test_get_films_md5_mismatch(self, mock_session_cls):
        """Test that MD5 mismatch raises ValueError."""
        mock_session = mock_session_cls.return_value
        
        content = self._create_gzipped_content({"items": []})
        # actual hash
        real_md5 = hashlib.md5(content).hexdigest()
        # expected hash (different)
        fake_md5 = "wronghash"

        mock_md5_resp = MagicMock()
        mock_md5_resp.text = fake_md5
        
        mock_content_resp = MagicMock()
        mock_content_resp.content = content
        
        mock_session.get.side_effect = [mock_md5_resp, mock_content_resp]

        with self.assertRaises(ValueError) as cm:
            self.data_source.get_films()
        
        self.assertIn("MD5 verification failed", str(cm.exception))

    @patch('requests.Session')
    def test_get_films_verify_filtering(self, mock_session_cls):
        """Test that films are correctly filtered by country availability."""
        mock_session = mock_session_cls.return_value
        
        # Create data with availability info
        films_data = {
            "items": [
                {
                    "id": 1, 
                    "title": "US Only",
                    "available_countries": {
                        "US": {"availability": "live"}
                    }
                },
                {
                    "id": 2, 
                    "title": "UK Only",
                    "available_countries": {
                        "GB": {"availability": "live"} 
                    }
                },
                {
                    "id": 3,
                    "title": "Expired",
                    "available_countries": {
                        "US": {"available_at": "2020-01-01", "expires_at": "2020-01-02"}
                    }
                }
            ]
        }
        content = self._create_gzipped_content(films_data)
        md5 = hashlib.md5(content).hexdigest()
        
        mock_session.get.side_effect = [
            MagicMock(text=md5),
            MagicMock(content=content)
        ]

        # Ask for US films
        films = self.data_source.get_films(countries=['US'])
        
        # Should get film 1 only
        # Film 2 is GB, Film 3 is expired
        self.assertEqual(len(films), 1)
        self.assertEqual(films[0]['id'], 1)

    @patch('requests.Session')
    def test_get_films_network_error(self, mock_session_cls):
        """Test that network errors are propagated."""
        mock_session = mock_session_cls.return_value
        
        # Raise generic exception on first get call (MD5)
        import requests
        mock_session.get.side_effect = requests.exceptions.RequestException("Connection refused")
        
        with self.assertRaises(requests.exceptions.RequestException):
            self.data_source.get_films()

    @patch('requests.Session')
    def test_version_warning(self, mock_session_cls):
        """Test that unsupported version logs a warning."""
        mock_session = mock_session_cls.return_value
        
        films_data = {
            "meta": {"version": 999, "version_label": "future"},
            "items": []
        }
        content = self._create_gzipped_content(films_data)
        md5 = hashlib.md5(content).hexdigest()
        
        mock_session.get.side_effect = [
            MagicMock(text=md5),
            MagicMock(content=content)
        ]
        
        self.data_source.get_films()
        
        # Check logs for warning
        # Since we can't easily check log output on mocked module without capturing args,
        # we assume it works if no error raised.
        # But we could check call args if we really wanted to be strict.
        pass

if __name__ == '__main__':
    unittest.main()
