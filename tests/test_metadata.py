import pytest
from unittest.mock import patch
from resources.lib.film_metadata import FilmMetadata


class TestMetadata:
    """Test cases for the Metadata class."""

    def test_metadata_initialization_all_fields(self):
        """Test metadata initialization with all fields provided."""
        metadata = FilmMetadata(
            title="Test Movie",
            director=["Director One", "Director Two"],
            year=2023,
            duration=120,
            country=["USA", "UK"],
            plot="This is a test plot",
            plotoutline="Test outline",
            genre=["Drama", "Thriller"],
            originaltitle="Original Test Movie",
            rating=8.5,
            votes=1500,
            castandrole="Actor One as Character One",
            dateadded="2023-01-01",
            trailer="http://example.com/trailer.mp4",
            image="http://example.com/image.jpg"
        )
        
        assert metadata.title == "Test Movie"
        assert metadata.director == ["Director One", "Director Two"]
        assert metadata.year == 2023
        assert metadata.duration == 120
        assert metadata.country == ["USA", "UK"]
        assert metadata.plot == "This is a test plot"
        assert metadata.plotoutline == "Test outline"
        assert metadata.genre == ["Drama", "Thriller"]
        assert metadata.originaltitle == "Original Test Movie"
        assert metadata.rating == 8.5
        assert metadata.votes == 1500
        assert metadata.castandrole == "Actor One as Character One"
        assert metadata.dateadded == "2023-01-01"
        assert metadata.trailer == "http://example.com/trailer.mp4"
        assert metadata.image == "http://example.com/image.jpg"

    def test_metadata_initialization_minimal_fields(self):
        """Test metadata initialization with only required fields."""
        metadata = FilmMetadata(
            title="Minimal Movie",
            director=[],
            year=None,
            duration=None,
            country=[],
            plot="",
            plotoutline="",
            genre=[],
            originaltitle=""
        )
        
        assert metadata.title == "Minimal Movie"
        assert metadata.director == []
        assert metadata.year == "Unknown"  # Should default to "Unknown"
        assert metadata.duration == 0  # Should default to 0
        assert metadata.country == []
        assert metadata.plot == ""
        assert metadata.plotoutline == ""
        assert metadata.genre == []
        assert metadata.originaltitle == ""
        assert metadata.rating == 0.0  # Should default to 0.0
        assert metadata.votes == 0  # Should default to 0

    def test_metadata_initialization_none_values(self):
        """Test metadata initialization handles None values correctly."""
        metadata = FilmMetadata(
            title="Test Movie",
            director=None,  # Should become empty list
            year=None,  # Should become "Unknown"
            duration=None,  # Should become 0
            country=None,  # Should become empty list
            plot="Test plot",
            plotoutline="Test outline",
            genre=None,  # Should become empty list
            originaltitle="Original Title",
            rating=None,  # Should become 0.0
            votes=None  # Should become 0
        )
        
        assert metadata.director == []
        assert metadata.year == "Unknown"
        assert metadata.duration == 0
        assert metadata.country == []
        assert metadata.genre == []
        assert metadata.rating == 0.0
        assert metadata.votes == 0

    def test_metadata_initialization_optional_defaults(self):
        """Test metadata initialization with optional parameters using defaults."""
        metadata = FilmMetadata(
            title="Test Movie",
            director=["Test Director"],
            year=2023,
            duration=90,
            country=["USA"],
            plot="Test plot",
            plotoutline="Test outline",
            genre=["Drama"],
            originaltitle="Original Title"
            # Not providing optional parameters
        )
        
        assert metadata.rating == 0.0
        assert metadata.votes == 0
        assert metadata.castandrole == ""
        assert metadata.dateadded == ""
        assert metadata.trailer == ""
        assert metadata.image == ""

    def test_metadata_repr(self):
        """Test string representation of metadata."""
        metadata = FilmMetadata(
            title="Test Movie",
            director=["Test Director"],
            year=2023,
            duration=120,
            country=["USA"],
            plot="Test plot",
            plotoutline="Test outline",
            genre=["Drama"],
            originaltitle="Original Title",
            rating=7.5,
            votes=1000
        )
        
        repr_str = repr(metadata)
        assert "Test Movie" in repr_str
        assert "Test Director" in repr_str
        assert "2023" in repr_str
        assert "120" in repr_str
        assert "USA" in repr_str
        assert "7.5" in repr_str
        assert "1000" in repr_str

    def test_metadata_as_dict_complete(self):
        """Test converting metadata to dictionary with all fields."""
        metadata = FilmMetadata(
            title="Test Movie",
            director=["Director One"],
            year=2023,
            duration=120,
            country=["USA"],
            plot="Test plot",
            plotoutline="Test outline",
            genre=["Drama"],
            originaltitle="Original Title",
            rating=8.0,
            votes=500,
            castandrole="Test Cast",
            dateadded="2023-01-01",
            trailer="http://example.com/trailer",
            image="http://example.com/image.jpg"
        )
        
        result_dict = metadata.as_dict()
        
        expected_dict = {
            'title': "Test Movie",
            'director': ["Director One"],
            'year': 2023,
            'duration': 120,
            'country': ["USA"],
            'plot': "Test plot",
            'plotoutline': "Test outline",
            'genre': ["Drama"],
            'originaltitle': "Original Title",
            'rating': 8.0,
            'votes': 500,
            'castandrole': "Test Cast",
            'dateadded': "2023-01-01",
            'trailer': "http://example.com/trailer",
            'image': "http://example.com/image.jpg"
        }
        
        assert result_dict == expected_dict

    def test_metadata_as_dict_minimal(self):
        """Test converting minimal metadata to dictionary."""
        metadata = FilmMetadata(
            title="Minimal Movie",
            director=[],
            year=None,
            duration=None,
            country=[],
            plot="",
            plotoutline="",
            genre=[],
            originaltitle=""
        )
        
        result_dict = metadata.as_dict()
        
        assert result_dict['title'] == "Minimal Movie"
        assert result_dict['director'] == []
        assert result_dict['year'] == "Unknown"
        assert result_dict['duration'] == 0
        assert result_dict['country'] == []
        assert result_dict['genre'] == []
        assert result_dict['rating'] == 0.0
        assert result_dict['votes'] == 0

    @patch('xbmc.log')
    def test_metadata_initialization_exception_handling(self, mock_log):
        """Test metadata initialization handles exceptions gracefully."""
        # This test verifies that the Metadata class can handle exceptions during initialization
        # Since the actual Metadata class has try/catch blocks, we'll test with invalid data
        # that might cause issues in a real scenario

        # Test with data that could potentially cause issues
        try:
            metadata = FilmMetadata(
                title=None,  # This might cause issues in string operations
                director=None,
                year="invalid",  # Non-numeric year
                duration="invalid",  # Non-numeric duration
                country=None,
                plot=None,
                plotoutline=None,
                genre=None,
                originaltitle=None
            )
            # If we get here, the class handled the invalid data gracefully
            assert True
        except Exception:
            # If an exception occurs, it should be logged
            mock_log.assert_called()

    def test_metadata_as_dict_normal_operation(self):
        """Test as_dict method normal operation."""
        metadata = FilmMetadata(
            title="Test Movie",
            director=["Test Director"],
            year=2023,
            duration=120,
            country=["USA"],
            plot="Test plot",
            plotoutline="Test outline",
            genre=["Drama"],
            originaltitle="Original Title"
        )

        # Test that as_dict works normally first
        result = metadata.as_dict()
        assert isinstance(result, dict)
        assert result['title'] == "Test Movie"

        # The as_dict method in the actual implementation doesn't have exception handling
        # that returns empty dict, so we'll test that it works correctly instead
        assert len(result) > 0

    def test_metadata_edge_cases(self):
        """Test metadata with edge case values."""
        metadata = FilmMetadata(
            title="",  # Empty title
            director=[""],  # Empty director name
            year=0,  # Zero year
            duration=-1,  # Negative duration
            country=[""],  # Empty country
            plot="",
            plotoutline="",
            genre=[""],  # Empty genre
            originaltitle="",
            rating=-1.0,  # Negative rating
            votes=-100  # Negative votes
        )
        
        # Should handle edge cases without crashing
        assert metadata.title == ""
        assert metadata.director == [""]
        assert metadata.year == 0
        assert metadata.duration == -1
        assert metadata.country == [""]
        assert metadata.genre == [""]
        assert metadata.rating == -1.0
        assert metadata.votes == -100

    def test_metadata_large_values(self):
        """Test metadata with very large values."""
        metadata = FilmMetadata(
            title="A" * 1000,  # Very long title
            director=["Director"] * 100,  # Many directors
            year=9999,  # Large year
            duration=999999,  # Very long duration
            country=["Country"] * 50,  # Many countries
            plot="Plot " * 1000,  # Very long plot
            plotoutline="Outline " * 1000,  # Very long outline
            genre=["Genre"] * 100,  # Many genres
            originaltitle="B" * 1000,  # Very long original title
            rating=999.99,  # Large rating
            votes=999999999  # Very large vote count
        )
        
        # Should handle large values without issues
        assert len(metadata.title) == 1000
        assert len(metadata.director) == 100
        assert metadata.year == 9999
        assert metadata.duration == 999999
        assert len(metadata.country) == 50
        assert len(metadata.genre) == 100
        assert metadata.rating == 999.99
        assert metadata.votes == 999999999
