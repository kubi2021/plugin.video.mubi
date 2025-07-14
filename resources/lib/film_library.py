from pathlib import Path
import xbmc
import xbmcgui
import xbmcaddon
from resources.lib.film import Film
from typing import List, Optional, Tuple
import os
import shutil
from typing import Set
import re

class Film_Library:
    def __init__(self):
        self.films: List[Film] = []

    def add_film(self, film: Film):
        if not film or not film.mubi_id or not film.title or not film.metadata:
            raise ValueError("Invalid film: missing required fields (mubi_id, title, or metadata).")
        if film not in self.films:
            self.films.append(film)

    def __len__(self):
        return len(self.films)

    def sync_locally(self, base_url: str, plugin_userdata_path: Path, omdb_api_key: Optional[str]):
        """
        Synchronize the local library with fetched film/serie data from MUBI.

        :param base_url: The base URL for creating STRM files.
        :param plugin_userdata_path: The path where object folders are stored.
        :param omdb_api_key: The OMDb API key for fetching additional metadata.
        """
        # Filter film by genre
        self.filter_films_by_genre()

        # Initialize counters
        newly_added = 0
        failed_to_add = 0
        total_films = len(self.films)

        # Initialize progress dialog
        pDialog = xbmcgui.DialogProgress()
        pDialog.create("Syncing with MUBI", "Starting the sync...")

        try:
            # create basefolder if it doesn't exist
            basefolder = plugin_userdata_path / "films"
            if not os.path.isdir(basefolder):
                os.makedirs(basefolder)                 

            # Process each film and update progress
            for idx, film in enumerate(self.films):
                percent = int(((idx + 1) / total_films) * 100)  # Ensuring 100% on last film
                pDialog.update(percent, f"Processing movie {idx + 1} of {total_films}:\n{film.title}")
                
                # Check if user canceled
                if pDialog.iscanceled():
                    xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                    break

                # Process film if valid
                if self.is_film_valid(film):
                    result = self.prepare_files_for_film(film, base_url, plugin_userdata_path, omdb_api_key)
                    if result is True:
                        newly_added += 1
                    elif result is False:
                        failed_to_add += 1
                    # If result is None, the film was skipped because files already exist

            # Final cleanup of obsolete files
            obsolete_films_count = self.remove_obsolete_files(plugin_userdata_path)

            # Construct summary message
            message = (
                f"Sync completed successfully!\n"
                f"New movies added: {newly_added}\n"
                f"Failed to add: {failed_to_add}\n"
                f"Obsolete movies removed: {obsolete_films_count}"
            )
            
            # Log results
            xbmc.log(
                f"Sync completed. New films: {newly_added}, Failed films: {failed_to_add}, "
                f"Obsolete films removed: {obsolete_films_count}",
                xbmc.LOGDEBUG
            )
            
            # Show summary dialog
            xbmcgui.Dialog().ok("MUBI", message)
        finally:
            # Ensure the dialog is closed in the end
            pDialog.close()

    def filter_films_by_genre(self):
        """
        Remove films from the library based on genres specified in the settings to skip.
        """
        import xbmcaddon

        # Retrieve settings
        addon = xbmcaddon.Addon()

        # Get the genres to skip from the text input setting
        skip_genres_setting = addon.getSetting('skip_genres')  # Returns a string of genres separated by semicolons
        xbmc.log(f"Skip genres setting value: '{skip_genres_setting}'", xbmc.LOGDEBUG)

        # Parse the genres to skip
        skip_genres = []
        if skip_genres_setting:
            # Split by semicolon, strip whitespace, convert to lowercase
            skip_genres = [genre.strip().lower() for genre in skip_genres_setting.split(';') if genre.strip()]
        
        xbmc.log(f"Genres to skip: {skip_genres}", xbmc.LOGDEBUG)

        # Filter films
        initial_count = len(self.films)
        self.films = [
            film for film in self.films
            if not any(genre.lower() in skip_genres for genre in (film.metadata.genre or []))
        ]
        removed_count = initial_count - len(self.films)
        xbmc.log(f"Removed {removed_count} films based on genre filtering.", xbmc.LOGDEBUG)



    def is_film_valid(self, film: Film) -> bool:
        # Check that film has all necessary attributes
        return film.mubi_id and film.title and film.metadata

    def prepare_files_for_film(
        self, film: Film, base_url: str, plugin_userdata_path: Path, omdb_api_key: Optional[str]
    ) -> Optional[bool]:
        """
        Prepare the necessary files for a given film. Creates NFO and STRM files.
        The STRM file is only created if the NFO file is successfully created.
        If the NFO file creation fails, the STRM file is not created, and the movie folder is removed.

        :param film: The Film object to process.
        :param base_url: The base URL for the STRM file.
        :param plugin_userdata_path: The path where film folders are stored.
        :param omdb_api_key: The OMDb API key for fetching additional metadata.
        :return: 
            - True if both NFO and STRM files were created successfully.
            - False if file creation failed.
            - None if files already exist and were skipped.
        """
        film_folder_name = film.get_sanitized_folder_name()
        film_path = plugin_userdata_path / "films" / film_folder_name

        # Define file paths
        strm_file = film_path / f"{film_folder_name}.strm"
        nfo_file = film_path / f"{film_folder_name}.nfo"

        try:
            # Check if both STRM and NFO files already exist
            if strm_file.exists() and nfo_file.exists():
                xbmc.log(f"Skipping film '{film.title}' - files already exist.", xbmc.LOGDEBUG)
                return None  # Files already exist; no action needed
        except PermissionError as e:
            xbmc.log(f"PermissionError when accessing files for film '{film.title}': {e}", xbmc.LOGERROR)
            return False  # Indicate failure due to permission error

        try:
            # Create the movie folder if it doesn't exist
            film_path.mkdir(parents=True, exist_ok=True)
            xbmc.log(f"Created folder '{film_path}'.", xbmc.LOGDEBUG)

            # Attempt to create the NFO file first
            xbmc.log(f"Creating NFO file for film '{film.title}'.", xbmc.LOGDEBUG)
            film.create_nfo_file(film_path, base_url, omdb_api_key)

            # Verify if the NFO file was created successfully
            if not nfo_file.exists():
                xbmc.log(
                    f"Skipping creation of STRM file for '{film.title}' as NFO file was not created.",
                    xbmc.LOGWARNING
                )
                # Remove the movie folder since NFO creation failed
                shutil.rmtree(film_path)
                xbmc.log(f"Removed folder '{film_path}' due to failed NFO creation.", xbmc.LOGDEBUG)
                return False  # Indicate failure in file creation

            # If NFO was created successfully, proceed to create the STRM file
            xbmc.log(f"Creating STRM file for film '{film.title}'.", xbmc.LOGDEBUG)
            film.create_strm_file(film_path, base_url)
            xbmc.log(f"Successfully created STRM file for '{film.title}'.", xbmc.LOGDEBUG)

            return True  # Indicate successful creation of both files

        except Exception as e:
            # Handle unexpected exceptions during file operations
            xbmc.log(f"Error processing film '{film.title}': {e}", xbmc.LOGERROR)
            # Attempt to remove the folder if it exists to maintain consistency
            if film_path.exists():
                shutil.rmtree(film_path)
                xbmc.log(f"Removed folder '{film_path}' due to error.", xbmc.LOGDEBUG)
            return False  # Indicate failure due to exception




    def remove_obsolete_files(self, plugin_userdata_path: Path) -> int:
        """
        Remove folders in plugin_userdata_path that do not correspond to any film in the library.
        
        :param plugin_userdata_path: Path where the film folders are stored.
        :return: The number of obsolete film folders removed.
        """
        # Get a set of sanitized folder names for the current films in the library
        current_film_folders = {film.get_sanitized_folder_name() for film in self.films}

        # Track obsolete folder count
        obsolete_folders_count = 0

        # Loop through each directory in plugin_userdata_path
        films_dir = plugin_userdata_path / "films"
        for folder in films_dir.iterdir():
            if folder.is_dir() and folder.name not in current_film_folders:
                # Remove the folder if it's not in the current films
                shutil.rmtree(folder)
                obsolete_folders_count += 1

        return obsolete_folders_count

