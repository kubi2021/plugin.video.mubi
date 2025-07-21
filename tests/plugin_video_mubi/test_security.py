"""
Level 2 Security Test Suite for MUBI Kodi Plugin

Level 2 (Filesystem Safety) Focus:
- Filename sanitization for cross-platform compatibility
- Path traversal prevention
- Control character protection
- Windows reserved name handling

This module tests ONLY Level 2 security concerns relevant to local media consumption.
It does NOT test web security concerns (XSS, SQL injection, SSRF) as those are not
relevant for Kodi plugins running in trusted local environments.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Import the modules we want to test
from plugin_video_mubi.resources.lib.film import Film
from plugin_video_mubi.resources.lib.metadata import Metadata


class TestLevel2FilesystemSecurity:
    """Test Level 2 filesystem safety - the only security level relevant for Kodi plugins."""

    def test_filename_sanitization_prevents_path_traversal(self):
        """Test that filename sanitization prevents path traversal attacks."""
        # Arrange
        metadata = Metadata(
            title="Test Movie",
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="Test plot",
            plotoutline="Test outline",
            originaltitle="Test Movie",
            rating=7.0,
            votes=100,
            duration=120,
            country=["Test"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="",
            image="",
            mpaa="",
            artwork_urls={},
            audio_languages=[],
            subtitle_languages=[],
            media_features=[]
        )

        # Test path traversal attempts
        malicious_titles = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "Movie/../../../secret",
            "Movie\\..\\..\\..\\secret"
        ]

        for malicious_title in malicious_titles:
            # Act
            film = Film("123", malicious_title, "", "", metadata)
            sanitized_name = film.get_sanitized_folder_name()

            # Assert
            assert ".." not in sanitized_name, f"Path traversal not prevented: {sanitized_name}"
            assert "/" not in sanitized_name, f"Forward slash not removed: {sanitized_name}"
            assert "\\" not in sanitized_name, f"Backslash not removed: {sanitized_name}"

    def test_filename_sanitization_removes_dangerous_characters(self):
        """Test that dangerous filesystem characters are removed."""
        # Arrange
        metadata = Metadata(
            title="Test Movie",
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="Test plot",
            plotoutline="Test outline",
            originaltitle="Test Movie",
            rating=7.0,
            votes=100,
            duration=120,
            country=["Test"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="",
            image="",
            mpaa="",
            artwork_urls={},
            audio_languages=[],
            subtitle_languages=[],
            media_features=[]
        )

        # Test dangerous characters (Level 2 filesystem safety)
        dangerous_title = 'Movie<>:"/\\|?*'
        
        # Act
        film = Film("123", dangerous_title, "", "", metadata)
        sanitized_name = film.get_sanitized_folder_name()

        # Assert - dangerous characters should be removed
        dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in dangerous_chars:
            assert char not in sanitized_name, f"Dangerous character not removed: {char}"

    def test_filename_sanitization_preserves_safe_characters(self):
        """Test that safe characters are preserved for good user experience."""
        # Arrange
        metadata = Metadata(
            title="Test Movie",
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="Test plot",
            plotoutline="Test outline",
            originaltitle="Test Movie",
            rating=7.0,
            votes=100,
            duration=120,
            country=["Test"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="",
            image="",
            mpaa="",
            artwork_urls={},
            audio_languages=[],
            subtitle_languages=[],
            media_features=[]
        )

        # Test safe characters that should be preserved (Level 2 user experience)
        safe_title = "Movie & Co: What's Up! (2023) - Director's Cut"
        
        # Act
        film = Film("123", safe_title, "", "", metadata)
        sanitized_name = film.get_sanitized_folder_name()

        # Assert - safe characters should be preserved
        assert "&" in sanitized_name, "Ampersand should be preserved"
        assert "'" in sanitized_name, "Apostrophe should be preserved"
        assert "!" in sanitized_name, "Exclamation should be preserved"
        assert "(" in sanitized_name, "Parentheses should be preserved"
        assert ")" in sanitized_name, "Parentheses should be preserved"
        assert "-" in sanitized_name, "Hyphen should be preserved"

    def test_control_character_protection(self):
        """Test that control characters are handled safely."""
        # Arrange
        metadata = Metadata(
            title="Test Movie",
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="Test plot",
            plotoutline="Test outline",
            originaltitle="Test Movie",
            rating=7.0,
            votes=100,
            duration=120,
            country=["Test"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="",
            image="",
            mpaa="",
            artwork_urls={},
            audio_languages=[],
            subtitle_languages=[],
            media_features=[]
        )

        # Test control characters
        control_title = "Movie\x00\x01\x02\x03\x04\x05"
        
        # Act
        film = Film("123", control_title, "", "", metadata)
        sanitized_name = film.get_sanitized_folder_name()

        # Assert - control characters should be removed or handled safely
        assert "\x00" not in sanitized_name, "Null byte should be removed"
        assert len(sanitized_name) > 0, "Should not result in empty filename"

    def test_windows_reserved_names_handling(self):
        """Test that Windows reserved names are handled safely."""
        # Arrange
        metadata = Metadata(
            title="Test Movie",
            year="2023",
            director=["Test Director"],
            genre=["Drama"],
            plot="Test plot",
            plotoutline="Test outline",
            originaltitle="Test Movie",
            rating=7.0,
            votes=100,
            duration=120,
            country=["Test"],
            castandrole="Test Actor",
            dateadded="2023-01-01",
            trailer="",
            image="",
            mpaa="",
            artwork_urls={},
            audio_languages=[],
            subtitle_languages=[],
            media_features=[]
        )

        # Test Windows reserved names
        reserved_names = ["CON", "PRN", "AUX", "COM1", "LPT1"]
        
        for reserved_name in reserved_names:
            # Act
            film = Film("123", reserved_name, "", "", metadata)
            sanitized_name = film.get_sanitized_folder_name()

            # Assert - should not be exactly a reserved name
            assert sanitized_name.upper() != reserved_name, f"Reserved name not handled: {reserved_name}"
            assert len(sanitized_name) > 0, "Should not result in empty filename"


# Note: We deliberately DO NOT test the following as they are beyond Level 2:
# - XSS prevention (not relevant for local Kodi plugins)
# - SQL injection (no SQL database in this context)
# - SSRF attacks (not relevant for local media consumption)
# - Authentication bypass (handled by MUBI API, not our concern)
# - Complex injection attacks (over-engineered for this use case)
#
# Level 2 focuses on filesystem safety and user experience, which is exactly
# what these tests cover.
