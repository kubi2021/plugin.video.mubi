"""
Test suite for metadata_utils module.

Dependencies:
pip install pytest pytest-mock

Framework: pytest
Coverage: ExternalMetadataResult, TitleNormalizer, RetryStrategy
"""

import pytest
from unittest.mock import MagicMock, patch
import requests

from backend.metadata_utils import ExternalMetadataResult, TitleNormalizer, RetryStrategy


class TestExternalMetadataResult:
    """Test cases for the ExternalMetadataResult dataclass."""

    def test_default_initialization(self):
        """Test default values are set correctly."""
        result = ExternalMetadataResult()
        
        assert result.imdb_id is None
        assert result.tmdb_id is None
        assert result.success is False
        assert result.source_provider == ""
        assert result.match_score == 0

    def test_success_initialization(self):
        """Test successful result initialization."""
        result = ExternalMetadataResult(
            imdb_id="tt1234567",
            tmdb_id="12345",
            success=True,
            source_provider="tmdb",
            vote_average=8.5,
            vote_count=1000,
            match_score=95
        )
        
        assert result.imdb_id == "tt1234567"
        assert result.tmdb_id == "12345"
        assert result.success is True
        assert result.vote_average == 8.5
        assert result.vote_count == 1000
        assert result.match_score == 95

    def test_failure_initialization(self):
        """Test failure result with error message."""
        result = ExternalMetadataResult(
            success=False,
            error_message="Movie not found"
        )
        
        assert result.success is False
        assert result.error_message == "Movie not found"


class TestTitleNormalizer:
    """Test cases for the TitleNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        return TitleNormalizer()

    def test_normalize_title_removes_and(self, normalizer):
        """Test that 'and' and '&' are removed."""
        assert normalizer.normalize_title("Romeo and Juliet") == "Romeo Juliet"
        assert normalizer.normalize_title("Romeo & Juliet") == "Romeo Juliet"

    def test_normalize_title_collapses_whitespace(self, normalizer):
        """Test that multiple spaces are collapsed."""
        assert normalizer.normalize_title("The   Quick   Brown") == "The Quick Brown"

    def test_generate_alternative_spellings_british_american(self, normalizer):
        """Test British/American spelling variations."""
        alternatives = normalizer.generate_alternative_spellings("The Color Purple")
        assert "The Colour Purple" in alternatives

    def test_generate_alternative_spellings_case_preserved(self, normalizer):
        """Test that case is preserved in alternatives."""
        alternatives = normalizer.generate_alternative_spellings("COLOR")
        assert "COLOUR" in alternatives

    def test_generate_alternative_spellings_no_match(self, normalizer):
        """Test no alternatives when no variations found."""
        alternatives = normalizer.generate_alternative_spellings("The Matrix")
        assert alternatives == []

    def test_clean_title_removes_directors_cut(self, normalizer):
        """Test that Director's Cut suffixes are removed."""
        assert normalizer.clean_title("Blade Runner (Director's Cut)") == "Blade Runner"
        assert normalizer.clean_title("Apocalypse Now Redux") == "Apocalypse Now"

    def test_clean_title_removes_remastered(self, normalizer):
        """Test that Remastered/Restored suffixes are removed."""
        assert normalizer.clean_title("2001: A Space Odyssey (Restored)") == "2001: A Space Odyssey"
        assert normalizer.clean_title("Jaws (Remastered)") == "Jaws"

    def test_clean_title_removes_mv_tag(self, normalizer):
        """Test that [MV] music video tag is removed."""
        assert normalizer.clean_title("Song Title [MV]") == "Song Title"

    def test_generate_title_variants_includes_original(self, normalizer):
        """Test that original title is included in variants."""
        variants = normalizer.generate_title_variants("The Matrix")
        assert "The Matrix" in variants
        # Original title should be first
        assert variants[0] == "The Matrix"

    def test_generate_title_variants_includes_original_title(self, normalizer):
        """Test that original_title parameter is included if different."""
        variants = normalizer.generate_title_variants(
            "The Intouchables",
            original_title="Intouchables"
        )
        assert "The Intouchables" in variants
        assert "Intouchables" in variants

    def test_generate_title_variants_complete_flow(self, normalizer):
        """Test full variant generation with cleaning and alternatives."""
        variants = normalizer.generate_title_variants(
            "The Color Purple (Director's Cut)"
        )
        # Should contain: original, cleaned, color->colour variant
        assert "The Color Purple (Director's Cut)" in variants
        assert "The Color Purple" in variants
        assert "The Colour Purple" in variants


class TestRetryStrategy:
    """Test cases for the RetryStrategy class."""

    def test_initialization_defaults(self):
        """Test default retry parameters."""
        strategy = RetryStrategy()
        assert strategy.max_retries == 10
        assert strategy.initial_backoff == 1.0
        assert strategy.multiplier == 1.5

    def test_initialization_custom(self):
        """Test custom retry parameters."""
        strategy = RetryStrategy(max_retries=5, initial_backoff=2.0, multiplier=2.0)
        assert strategy.max_retries == 5
        assert strategy.initial_backoff == 2.0
        assert strategy.multiplier == 2.0

    def test_execute_success_first_try(self):
        """Test successful execution on first attempt."""
        strategy = RetryStrategy()
        
        mock_func = MagicMock(return_value=ExternalMetadataResult(
            success=True,
            imdb_id="tt1234567"
        ))
        
        result = strategy.execute(mock_func, "Test Movie")
        
        assert result.success is True
        assert result.imdb_id == "tt1234567"
        assert mock_func.call_count == 1

    def test_execute_returns_failure_on_not_found(self):
        """Test that 404 returns immediately without retry."""
        strategy = RetryStrategy(max_retries=3)
        
        mock_func = MagicMock(return_value=ExternalMetadataResult(
            success=False,
            error_message="Title not found (404)"
        ))
        
        result = strategy.execute(mock_func, "Unknown Movie")
        
        assert result.success is False
        assert "404" in result.error_message
        assert mock_func.call_count == 1  # No retries for 404

    @patch('time.sleep')
    def test_execute_retries_on_429(self, mock_sleep):
        """Test that 429 triggers retry with backoff."""
        strategy = RetryStrategy(max_retries=3, initial_backoff=1.0)
        
        # First call raises 429, second succeeds
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        
        success_result = ExternalMetadataResult(success=True, imdb_id="tt1234567")
        
        mock_func = MagicMock(side_effect=[http_error, success_result])
        
        result = strategy.execute(mock_func, "Rate Limited Movie")
        
        assert result.success is True
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once()

    @patch('time.sleep')
    def test_execute_respects_retry_after_header(self, mock_sleep):
        """Test that Retry-After header is respected."""
        strategy = RetryStrategy(max_retries=3)
        
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "5"}
        
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        
        success_result = ExternalMetadataResult(success=True, imdb_id="tt1234567")
        mock_func = MagicMock(side_effect=[http_error, success_result])
        
        result = strategy.execute(mock_func, "Movie")
        
        # Should wait 5 + 1 = 6 seconds (buffer added)
        mock_sleep.assert_called_once_with(6.0)

    def test_execute_max_retries_exhausted(self):
        """Test that max retries returns error."""
        strategy = RetryStrategy(max_retries=2)
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}
        
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        
        # Both attempts fail with 500
        mock_func = MagicMock(side_effect=[http_error, http_error])
        
        with patch('time.sleep'):
            result = strategy.execute(mock_func, "Server Error Movie")
        
        assert result.success is False
        assert "Max retries" in result.error_message

    def test_execute_handles_generic_exception(self):
        """Test that generic exceptions are handled gracefully."""
        strategy = RetryStrategy()
        
        mock_func = MagicMock(side_effect=ConnectionError("Network failure"))
        
        result = strategy.execute(mock_func, "Network Error Movie")
        
        assert result.success is False
        assert "Network failure" in result.error_message
