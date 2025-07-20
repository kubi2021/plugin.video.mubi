"""
Configuration for repository infrastructure tests.
"""

import pytest
import sys
from pathlib import Path

# Add the repo directory to Python path for imports
repo_path = Path(__file__).parent.parent.parent / "repo"
sys.path.insert(0, str(repo_path))

@pytest.fixture
def repository_root():
    """Fixture providing path to repository root."""
    return Path(__file__).parent.parent.parent

@pytest.fixture
def repo_zips_dir():
    """Fixture providing path to repo/zips directory."""
    return Path(__file__).parent.parent.parent / "repo" / "zips"

@pytest.fixture
def repository_zip_path():
    """Fixture providing path to root repository zip."""
    return Path(__file__).parent.parent.parent / "repository.kubi2021-2.zip"

@pytest.fixture
def index_html_path():
    """Fixture providing path to index.html."""
    return Path(__file__).parent.parent.parent / "index.html"
