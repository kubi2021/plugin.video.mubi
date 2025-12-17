import pytest
import os
import sys
import json
from unittest.mock import MagicMock, patch

# Add the repo/plugin_video_mubi/resources/lib to path
RESOURCE_LIB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../repo/plugin_video_mubi/resources/lib'))
sys.path.append(RESOURCE_LIB_PATH)

from models import MubiDatabase, Film

def test_plugin_consumes_valid_schema():
    """
    Test that simulates the plugin loading data and validating it against the schema.
    This ensures that whatever the plugin downloads (simulated here) matches our expectations.
    """
    # Create a dummy compliant fixture
    valid_data = {
        "meta": {
            "generated_at": "2023-10-27T10:00:00Z",
            "version": 1,
            "total_count": 1,
            "mode": "test"
        },
        "items": [
            {
                "mubi_id": 123,
                "title": "Test Film",
                "genres": ["Drama"],
                "countries": ["US"],
                "directors": ["Director Name"],
                "year": 2023,
                "duration": 120
            }
        ]
    }
    
    # Validation should pass
    try:
        db = MubiDatabase(**valid_data)
        assert len(db.items) == 1
        assert db.items[0].title == "Test Film"
    except Exception as e:
        pytest.fail(f"Valid data validation failed: {e}")

def test_plugin_rejects_invalid_schema():
    """
    Test that validation fails for invalid data (e.g. missing required fields).
    """
    invalid_data = {
        "meta": {
             "generated_at": "2023-10-27T10:00:00Z",
             "version": 1,
             "total_count": 1,
             "mode": "test"
        },
        "items": [
            {
                # Missing mubi_id and title
                "genres": ["Drama"]
            }
        ]
    }
    
    with pytest.raises(Exception):
        MubiDatabase(**invalid_data)


