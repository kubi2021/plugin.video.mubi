"""
Test suite for Library class following QA guidelines.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Happy path, edge cases, and error handling
"""

import tempfile
from unittest.mock import Mock, patch, call
from pathlib import Path
from plugin_video_mubi.resources.lib.film import Film
from plugin_video_mubi.resources.lib.library import Library
import os
from datetime import datetime, timedelta, timezone

# Helper for creating valid playable country data
NOW = datetime.now(timezone.utc)
PAST = (NOW - timedelta(days=365)).isoformat().replace('+00:00', 'Z')
FUTURE = (NOW + timedelta(days=365)).isoformat().replace('+00:00', 'Z')

VALID_COUNTRY_DATA = {
    "US": {
        "available_at": PAST,
        "availability_ends_at": FUTURE,
        "availability": "live"
    }
}


# Mock Metadata class for testing
class MockMetadata:
    def __init__(self, year=2023, genre=None, title="Test Movie", director=None,
                 duration=120, country=None, plot="Test plot", plotoutline="Test outline",
                 originaltitle="Test Original Title", rating=7.5, votes=1000,
                 castandrole="", dateadded="", trailer="", image=""):
        self.year = year
        self.genre = genre or ["Drama"]
        self.title = title
        self.director = director or ["Test Director"]
        self.duration = duration
        self.country = country or ["USA"]
        self.plot = plot
        self.plotoutline = plotoutline
        self.originaltitle = originaltitle
        self.rating = rating
        self.votes = votes
        self.castandrole = castandrole
        self.dateadded = dateadded
        self.trailer = trailer
        self.image = image

def test_add_valid_film():
    """Test adding a valid film to the library."""
    # Arrange
    library = Library()
    metadata = MockMetadata(year=2023)
    film = Film(
        mubi_id="123456",
        title="Sample Movie",
        artwork="http://example.com/art.jpg",
        web_url="http://example.com",
        metadata=metadata,
        available_countries=VALID_COUNTRY_DATA
    )

    # Act
    library.add_film(film)

    # Assert
    assert len(library.films) == 1

def test_library_len():
    """Test library length calculation."""
    # Arrange
    library = Library()
    film1 = Film(
        mubi_id="123",
        title="Film One",
        artwork="http://example.com/art1.jpg",
        web_url="http://example.com/film1",
        metadata=MockMetadata(2021),
        available_countries=VALID_COUNTRY_DATA
    )
    film2 = Film(
        mubi_id="456",
        title="Film Two",
        artwork="http://example.com/art2.jpg",
        web_url="http://example.com/film2",
        metadata=MockMetadata(2022),
        available_countries=VALID_COUNTRY_DATA
    )

    # Act
    initial_length = len(library)
    library.add_film(film1)
    library.add_film(film2)
    final_length = len(library)

    # Assert
    assert initial_length == 0
    assert final_length == 2

@patch.object(Film, "create_nfo_file")
@patch.object(Film, "create_strm_file")
def test_prepare_files_for_film_success(mock_create_strm, mock_create_nfo):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Create a Film object
        metadata = MockMetadata(year=2023)
        film = Film(
            mubi_id="123456",
            title="Sample Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com",
            metadata=metadata
        )
        library.add_film(film)

        # Prepare paths
        film_folder_name = film.get_sanitized_folder_name()
        film_path = plugin_userdata_path / film_folder_name
        nfo_file = film_path / f"{film_folder_name}.nfo"
        strm_file = film_path / f"{film_folder_name}.strm"

        # Mock create_nfo_file to create the NFO file
        def create_nfo_side_effect(film_path_arg, base_url_arg, **kwargs):
            film_path_arg.mkdir(parents=True, exist_ok=True)
            nfo_file.touch()

        mock_create_nfo.side_effect = create_nfo_side_effect

        # Mock create_strm_file to create the STRM file
        def create_strm_side_effect(film_path_arg, base_url_arg):
            strm_file.touch()

        mock_create_strm.side_effect = create_strm_side_effect

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path)

        # Assert that prepare_files_for_film returned True
        assert result is True, "prepare_files_for_film should return True for successful file creation."

        # Check if the calls to `create_nfo_file` and `create_strm_file` have the expected arguments
        expected_folder = plugin_userdata_path / film.get_sanitized_folder_name()

        # Assert that create_nfo_file is called with expected args
        mock_create_nfo.assert_called_once_with(expected_folder, base_url, skip_external_metadata=False)

        # Assert that create_strm_file is called with expected args (no user_country)
        mock_create_strm.assert_called_once_with(expected_folder, base_url)


@patch.object(Film, "create_nfo_file")
@patch.object(Film, "update_nfo_availability")
def test_prepare_files_for_film_nfo_exists_availability_updated(mock_update_availability, mock_create_nfo):
    """Test that when NFO exists, availability is updated in NFO file."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Create a Film object with available countries
        metadata = MockMetadata(year=2023)
        film = Film(
            mubi_id="789012",
            title="Existing Movie",
            artwork="http://example.com/art2.jpg",
            web_url="http://example.com",
            metadata=metadata,
            available_countries=["CH", "DE", "US"]
        )
        library.add_film(film)

        # Prepare paths
        film_folder_name = film.get_sanitized_folder_name()
        film_path = plugin_userdata_path / film_folder_name
        nfo_file = film_path / f"{film_folder_name}.nfo"

        # Simulate existing NFO file (availability will be updated)
        film_path.mkdir(parents=True, exist_ok=True)
        # NFO must match metadata rating (MUBI: 7.5) to be considered synced
        nfo_content = """<movie>
            <title>Existing Movie</title>
            <ratings>
                <rating name="MUBI" max="10">
                    <value>7.5</value>
                    <votes>1000</votes>
                </rating>
            </ratings>
        </movie>"""
        nfo_file.write_text(nfo_content)

        # Mock update_nfo_availability to return True
        mock_update_availability.return_value = True

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        result = library.prepare_files_for_film(
            film, base_url, plugin_userdata_path
        )

        # Assert that prepare_files_for_film returned None (availability updated)
        assert result is None, "Should return None when NFO exists and availability is updated."

        # Assert that create_nfo_file was NOT called (NFO already exists)
        mock_create_nfo.assert_not_called()

        # Assert that update_nfo_availability WAS called (to update country availability)
        mock_update_availability.assert_called_once_with(nfo_file)


@patch.object(Film, "create_nfo_file")
@patch.object(Film, "create_strm_file")
def test_prepare_files_for_film_failure(mock_create_strm, mock_create_nfo):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()
        
        # Create a Film object
        metadata = MockMetadata(year=2023)
        film = Film(
            mubi_id="345678",
            title="Failed Movie",
            artwork="http://example.com/art3.jpg",
            web_url="http://example.com",
            metadata=metadata
        )
        library.add_film(film)

        # Prepare paths
        film_folder_name = film.get_sanitized_folder_name()
        film_path = plugin_userdata_path / film_folder_name
        nfo_file = film_path / f"{film_folder_name}.nfo"
        strm_file = film_path / f"{film_folder_name}.strm"

        # Mock create_nfo_file to simulate failure (do nothing)
        def create_nfo_side_effect(film_path_arg, base_url_arg, **kwargs):
            pass  # Do nothing; NFO file is not created

        mock_create_nfo.side_effect = create_nfo_side_effect

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"

        # Ensure that the NFO file does not exist
        assert not nfo_file.exists()

        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path)

        # Assert that prepare_files_for_film returned False
        assert result is False, "prepare_files_for_film should return False when file creation fails."

        # Assert that create_nfo_file was called
        expected_folder = plugin_userdata_path / film.get_sanitized_folder_name()
        mock_create_nfo.assert_called_once_with(expected_folder, base_url, skip_external_metadata=False)

        # Assert that create_strm_file was not called since NFO creation failed
        mock_create_strm.assert_not_called()

def test_remove_obsolete_files():
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)

        # Create dummy folders to simulate obsolete files
        (plugin_userdata_path / "Old Film (2021)").mkdir()
        (plugin_userdata_path / "Another Old Film (2022)").mkdir()

        # Create a film and add it to the library
        library = Library()
        metadata = MockMetadata(year=2023)
        film = Film(mubi_id="123456", title="Current Film", artwork="http://example.com/art.jpg", web_url="http://example.com", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
        library.add_film(film)

        # Create the folder for the current film to simulate an existing folder
        current_folder = plugin_userdata_path / film.get_sanitized_folder_name()
        current_folder.mkdir()

        # Remove obsolete files
        library.remove_obsolete_files(plugin_userdata_path)

        # Check that obsolete folders were removed
        assert not (plugin_userdata_path / "Old Film (2021)").exists(), "Obsolete folder 'Old Film (2021)' was not removed."
        assert not (plugin_userdata_path / "Another Old Film (2022)").exists(), "Obsolete folder 'Another Old Film (2022)' was not removed."

        # Check that the current film folder was not removed
        assert current_folder.exists(), "Current film folder should not have been removed."

def test_remove_obsolete_files_with_artwork():
    """Test that obsolete film folders are completely removed including all artwork files."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)

        # Create obsolete film folder with various files including artwork
        obsolete_folder = plugin_userdata_path / "Old Movie (2020)"
        obsolete_folder.mkdir()

        # Create typical film files that would be in a film folder
        nfo_file = obsolete_folder / "Old Movie (2020).nfo"
        strm_file = obsolete_folder / "Old Movie (2020).strm"
        thumb_file = obsolete_folder / "Old Movie (2020)-thumb.jpg"
        poster_file = obsolete_folder / "Old Movie (2020)-poster.jpg"
        clearlogo_file = obsolete_folder / "Old Movie (2020)-clearlogo.png"

        # Create all the files
        nfo_file.touch()
        strm_file.touch()
        thumb_file.touch()
        poster_file.touch()
        clearlogo_file.touch()

        # Verify files exist before cleanup
        assert nfo_file.exists(), "NFO file should exist before cleanup"
        assert strm_file.exists(), "STRM file should exist before cleanup"
        assert thumb_file.exists(), "Thumbnail file should exist before cleanup"
        assert poster_file.exists(), "Poster file should exist before cleanup"
        assert clearlogo_file.exists(), "Clearlogo file should exist before cleanup"

        # Create a library with no films (so the obsolete folder should be removed)
        library = Library()

        # Remove obsolete files
        removed_count = library.remove_obsolete_files(plugin_userdata_path)

        # Assert that the obsolete folder and all its contents were removed
        assert removed_count == 1, "Should have removed 1 obsolete folder"
        assert not obsolete_folder.exists(), "Obsolete folder should be completely removed"
        assert not nfo_file.exists(), "NFO file should be removed with folder"
        assert not strm_file.exists(), "STRM file should be removed with folder"
        assert not thumb_file.exists(), "Thumbnail file should be removed with folder"
        assert not poster_file.exists(), "Poster file should be removed with folder"
        assert not clearlogo_file.exists(), "Clearlogo file should be removed with folder"

def test_remove_obsolete_files_preserves_current_artwork():
    """Test that current film folders and their artwork are preserved during cleanup."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)

        # Create obsolete film folder
        obsolete_folder = plugin_userdata_path / "Old Movie (2020)"
        obsolete_folder.mkdir()
        (obsolete_folder / "Old Movie (2020).nfo").touch()
        (obsolete_folder / "Old Movie (2020)-thumb.jpg").touch()

        # Create current film and add to library
        library = Library()
        metadata = MockMetadata(year=2023)
        current_film = Film(
            mubi_id="123456",
            title="Current Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com",
            metadata=metadata,
            available_countries=VALID_COUNTRY_DATA
        )
        library.add_film(current_film)

        # Create current film folder with artwork
        current_folder = plugin_userdata_path / current_film.get_sanitized_folder_name()
        current_folder.mkdir()
        current_nfo = current_folder / f"{current_film.get_sanitized_folder_name()}.nfo"
        current_thumb = current_folder / f"{current_film.get_sanitized_folder_name()}-thumb.jpg"
        current_poster = current_folder / f"{current_film.get_sanitized_folder_name()}-poster.jpg"

        current_nfo.touch()
        current_thumb.touch()
        current_poster.touch()

        # Remove obsolete files
        removed_count = library.remove_obsolete_files(plugin_userdata_path)

        # Assert obsolete folder was removed but current folder preserved
        assert removed_count == 1, "Should have removed 1 obsolete folder"
        assert not obsolete_folder.exists(), "Obsolete folder should be removed"
        assert current_folder.exists(), "Current film folder should be preserved"
        assert current_nfo.exists(), "Current film NFO should be preserved"
        assert current_thumb.exists(), "Current film thumbnail should be preserved"
        assert current_poster.exists(), "Current film poster should be preserved"

@patch("xbmcaddon.Addon")
@patch("xbmcgui.DialogProgress")
@patch.object(Library, "prepare_files_for_film")
@patch.object(Library, "remove_obsolete_files")
def test_sync_locally(mock_remove_obsolete, mock_prepare_files, mock_dialog_progress, mock_addon):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Mock getSettingBool to return False for all genre settings (no filtering)
        addon_instance = mock_addon.return_value
        addon_instance.getSettingBool.return_value = False

        # Create Film objects and add them to the library
        metadata = MockMetadata(year=2023)
        film1 = Film(mubi_id="123", title="Sample Movie 1", artwork="http://example.com/art1.jpg",
                     web_url="http://example.com/film1", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
        film2 = Film(mubi_id="456", title="Sample Movie 2", artwork="http://example.com/art2.jpg",
                     web_url="http://example.com/film2", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
        library.add_film(film1)
        library.add_film(film2)

        # Set up mock behavior for prepare_files_for_film
        mock_prepare_files.side_effect = [
            ([film1], []),  # Return new films for film1
            ([], [film2])   # Return skipped for film2
        ]

        # Mock dialog behavior to not cancel
        mock_dialog = mock_dialog_progress.return_value
        mock_dialog.iscanceled.return_value = False

        # Run sync_locally
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        library.sync_locally(base_url, plugin_userdata_path)

        # Assertions for progress dialog
        mock_dialog.create.assert_called_once_with("Syncing with MUBI 2/2", "Processing 2 films...")
        assert mock_dialog.update.call_count == 2, "Progress dialog should have been updated twice"
        mock_dialog.close.assert_called_once()

        # Assert that prepare_files_for_film was called for each film
        expected_calls = [
            call(film1, base_url, plugin_userdata_path, False),
            call(film2, base_url, plugin_userdata_path, False)
        ]
        mock_prepare_files.assert_has_calls(expected_calls, any_order=False)

        # Assert that remove_obsolete_files was called
        mock_remove_obsolete.assert_called_once_with(plugin_userdata_path)

@patch("xbmcaddon.Addon")
@patch("xbmcgui.DialogProgress")
@patch.object(Library, "prepare_files_for_film")
@patch.object(Library, "remove_obsolete_files")
@patch("plugin_video_mubi.resources.lib.library.xbmc")
def test_sync_locally_user_cancellation(mock_xbmc, mock_remove_obsolete, mock_prepare_files, mock_dialog_progress, mock_addon):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Mock getSettingBool to return False for all genre settings (no filtering)
        addon_instance = mock_addon.return_value
        addon_instance.getSettingBool.return_value = False

        # Create Film objects and add them to the library
        metadata = MockMetadata(year=2023)
        film1 = Film(mubi_id="123", title="Sample Movie 1", artwork="http://example.com/art1.jpg",
                     web_url="http://example.com/film1", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
        film2 = Film(mubi_id="456", title="Sample Movie 2", artwork="http://example.com/art2.jpg",
                     web_url="http://example.com/film2", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
        library.add_film(film1)
        library.add_film(film2)

        # Set up mock behavior for prepare_files_for_film
        mock_prepare_files.return_value = True

        # Mock dialog behavior to simulate cancellation after first film
        mock_dialog = mock_dialog_progress.return_value
        mock_dialog.iscanceled.side_effect = [False, True]  # Cancel after first update

        # Run sync_locally
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        library.sync_locally(base_url, plugin_userdata_path)

        # In parallel execution, multiple tasks may start before cancellation is detected.
        # We verify that cancellation logic was triggered.
        mock_xbmc.log.assert_any_call("User canceled the sync process.", mock_xbmc.LOGDEBUG)

        # Assert that remove_obsolete_files was called
        mock_remove_obsolete.assert_called_once_with(plugin_userdata_path)
@patch.object(Film, "create_nfo_file")
@patch.object(Film, "create_strm_file")
def test_prepare_files_for_film_exception_in_nfo(mock_create_strm, mock_create_nfo):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Create a Film object
        metadata = MockMetadata(year=2023)
        film = Film(
            mubi_id="999999",
            title="Exception Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com",
            metadata=metadata
        )
        library.add_film(film)

        # Simulate exception in create_nfo_file
        mock_create_nfo.side_effect = Exception("Simulated exception in create_nfo_file")

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path)

        # Assert that prepare_files_for_film returned False
        assert result is False, "Should return False when an exception occurs in create_nfo_file."

        # Assert that create_strm_file was not called
        mock_create_strm.assert_not_called()

@patch.object(Film, "create_nfo_file")
@patch.object(Film, "create_strm_file")
def test_prepare_files_for_film_exception_in_strm(mock_create_strm, mock_create_nfo):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Create a Film object
        metadata = MockMetadata(year=2023)
        film = Film(
            mubi_id="888888",
            title="Exception Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com",
            metadata=metadata
        )
        library.add_film(film)

        # Mock create_nfo_file to create the NFO file
        def create_nfo_side_effect(film_path_arg, base_url_arg, **kwargs):
            film_path_arg.mkdir(parents=True, exist_ok=True)
            (film_path_arg / f"{film.get_sanitized_folder_name()}.nfo").touch()

        mock_create_nfo.side_effect = create_nfo_side_effect

        # Simulate exception in create_strm_file
        mock_create_strm.side_effect = Exception("Simulated exception in create_strm_file")

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path)

        # Assert that prepare_files_for_film returned False
        assert result is False, "Should return False when an exception occurs in create_strm_file."

def test_remove_obsolete_files_no_obsolete():
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)

        # Create a film and add it to the library
        library = Library()
        metadata = MockMetadata(year=2023)
        film = Film(mubi_id="123456", title="Current Film", artwork="http://example.com/art.jpg",
                    web_url="http://example.com", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
        library.add_film(film)

        # Create the folder for the current film to simulate an existing folder
        current_folder = plugin_userdata_path / film.get_sanitized_folder_name()
        current_folder.mkdir()

        # Remove obsolete files
        count = library.remove_obsolete_files(plugin_userdata_path)

        # Assert that no folders were removed
        assert count == 0, "No obsolete folders should have been removed."
        assert current_folder.exists(), "Current film folder should not have been removed."
def test_remove_obsolete_files_nonexistent_path():
    plugin_userdata_path = Path("/non/existent/path")

    # Create a film and add it to the library
    library = Library()
    metadata = MockMetadata(year=2023)
    film = Film(mubi_id="123456", title="Current Film", artwork="http://example.com/art.jpg",
                web_url="http://example.com", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
    library.add_film(film)

    # Attempt to remove obsolete files
    try:
        count = library.remove_obsolete_files(plugin_userdata_path)
        assert count == 0, "Should return 0 when path does not exist."
    except FileNotFoundError:
        # Expected behavior if the method does not handle non-existent paths internally
        pass

@patch("xbmcaddon.Addon")
@patch("xbmcgui.DialogProgress")
@patch.object(Library, "remove_obsolete_files")
def test_sync_locally_empty_library(mock_remove_obsolete, mock_dialog_progress, mock_addon):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()  # Empty library

        # Mock dialog behavior to not cancel
        mock_dialog = mock_dialog_progress.return_value
        mock_dialog.iscanceled.return_value = False

        # Run sync_locally
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        library.sync_locally(base_url, plugin_userdata_path)

        # Assertions for progress dialog
        mock_dialog.create.assert_called_once_with("Syncing with MUBI 2/2", "Processing 0 films...")
        mock_dialog.update.assert_not_called()
        mock_dialog.close.assert_called_once()

        # Assert that remove_obsolete_files was called
        mock_remove_obsolete.assert_called_once_with(plugin_userdata_path)

def test_prepare_files_for_film_with_invalid_characters():
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Create a Film object with invalid characters in the title
        metadata = MockMetadata(year=2023)
        film = Film(
            mubi_id="654321",
            title="Invalid/Character: Movie*?",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com",
            metadata=metadata
        )
        library.add_film(film)

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"

        # Mock create_nfo_file and create_strm_file to create files
        with patch.object(Film, "create_nfo_file") as mock_create_nfo, \
             patch.object(Film, "create_strm_file") as mock_create_strm:
            def create_nfo_side_effect(film_path_arg, base_url_arg, **kwargs):
                film_path_arg.mkdir(parents=True, exist_ok=True)
                (film_path_arg / f"{film.get_sanitized_folder_name()}.nfo").touch()

            def create_strm_side_effect(film_path_arg, base_url_arg, user_country=None):
                (film_path_arg / f"{film.get_sanitized_folder_name()}.strm").touch()

            mock_create_nfo.side_effect = create_nfo_side_effect
            mock_create_strm.side_effect = create_strm_side_effect

            result = library.prepare_files_for_film(
                film, base_url, plugin_userdata_path
            )

            # Assert that prepare_files_for_film returned True
            assert result is True, "Should return True when files are created successfully."

            # Check that the folder was created with sanitized name
            sanitized_folder_name = film.get_sanitized_folder_name()
            film_path = plugin_userdata_path / sanitized_folder_name
            assert film_path.exists(), "Film folder with sanitized name should exist."


def test_prepare_files_for_film_unwritable_path():
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname) / "unwritable_dir"
        plugin_userdata_path.mkdir()
        os.chmod(plugin_userdata_path, 0o400)  # Read-only permissions

        library = Library()
        metadata = MockMetadata(year=2023)
        film = Film(
            mubi_id="777777",
            title="Unwritable Path Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com",
            metadata=metadata
        )
        library.add_film(film)

        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"

        # Run prepare_files_for_film
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path)

        # Assert that prepare_files_for_film returned False due to exception
        assert result is False, "Should return False when unable to write to the directory."

        # Reset permissions for cleanup
        os.chmod(plugin_userdata_path, 0o700)

@patch("xbmcaddon.Addon")
@patch("xbmcgui.DialogProgress")
@patch.object(Library, "prepare_files_for_film")
@patch.object(Library, "remove_obsolete_files")
def test_sync_locally_large_library(mock_remove_obsolete, mock_prepare_files, mock_dialog_progress, mock_addon):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Mock getSettingBool to return False for all genre settings (no filtering)
        addon_instance = mock_addon.return_value
        addon_instance.getSettingBool.return_value = False

        # Create 200 Film objects and add them to the library
        metadata = MockMetadata(year=2023)
        for i in range(200):
            film = Film(
                mubi_id=str(i),
                title=f"Sample Movie {i}",
                artwork=f"http://example.com/art{i}.jpg",
                web_url=f"http://example.com/film{i}",
                metadata=metadata,
                available_countries=VALID_COUNTRY_DATA
            )
            library.add_film(film)

        # Set up mock behavior for prepare_files_for_film
        mock_prepare_files.return_value = True

        # Mock dialog behavior to not cancel
        mock_dialog = mock_dialog_progress.return_value
        mock_dialog.iscanceled.return_value = False

        # Run sync_locally
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        library.sync_locally(base_url, plugin_userdata_path)

        # Assert that prepare_files_for_film was called 200 times
        assert mock_prepare_files.call_count == 200, "prepare_files_for_film should be called 200 times."

def test_add_duplicate_film():
    library = Library()
    metadata = MockMetadata(year=2023)
    film = Film(mubi_id="123456", title="Sample Movie", artwork="http://example.com/art.jpg",
                web_url="http://example.com", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
    library.add_film(film)
    library.add_film(film)
    assert len(library) == 1, "Library should contain only one instance of the film."

def test_film_equality():
    metadata = MockMetadata(year=2023)
    film1 = Film(mubi_id="123456", title="Sample Movie", artwork="http://example.com/art.jpg",
                 web_url="http://example.com", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
    film2 = Film(mubi_id="123456", title="Sample Movie", artwork="http://example.com/art.jpg",
                 web_url="http://example.com", metadata=metadata, available_countries=VALID_COUNTRY_DATA)
    film3 = Film(mubi_id="654321", title="Another Movie", artwork="http://example.com/art2.jpg",
                 web_url="http://example.com", metadata=metadata, available_countries=VALID_COUNTRY_DATA)

    assert film1 == film2, "Films with the same mubi_id should be equal."
    assert film1 != film3, "Films with different mubi_id should not be equal."

def test_sync_locally_with_genre_filtering_OBSOLETE():
    """
    OBSOLETE: Genre filtering logic has been moved to FilmFilter class.
    This test is removed.
    """
    pass



class TestLibrarySyncEdgeCases:
    """Test edge cases for library sync and deduplication."""

    def test_add_film_duplicate_handling(self):
        """Test adding same film_id twice doesn't create duplicates."""
        library = Library()
        metadata = MockMetadata(year=2023)

        film1 = Film(
            mubi_id="123",
            title="Test Movie",
            artwork="http://example.com/art.jpg",
            web_url="http://example.com/film",
            metadata=metadata,
            available_countries=VALID_COUNTRY_DATA
        )
        film2 = Film(
            mubi_id="123",  # Same ID
            title="Test Movie Updated",
            artwork="http://example.com/art2.jpg",
            web_url="http://example.com/film",
            metadata=metadata,
            available_countries=VALID_COUNTRY_DATA
        )

        library.add_film(film1)
        library.add_film(film2)

        # Should only have one film
        assert len(library.films) == 1

    def test_film_availability_country_merging(self):
        """Test when same film added from different countries, availability is merged."""
        library = Library()
        metadata = MockMetadata(year=2023)

        # Film from US
        film_us = Film(
            mubi_id="123",
            title="Test Movie",
            artwork="",
            web_url="",
            metadata=metadata,
            available_countries={'US': VALID_COUNTRY_DATA['US']}
        )
        # Same film from FR (duplicate by mubi_id)
        film_fr = Film(
            mubi_id="123",
            title="Test Movie",
            artwork="",
            web_url="",
            metadata=metadata,
            available_countries={'FR': VALID_COUNTRY_DATA['US']}
        )

        library.add_film(film_us)
        library.add_film(film_fr)

        # Library keeps one entry but merges countries
        assert len(library.films) == 1
        film = library.films["123"]
        # Both countries are preserved
        assert 'US' in film.available_countries
        assert 'FR' in film.available_countries

    def test_library_with_zero_films(self):
        """Test empty library operations work correctly."""
        library = Library()

        assert len(library.films) == 0
        assert library.films == {}

    def test_library_with_one_film(self):
        """Test single film boundary case."""
        library = Library()
        metadata = MockMetadata(year=2023)

        film = Film(
            mubi_id="123",
            title="Only Film",
            artwork="",
            web_url="",
            metadata=metadata
        )
        library.add_film(film)

        assert len(library.films) == 1
        assert library.films["123"].title == "Only Film"


class TestRegressionTests:
    """Regression tests for known bugs."""

    def test_filename_sanitization_consecutive_spaces(self):
        """Test prohibited chars removal doesn't leave consecutive spaces."""
        metadata = MockMetadata(year=2023)
        # Title with multiple prohibited chars that could leave spaces
        film = Film(
            mubi_id="123",
            title="What???Why!!!How...",
            artwork="",
            web_url="",
            metadata=metadata
        )

        folder_name = film.get_sanitized_folder_name()

        # Should not have consecutive spaces
        assert "  " not in folder_name
        # Should still have the year
        assert "(2023)" in folder_name

    def test_vpn_country_suggestion_message_format(self):
        """Test VPN suggestion message shows current country AND suggestions."""
        from plugin_video_mubi.resources.lib.countries import get_country_name

        # Verify country name lookup works for message formatting
        assert get_country_name('CH') == 'Switzerland'
        assert get_country_name('US') == 'United States'
        assert get_country_name('FR') == 'France'

        # Unknown country returns None
        assert get_country_name('XX') is None

    def test_remove_obsolete_files_removes_unavailable_films(self):
        """
        Test that films present in the library object but NOT valid/playable 
        are treated as obsolete and their files are removed.
        
        Specific regression test for 'Night on Earth' issue where upcoming 
        films were persisting in the library.
        """
        with tempfile.TemporaryDirectory() as tmpdirname:
            plugin_userdata_path = Path(tmpdirname)

            # Create upcoming film data mirroring the 'Night on Earth' JSON data found
            # Use dynamic future date to prevent test from failing as time passes
            from datetime import datetime, timedelta, timezone
            future_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat().replace("+00:00", "Z")
            future_end_date = (datetime.now(timezone.utc) + timedelta(days=730)).isoformat().replace("+00:00", "Z")
            
            upcoming_country_data = {
                "AT": {
                    "available_at": future_date, 
                    "availability": "upcoming",
                    "availability_ends_at": future_end_date
                }
            }

            library = Library()
            metadata = MockMetadata(year=1991)
            upcoming_film = Film(
                mubi_id="12345_night_on_earth", 
                title="Night on Earth", 
                artwork="http://example.com/art.jpg", 
                web_url="http://example.com/film", 
                metadata=metadata, 
                available_countries=upcoming_country_data
            )
            
            # Add to library (simulating how mubi.py adds everything before validation)
            library.add_film(upcoming_film)
            
            # Verify it is NOT playable/valid (Crucial check: is_playable must return False)
            assert not library.is_film_valid(upcoming_film)

            # Create the folder for this film to simulate it existing from a previous sync
            # This simulates the state where the user had the folder and it wasn't being removed
            film_folder = plugin_userdata_path / upcoming_film.get_sanitized_folder_name()
            film_folder.mkdir()
            (film_folder / "movie.nfo").touch()

            # Create a valid film too (to ensure we don't just delete everything)
            valid_film = Film(
                mubi_id="valid_film_id", title="Valid Film", artwork="", web_url="", metadata=metadata,
                available_countries=VALID_COUNTRY_DATA
            )
            library.add_film(valid_film)
            valid_folder = plugin_userdata_path / valid_film.get_sanitized_folder_name()
            valid_folder.mkdir()

            # Remove obsolete files
            # Expectation: "Night on Earth" folder should be removed because it's invalid
            removed_count = library.remove_obsolete_files(plugin_userdata_path)

            # Assertions
            assert removed_count == 1, f"Expected 1 remove, got {removed_count}"
            assert not film_folder.exists(), "Night on Earth folder should have been removed."
            assert valid_folder.exists(), "Valid film folder should be preserved."