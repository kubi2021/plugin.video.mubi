import tempfile
from unittest.mock import patch, call
from pathlib import Path
from resources.lib.film import Film
from resources.lib.library import Library
import pytest
import os

# Mock Metadata class for testing
class MockMetadata:
    def __init__(self, year):
        self.year = year

def test_add_valid_film():
    library = Library()
    metadata = MockMetadata(year=2023)
    film = Film(mubi_id="123456", title="Sample Movie", artwork="http://example.com/art.jpg", web_url="http://example.com", category="Drama", metadata=metadata)
    library.add_film(film)
    assert len(library.films) == 1, "Film should have been added to the library."

def test_library_len():
    library = Library()
    assert len(library) == 0, "Expected library length to be 0 when empty."
    film1 = Film(mubi_id="123", title="Film One", artwork="http://example.com/art1.jpg", web_url="http://example.com/film1", category="Drama", metadata=MockMetadata(2021))
    film2 = Film(mubi_id="456", title="Film Two", artwork="http://example.com/art2.jpg", web_url="http://example.com/film2", category="Comedy", metadata=MockMetadata(2022))
    library.add_film(film1)
    library.add_film(film2)
    assert len(library) == 2, "Expected library length to be 2 after adding two films."

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
            category="Drama",
            metadata=metadata
        )
        library.add_film(film)

        # Prepare paths
        film_folder_name = film.get_sanitized_folder_name()
        film_path = plugin_userdata_path / film_folder_name
        nfo_file = film_path / f"{film_folder_name}.nfo"
        strm_file = film_path / f"{film_folder_name}.strm"

        # Mock create_nfo_file to create the NFO file
        def create_nfo_side_effect(film_path_arg, base_url_arg, omdb_api_key_arg):
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
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path, omdb_api_key)

        # Assert that prepare_files_for_film returned True
        assert result is True, "prepare_files_for_film should return True for successful file creation."

        # Check if the calls to `create_nfo_file` and `create_strm_file` have the expected arguments
        expected_folder = plugin_userdata_path / film.get_sanitized_folder_name()
        
        # Assert that create_nfo_file is called with `expected_folder`, `base_url`, and `omdb_api_key`
        mock_create_nfo.assert_called_once_with(expected_folder, base_url, omdb_api_key)
        
        # Assert that create_strm_file is called with `expected_folder` and `base_url`
        mock_create_strm.assert_called_once_with(expected_folder, base_url)


@patch.object(Film, "create_nfo_file")
@patch.object(Film, "create_strm_file")
def test_prepare_files_for_film_skipped(mock_create_strm, mock_create_nfo):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()
        
        # Create a Film object
        metadata = MockMetadata(year=2023)
        film = Film(
            mubi_id="789012",
            title="Existing Movie",
            artwork="http://example.com/art2.jpg",
            web_url="http://example.com",
            category="Comedy",
            metadata=metadata
        )
        library.add_film(film)

        # Prepare paths
        film_folder_name = film.get_sanitized_folder_name()
        film_path = plugin_userdata_path / film_folder_name
        nfo_file = film_path / f"{film_folder_name}.nfo"
        strm_file = film_path / f"{film_folder_name}.strm"

        # Simulate existing files by creating them
        film_path.mkdir(parents=True, exist_ok=True)
        nfo_file.touch()
        strm_file.touch()

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path, omdb_api_key)

        # Assert that prepare_files_for_film returned None
        assert result is None, "prepare_files_for_film should return None when files already exist."

        # Assert that create_nfo_file and create_strm_file were not called
        mock_create_nfo.assert_not_called()
        mock_create_strm.assert_not_called()


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
            category="Action",
            metadata=metadata
        )
        library.add_film(film)

        # Prepare paths
        film_folder_name = film.get_sanitized_folder_name()
        film_path = plugin_userdata_path / film_folder_name
        nfo_file = film_path / f"{film_folder_name}.nfo"
        strm_file = film_path / f"{film_folder_name}.strm"

        # Mock create_nfo_file to simulate failure (do nothing)
        def create_nfo_side_effect(film_path_arg, base_url_arg, omdb_api_key_arg):
            pass  # Do nothing; NFO file is not created

        mock_create_nfo.side_effect = create_nfo_side_effect

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"

        # Ensure that the NFO file does not exist
        assert not nfo_file.exists()

        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path, omdb_api_key)

        # Assert that prepare_files_for_film returned False
        assert result is False, "prepare_files_for_film should return False when file creation fails."

        # Assert that create_nfo_file was called
        expected_folder = plugin_userdata_path / film.get_sanitized_folder_name()
        mock_create_nfo.assert_called_once_with(expected_folder, base_url, omdb_api_key)

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
        film = Film(mubi_id="123456", title="Current Film", artwork="http://example.com/art.jpg", web_url="http://example.com", category="Drama", metadata=metadata)
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

@patch("xbmcgui.DialogProgress")
@patch.object(Library, "prepare_files_for_film")
@patch.object(Library, "remove_obsolete_files")
def test_sync_locally(mock_remove_obsolete, mock_prepare_files, mock_dialog_progress):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Create Film objects and add them to the library
        metadata = MockMetadata(year=2023)
        film1 = Film(mubi_id="123", title="Sample Movie 1", artwork="http://example.com/art1.jpg",
                     web_url="http://example.com/film1", category="Drama", metadata=metadata)
        film2 = Film(mubi_id="456", title="Sample Movie 2", artwork="http://example.com/art2.jpg",
                     web_url="http://example.com/film2", category="Comedy", metadata=metadata)
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
        library.sync_locally(base_url, plugin_userdata_path, omdb_api_key)

        # Assertions for progress dialog
        mock_dialog.create.assert_called_once_with("Syncing with MUBI", "Starting the sync...")
        assert mock_dialog.update.call_count == 2, "Progress dialog should have been updated twice"
        mock_dialog.close.assert_called_once()

        # Assert that prepare_files_for_film was called for each film
        expected_calls = [
            call(film1, base_url, plugin_userdata_path, omdb_api_key),
            call(film2, base_url, plugin_userdata_path, omdb_api_key)
        ]
        mock_prepare_files.assert_has_calls(expected_calls, any_order=False)

        # Assert that remove_obsolete_files was called
        mock_remove_obsolete.assert_called_once_with(plugin_userdata_path)

@patch("xbmcgui.DialogProgress")
@patch.object(Library, "prepare_files_for_film")
@patch.object(Library, "remove_obsolete_files")
def test_sync_locally_user_cancellation(mock_remove_obsolete, mock_prepare_files, mock_dialog_progress):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Create Film objects and add them to the library
        metadata = MockMetadata(year=2023)
        film1 = Film(mubi_id="123", title="Sample Movie 1", artwork="http://example.com/art1.jpg",
                     web_url="http://example.com/film1", category="Drama", metadata=metadata)
        film2 = Film(mubi_id="456", title="Sample Movie 2", artwork="http://example.com/art2.jpg",
                     web_url="http://example.com/film2", category="Comedy", metadata=metadata)
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
        library.sync_locally(base_url, plugin_userdata_path, omdb_api_key)

        # Assert that prepare_files_for_film was called only once
        mock_prepare_files.assert_called_once_with(film1, base_url, plugin_userdata_path, omdb_api_key)

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
            category="Drama",
            metadata=metadata
        )
        library.add_film(film)

        # Simulate exception in create_nfo_file
        mock_create_nfo.side_effect = Exception("Simulated exception in create_nfo_file")

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path, omdb_api_key)

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
            category="Drama",
            metadata=metadata
        )
        library.add_film(film)

        # Mock create_nfo_file to create the NFO file
        def create_nfo_side_effect(film_path_arg, base_url_arg, omdb_api_key_arg):
            film_path_arg.mkdir(parents=True, exist_ok=True)
            (film_path_arg / f"{film.get_sanitized_folder_name()}.nfo").touch()

        mock_create_nfo.side_effect = create_nfo_side_effect

        # Simulate exception in create_strm_file
        mock_create_strm.side_effect = Exception("Simulated exception in create_strm_file")

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path, omdb_api_key)

        # Assert that prepare_files_for_film returned False
        assert result is False, "Should return False when an exception occurs in create_strm_file."

def test_remove_obsolete_files_no_obsolete():
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)

        # Create a film and add it to the library
        library = Library()
        metadata = MockMetadata(year=2023)
        film = Film(mubi_id="123456", title="Current Film", artwork="http://example.com/art.jpg",
                    web_url="http://example.com", category="Drama", metadata=metadata)
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
                web_url="http://example.com", category="Drama", metadata=metadata)
    library.add_film(film)

    # Attempt to remove obsolete files
    try:
        count = library.remove_obsolete_files(plugin_userdata_path)
        assert count == 0, "Should return 0 when path does not exist."
    except FileNotFoundError:
        # Expected behavior if the method does not handle non-existent paths internally
        pass

@patch("xbmcgui.DialogProgress")
@patch.object(Library, "remove_obsolete_files")
def test_sync_locally_empty_library(mock_remove_obsolete, mock_dialog_progress):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()  # Empty library

        # Mock dialog behavior to not cancel
        mock_dialog = mock_dialog_progress.return_value
        mock_dialog.iscanceled.return_value = False

        # Run sync_locally
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"
        library.sync_locally(base_url, plugin_userdata_path, omdb_api_key)

        # Assertions for progress dialog
        mock_dialog.create.assert_called_once_with("Syncing with MUBI", "Starting the sync...")
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
            category="Drama",
            metadata=metadata
        )
        library.add_film(film)

        # Run prepare_files_for_film
        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"

        # Mock create_nfo_file and create_strm_file to create files
        with patch.object(Film, "create_nfo_file") as mock_create_nfo, \
             patch.object(Film, "create_strm_file") as mock_create_strm:
            def create_nfo_side_effect(film_path_arg, base_url_arg, omdb_api_key_arg):
                film_path_arg.mkdir(parents=True, exist_ok=True)
                (film_path_arg / f"{film.get_sanitized_folder_name()}.nfo").touch()

            def create_strm_side_effect(film_path_arg, base_url_arg):
                (film_path_arg / f"{film.get_sanitized_folder_name()}.strm").touch()

            mock_create_nfo.side_effect = create_nfo_side_effect
            mock_create_strm.side_effect = create_strm_side_effect

            result = library.prepare_files_for_film(film, base_url, plugin_userdata_path, omdb_api_key)

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
            category="Drama",
            metadata=metadata
        )
        library.add_film(film)

        base_url = "plugin://plugin.video.mubi/"
        omdb_api_key = "fake_api_key"

        # Run prepare_files_for_film
        result = library.prepare_files_for_film(film, base_url, plugin_userdata_path, omdb_api_key)

        # Assert that prepare_files_for_film returned False due to exception
        assert result is False, "Should return False when unable to write to the directory."

        # Reset permissions for cleanup
        os.chmod(plugin_userdata_path, 0o700)


@patch("xbmcgui.DialogProgress")
@patch.object(Library, "prepare_files_for_film")
@patch.object(Library, "remove_obsolete_files")
def test_sync_locally_large_library(mock_remove_obsolete, mock_prepare_files, mock_dialog_progress):
    with tempfile.TemporaryDirectory() as tmpdirname:
        plugin_userdata_path = Path(tmpdirname)
        library = Library()

        # Create 1000 Film objects and add them to the library
        metadata = MockMetadata(year=2023)
        for i in range(1000):
            film = Film(
                mubi_id=str(i),
                title=f"Sample Movie {i}",
                artwork=f"http://example.com/art{i}.jpg",
                web_url=f"http://example.com/film{i}",
                category="Drama",
                metadata=metadata
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
        library.sync_locally(base_url, plugin_userdata_path, omdb_api_key)

        # Assert that prepare_files_for_film was called 1000 times
        assert mock_prepare_files.call_count == 1000, "prepare_files_for_film should be called 1000 times."

def test_add_duplicate_film():
    library = Library()
    metadata = MockMetadata(year=2023)
    film = Film(mubi_id="123456", title="Sample Movie", artwork="http://example.com/art.jpg",
                web_url="http://example.com", category="Drama", metadata=metadata)
    library.add_film(film)
    library.add_film(film)
    assert len(library) == 1, "Library should contain only one instance of the film."

def test_film_equality():
    metadata = MockMetadata(year=2023)
    film1 = Film(mubi_id="123456", title="Sample Movie", artwork="http://example.com/art.jpg",
                 web_url="http://example.com", category="Drama", metadata=metadata)
    film2 = Film(mubi_id="123456", title="Sample Movie", artwork="http://example.com/art.jpg",
                 web_url="http://example.com", category="Drama", metadata=metadata)
    film3 = Film(mubi_id="654321", title="Another Movie", artwork="http://example.com/art2.jpg",
                 web_url="http://example.com", category="Drama", metadata=metadata)

    assert film1 == film2, "Films with the same mubi_id should be equal."
    assert film1 != film3, "Films with different mubi_id should not be equal."
