from pathlib import Path
import xbmc
import xbmcgui
from resources.lib.film import Film
from typing import List, Optional
import os
import shutil
from typing import Set


class Library:
    """
    A class to manage a collection of Film objects and handle operations like merging duplicates
    and syncing films locally.
    """

    def __init__(self):
        self.films: List[Film] = []

    def add_film(self, film: Film):
        """
        Add a film to the library.

        :param film: The Film object to be added.
        :raises ValueError: If the film is invalid (missing title, ID, or metadata).
        """
        if not film or not film.mubi_id or not film.title or not film.metadata:
            raise ValueError("Invalid film: missing required fields (mubi_id, title, or metadata).")
        self.films.append(film)

    def merge_duplicates(self) -> List[Film]:
        """
        Merge duplicate films based on their Mubi ID, combining categories.

        :return: A list of unique films with merged categories.
        """
        unique_films = {}

        for film in self.films:
            try:
                if film.mubi_id in unique_films:
                    # Add new categories to the existing film's categories
                    for category in film.categories:
                        unique_films[film.mubi_id].add_category(category)
                else:
                    # Add the film if it's not already in the collection
                    unique_films[film.mubi_id] = film
            except AttributeError as e:
                xbmc.log(f"Error processing film '{film.title}': {e}", xbmc.LOGERROR)

        # Replace the current list of films with the merged list
        self.films = list(unique_films.values())
        return self.films

    def __len__(self) -> int:
        """
        Returns the number of films in the library.

        :return: Number of films in the library.
        """
        return len(self.films)

    def sync_locally(self, base_url: str, plugin_userdata_path: Path, omdb_api_key: Optional[str]):
        """
        Sync the films locally by creating STRM and NFO files for each film.
        Also removes local films that are no longer available on Mubi.

        :param base_url: Base URL to use for the STRM file links.
        :param plugin_userdata_path: The path where the library files are saved.
        :param omdb_api_key: The OMDb API key for fetching IMDb information.
        :raises ValueError: If no films are available to sync.
        """
        if not self.films:
            raise ValueError("No films available to sync.")

        # Merge duplicates before syncing
        self.merge_duplicates()

        # Collect existing film directories before syncing
        existing_film_dirs = set()
        for item in plugin_userdata_path.iterdir():
            if item.is_dir():
                existing_film_dirs.add(item.name)

        # Create or update films
        new_films_count = self.create_or_update_films(base_url, plugin_userdata_path, omdb_api_key)

        # Collect current film directories after syncing
        current_film_dirs = set()
        for film in self.films:
            clean_title = film.title.replace("/", " ")
            year = film.metadata.year if film.metadata.year else "Unknown"
            film_folder_name = f"{clean_title} ({year})"
            current_film_dirs.add(film_folder_name)

        # Remove obsolete films
        obsolete_film_dirs = existing_film_dirs - current_film_dirs
        obsolete_films_count = self.remove_obsolete_films(plugin_userdata_path, obsolete_film_dirs)

        message = (
            f"Sync completed successfully!\n"
            f"New movies added: {new_films_count}\n"
            f"Obsolete movies removed: {obsolete_films_count}"
        )
        xbmcgui.Dialog().ok("MUBI", message)

    def create_or_update_films(self, base_url: str, plugin_userdata_path: Path, omdb_api_key: Optional[str]) -> int:
        """
        Create or update STRM and NFO files for each film.

        :param base_url: Base URL to use for the STRM file links.
        :param plugin_userdata_path: The path where the library files are saved.
        :param omdb_api_key: The OMDb API key for fetching IMDb information.
        :return: The number of new films added.
        """
        total_films = len(self.films)
        new_films_count = 0

        pDialog = xbmcgui.DialogProgress()
        pDialog.create("Syncing with MUBI", "Starting the sync...")

        for idx, film in enumerate(self.films):
            percent = int((idx / total_films) * 100)
            pDialog.update(percent, f"Processing movie {idx + 1} of {total_films}:\n{film.title}")

            if pDialog.iscanceled():
                pDialog.close()
                xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                return new_films_count  # Return the count of new films added

            try:
                # Prepare file name and path
                clean_title = film.title.replace("/", " ")
                year = film.metadata.year if film.metadata.year else "Unknown"
                film_folder_name = f"{clean_title} ({year})"
                film_path = plugin_userdata_path / film_folder_name

                # Paths to the STRM and NFO files
                strm_file = film_path / f"{film_folder_name}.strm"
                nfo_file = film_path / f"{film_folder_name}.nfo"

                # Check if the film directory and both files already exist
                if film_path.exists() and strm_file.exists() and nfo_file.exists():
                    xbmc.log(f"Film '{film.title}' already synced. Skipping...", xbmc.LOGDEBUG)
                    continue  # Skip to the next film

                # Create the folder if it doesn't exist
                film_path.mkdir(parents=True, exist_ok=True)

                # Use Film class methods to create STRM and NFO files
                film.create_strm_file(film_path, base_url)
                film.create_nfo_file(film_path, base_url, omdb_api_key)

                # Increment new films count
                new_films_count += 1

            except OSError as error:
                xbmc.log(f"Error while creating library files for film '{film.title}': {error}", xbmc.LOGERROR)
            except ValueError as error:
                xbmc.log(f"Invalid data for film '{film.title}': {error}", xbmc.LOGERROR)

        pDialog.close()
        return new_films_count


    def remove_obsolete_films(self, plugin_userdata_path: Path, obsolete_film_dirs: Set[str]) -> int:
        """
        Remove local film directories that are no longer available on Mubi.

        :param plugin_userdata_path: The path where the library files are saved.
        :param obsolete_film_dirs: A set of directory names corresponding to obsolete films.
        :return: The number of obsolete films removed.
        """
        obsolete_films_count = 0
        for dir_name in obsolete_film_dirs:
            dir_path = plugin_userdata_path / dir_name
            try:
                # Remove the directory and its contents
                shutil.rmtree(dir_path)
                obsolete_films_count += 1
                xbmc.log(f"Removed obsolete film directory: {dir_path}", xbmc.LOGDEBUG)
            except Exception as e:
                xbmc.log(f"Error removing obsolete film directory '{dir_path}': {e}", xbmc.LOGERROR)
        return obsolete_films_count

