import pytest
import hashlib
import gzip
import json
import io
import sys
import os
from unittest.mock import MagicMock

# Mock xbmc modules BEFORE importing plugin code
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmc'].__file__ = None
sys.modules['xbmc'].LOGINFO = 1
sys.modules['xbmc'].LOGERROR = 2
sys.modules['xbmcgui'] = MagicMock()
sys.modules['xbmcgui'].__file__ = None
sys.modules['xbmcvfs'] = MagicMock()
sys.modules['xbmcvfs'].__file__ = None
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcaddon'].__file__ = None
sys.modules['xbmcplugin'] = MagicMock()
sys.modules['xbmcplugin'].__file__ = None

# Add repo to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../repo/plugin_video_mubi/resources/lib')))

from data_source import GithubDataSource
from models import MubiDatabase


class TestLiveGitHubData:
    """
    Integration tests that hit the live GitHub endpoint.
    Verifies infrastructure integrity: Download -> MD5 -> Schema -> Plugin Integration.
    """
    
    @pytest.fixture(scope="function", autouse=True)
    def ensure_real_requests_context(self):
        """
        Ensure real requests library is used for this test class.
        This handles opting out of the global mocks in conftest.py.
        """
        import sys
        import importlib
        from unittest.mock import MagicMock

        # Store the mocked modules to restore them later
        mocked_modules = {}
        # Unmock requests and standard libraries (only those globally mocked in conftest.py)
        target_prefixes = ['requests', 'dateutil', 'webbrowser', 'time']
        
        # Also need to reload plugin modules that consume requests
        plugin_modules_to_reload = [
            'plugin_video_mubi.resources.lib.data_source',
            'plugin_video_mubi.resources.lib.mubi',
            'resources.lib.data_source',
            'resources.lib.mubi'
        ]

        # 1. Save mocks and remove from sys.modules
        for name in list(sys.modules.keys()):
            # Check if module starts with any of the target prefixes
            # We use 'name == t or name.startswith(t + ".")' to avoid partial matches like 'timer' matching 'time'
            if any(name == t or name.startswith(t + ".") for t in target_prefixes):
                mocked_modules[name] = sys.modules[name]
                del sys.modules[name]
        
        # 2. Import real modules and place them in sys.modules
        import requests
        import time
        import webbrowser
        
        # Explicitly ensure they're in sys.modules with the real versions
        sys.modules['requests'] = requests
        sys.modules['time'] = time
        sys.modules['webbrowser'] = webbrowser
        
        # CRITICAL: Also ensure hashlib/gzip/json/io are NOT mocked
        # These were never globally mocked in conftest.py, but unit tests might have set them
        # Force real imports to ensure data_source.py gets real modules
        import hashlib as real_hashlib
        import gzip as real_gzip
        import json as real_json
        import io as real_io
        
        sys.modules['hashlib'] = real_hashlib
        sys.modules['gzip'] = real_gzip
        sys.modules['json'] = real_json
        sys.modules['io'] = real_io
        
        # 3. Reload plugin modules so they bind to the real modules
        reloaded_plugin_modules = []
        for pm in plugin_modules_to_reload:
            if pm in sys.modules:
                try:
                    importlib.reload(sys.modules[pm])
                    reloaded_plugin_modules.append(pm)
                except Exception as e:
                    print(f"Warning: Failed to reload {pm} for integration test: {e}")

        yield

        # 4. Teardown: Restore mocks
        # Clear real modules that were imported
        for name in list(sys.modules.keys()):
            # Only delete modules that we saved as mocks
            if name in mocked_modules:
                if name in sys.modules:
                    del sys.modules[name]
                
        # Restore saved mocks
        sys.modules.update(mocked_modules)
        
        # Reload plugin modules AGAIN so they bind back to the mocks
        for pm in reloaded_plugin_modules:
            if pm in sys.modules:
                try:
                    importlib.reload(sys.modules[pm])
                except Exception as e:
                    print(f"Warning: Failed to restore {pm} to mocks: {e}")
            
    GITHUB_URL = "https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz"

    
    def test_live_data_integrity_and_schema(self):
        """
        Downloads live files, verifies MD5, and validates schema using Pydantic.
        """
        import requests
        
        # 1. Download MD5
        md5_url = self.GITHUB_URL + ".md5"
        print(f"\nDownloading MD5 from {md5_url}...")
        resp_md5 = requests.get(md5_url, timeout=10)
        resp_md5.raise_for_status()
        expected_md5 = resp_md5.text.strip().split()[0]
        
        # 2. Download Content
        print(f"Downloading Database from {self.GITHUB_URL}...")
        resp_data = requests.get(self.GITHUB_URL, stream=True, timeout=30)
        resp_data.raise_for_status()
        content = resp_data.content
        
        # 3. Verify MD5
        calculated_md5 = hashlib.md5(content).hexdigest()
        assert calculated_md5 == expected_md5, f"MD5 mismatch! Expected {expected_md5}, got {calculated_md5}"
        print("MD5 Verification Passed.")
        
        # 4. Decompress
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
            json_data = json.load(gz)
            
        # 5. Verify Schema (Pydantic)
        # This will raise validation error if schema doesn't match
        # We handle normalization in the plugin, but the RAW data should match 'MubiDatabase' if we aligned them.
        # Wait, MubiDatabase model in 'models.py' defined 'directors' as List[str] because that's what the backend produces.
        # So this validation should PASS on raw data.
        print("Validating Schema...")
        db = MubiDatabase(**json_data)
        assert len(db.items) > 0
        print(f"Schema Validation Passed. {len(db.items)} items found.")
        
    def test_github_data_source_integration(self):
        """
        Verifies that GithubDataSource class correctly handles the live data 
        (including internal MD5 check and normalization).
        """
        source = GithubDataSource()
        
        # This calls get_films(), which does the internal MD5 check and normalization
        films = source.get_films()
        
        assert len(films) > 0
        
        # Verify normalization happened
        first_film = films[0]
        assert 'id' in first_film, "ID normalization failed"
        assert 'directors' in first_film
        if first_film['directors']:
            assert isinstance(first_film['directors'][0], dict), "Directors normalization failed (expected dicts)"
            assert 'name' in first_film['directors'][0], "Directors dict missing 'name' key"
