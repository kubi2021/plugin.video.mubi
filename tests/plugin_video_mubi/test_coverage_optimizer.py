"""
Test suite for Coverage Optimizer - Greedy Set Cover Algorithm.

Tests the functions in coverage_optimizer.py that determine the minimum
set of countries needed for 100% MUBI catalogue coverage.
"""
import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock


class TestCoverageOptimizer:
    """Test cases for coverage_optimizer functions."""

    @pytest.fixture
    def sample_catalogue(self, tmp_path):
        """Create a sample country catalogue for testing."""
        catalogue = {
            "films": {
                "1": ["us", "gb"],
                "2": ["us", "fr"],
                "3": ["gb"],
                "4": ["fr", "de"],
                "5": ["de"],
                "6": ["jp"],  # Only available in Japan - will always need JP
            }
        }
        catalogue_file = tmp_path / "country_catalogue.json"
        catalogue_file.write_text(json.dumps(catalogue))
        return str(catalogue_file)

    @pytest.fixture
    def mock_countries_module(self):
        """Mock COUNTRIES module for VPN tier lookup."""
        countries_data = {
            "us": {"name": "United States", "vpn_tier": 1},
            "gb": {"name": "United Kingdom", "vpn_tier": 1},
            "fr": {"name": "France", "vpn_tier": 2},
            "de": {"name": "Germany", "vpn_tier": 2},
            "jp": {"name": "Japan", "vpn_tier": 3},
            "ch": {"name": "Switzerland", "vpn_tier": 2},
        }
        # Create mock module
        mock_module = MagicMock()
        mock_module.COUNTRIES = countries_data
        return mock_module, countries_data

    def test_get_optimal_countries_starts_with_user_country(self, sample_catalogue, mock_countries_module):
        """Test that user's country is always first in the optimal list."""
        mock_module, countries_data = mock_countries_module
        
        # Patch both the module and the local import in coverage_optimizer
        with patch.dict(sys.modules, {
            'plugin_video_mubi.resources.lib.countries': mock_module,
            '.countries': mock_module,
        }):
            from plugin_video_mubi.resources.lib import coverage_optimizer
            
            with patch.object(coverage_optimizer, '_get_catalogue_path', return_value=sample_catalogue):
                # Also need to patch the local import inside the function
                original_get = coverage_optimizer.get_optimal_countries
                
                def patched_get(user_country):
                    # Install our mock countries for the function's local import
                    with patch.dict(sys.modules, {'plugin_video_mubi.resources.lib.countries': mock_module}):
                        return original_get(user_country)
                
                result = patched_get("US")
        
        assert len(result) > 0
        assert result[0] == "US"

    def test_get_optimal_countries_empty_catalogue(self):
        """Test handling of missing catalogue file."""
        from plugin_video_mubi.resources.lib import coverage_optimizer
        
        with patch.object(coverage_optimizer, '_get_catalogue_path', return_value="/nonexistent/path.json"):
            result = coverage_optimizer.get_optimal_countries("US")
        
        assert result == []

    def test_load_country_catalogue_invalid_json(self, tmp_path):
        """Test handling of malformed JSON in catalogue file."""
        catalogue_file = tmp_path / "country_catalogue.json"
        catalogue_file.write_text("{ invalid json }")
        
        from plugin_video_mubi.resources.lib import coverage_optimizer
        
        with patch.object(coverage_optimizer, '_get_catalogue_path', return_value=str(catalogue_file)):
            result = coverage_optimizer.load_country_catalogue()
        
        assert result is None

    def test_load_country_catalogue_missing_films_key(self, tmp_path):
        """Test handling of catalogue missing 'films' key."""
        catalogue_file = tmp_path / "country_catalogue.json"
        catalogue_file.write_text(json.dumps({"invalid": "structure"}))
        
        from plugin_video_mubi.resources.lib import coverage_optimizer
        
        with patch.object(coverage_optimizer, '_get_catalogue_path', return_value=str(catalogue_file)):
            result = coverage_optimizer.load_country_catalogue()
        
        assert result is None

    def test_load_country_catalogue_success(self, sample_catalogue):
        """Test successful loading of country catalogue."""
        from plugin_video_mubi.resources.lib import coverage_optimizer
        
        with patch.object(coverage_optimizer, '_get_catalogue_path', return_value=sample_catalogue):
            result = coverage_optimizer.load_country_catalogue()
        
        assert result is not None
        assert 'films' in result
        assert len(result['films']) == 6
