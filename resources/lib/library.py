# library.py

from pathlib import Path
import xbmc
import xbmcvfs
import xbmcgui
from resources.lib.film import Film


class Library:
    """
    A class to manage a collection of Film objects and handle operations like merging duplicates
    and syncing films locally.
    """

    def __init__(self):
        self.films = []

    def add_film(self, film: Film):
        """
        Add a film to the library.
        
        :param film: The Film object to be added.
        """
        self.films.append(film)


    def merge_duplicates(self):
        """
        Merge duplicate films based on their Mubi ID, combining categories.

        :return: A list of unique films with merged categories.
        """
        unique_films = {}

        for film in self.films:
            if film.mubi_id in unique_films:
                # If the film already exists, append new categories to the existing film's categories.
                for category in film.categories:
                    unique_films[film.mubi_id].add_category(category)
            else:
                # Add the film if it doesn't exist.
                unique_films[film.mubi_id] = film

        # Return the unique films as a list.
        return list(unique_films.values())

    def __len__(self):
        """
        Returns the number of films in the library.
        """
        return len(self.films)


    def sync_locally(self, base_url: str, plugin_userdata_path: Path, omdb_api_key: str):
        """
        Sync the films locally by creating STRM and NFO files for each film.

        :param base_url: Base URL to use for the STRM file links.
        :param plugin_userdata_path: The path where the library files are saved.
        :param omdb_api_key: The OMDb API key for fetching IMDb information.
        """
        pDialog = xbmcgui.DialogProgress()
        pDialog.create("Syncing with Mubi", "Starting the sync...")

        # Merge duplicates before syncing
        self.merge_duplicates()

        total_films = len(self.films)

        # Create files (STRM and NFO)
        for idx, film in enumerate(self.films):
            percent = int((idx / total_films) * 100)
            pDialog.update(percent, f"Creating local data for movie {idx + 1} of {total_films}:\n{film.title}")

            try:
                # Prepare file name and path
                clean_title = film.title.replace("/", " ")
                year = film.metadata.year if film.metadata.year else "Unknown"
                film_folder_name = Path(f"{clean_title} ({year})")
                film_path = plugin_userdata_path / film_folder_name

                # Create the folder
                film_path.mkdir(parents=True, exist_ok=True)

                # Use Film class methods to create STRM and NFO files
                film.create_strm_file(film_path, base_url)
                film.create_nfo_file(film_path, base_url, omdb_api_key)

            except Exception as error:
                xbmc.log(f"Error while creating the library for film {film.title}: {error}", xbmc.LOGERROR)

            if pDialog.iscanceled():
                pDialog.close()
                xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                return None

        pDialog.close()