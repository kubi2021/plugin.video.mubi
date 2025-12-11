from pathlib import Path
import xbmc
import xbmcgui
import xbmcaddon
from .film import Film
from typing import List, Optional, Tuple
import os
import shutil
from typing import Set
import re

class Library:
    def __init__(self):
        self.films: List[Film] = []

    def add_film(self, film: Film):
        if not film or not film.mubi_id or not film.title or not film.metadata:
            raise ValueError("Invalid film: missing required fields (mubi_id, title, or metadata).")
        if film not in self.films:
            self.films.append(film)

    def __len__(self):
        return len(self.films)

    def sync_locally(self, base_url: str, plugin_userdata_path: Path):
        """
        Synchronize the local library with fetched film data from MUBI.

        :param base_url: The base URL for creating STRM files.
        :param plugin_userdata_path: The path where film folders are stored.
        """
        # Store initial count before filtering
        initial_film_count = len(self.films)

        # Filter film by genre
        self.filter_films_by_genre()

        # Calculate how many were filtered
        genre_filtered_count = initial_film_count - len(self.films)

        # Log films that contain problematic characters for debugging
        for film in self.films:
            if '#' in film.title or any(char in film.title for char in '<>:"/\\|?*^%$&{}@!;`~'):
                xbmc.log(
                    f"Processing film with special characters: '{film.title}' "
                    f"-> sanitized: '{film.get_sanitized_folder_name()}'",
                    xbmc.LOGINFO
                )

        # Initialize counters
        newly_added = 0
        failed_to_add = 0
        availability_updated = 0
        films_to_process = len(self.films)

        # Initialize progress dialog with filter info
        pDialog = xbmcgui.DialogProgress()
        if genre_filtered_count > 0:
            pDialog.create(
                "Syncing with MUBI 2/2",
                f"Processing {films_to_process} films ({genre_filtered_count} filtered out by genre)..."
            )
        else:
            pDialog.create("Syncing with MUBI 2/2", f"Processing {films_to_process} films...")

        try:
            # Process each film and update progress
            for idx, film in enumerate(self.films):
                percent = int(((idx + 1) / films_to_process) * 100)
                if genre_filtered_count > 0:
                    progress_msg = f"Processing movie {idx + 1} of {films_to_process} ({genre_filtered_count} skipped by genre filter):\n{film.title}"
                else:
                    progress_msg = f"Processing movie {idx + 1} of {films_to_process}:\n{film.title}"
                pDialog.update(percent, progress_msg)

                # Check if user canceled
                if pDialog.iscanceled():
                    xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                    break

                # Process film if valid
                if self.is_film_valid(film):
                    result = self.prepare_files_for_film(
                        film, base_url, plugin_userdata_path
                    )
                    if result is True:
                        newly_added += 1
                    elif result is False:
                        failed_to_add += 1
                    elif result is None:
                        availability_updated += 1  # NFO availability was updated for existing film

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

        # Build list of genres to skip based on toggle settings
        # Map setting IDs to genre names (lowercase for comparison)
        genre_settings = {
            'skip_genre_action': 'action',
            'skip_genre_adventure': 'adventure',
            'skip_genre_animation': 'animation',
            'skip_genre_avant_garde': 'avant-garde',
            'skip_genre_comedy': 'comedy',
            'skip_genre_commercial': 'commercial',
            'skip_genre_crime': 'crime',
            'skip_genre_cult': 'cult',
            'skip_genre_documentary': 'documentary',
            'skip_genre_drama': 'drama',
            'skip_genre_erotica': 'erotica',
            'skip_genre_fantasy': 'fantasy',
            'skip_genre_horror': 'horror',
            'skip_genre_lgbtq': 'lgbtq+',
            'skip_genre_mystery': 'mystery',
            'skip_genre_romance': 'romance',
            'skip_genre_sci_fi': 'sci-fi',
            'skip_genre_short': 'short',
            'skip_genre_thriller': 'thriller',
            'skip_genre_tv_movie': 'tv movie',
        }

        skip_genres = []
        for setting_id, genre_name in genre_settings.items():
            if addon.getSettingBool(setting_id):
                skip_genres.append(genre_name)

        xbmc.log(f"Genres to skip: {skip_genres}", xbmc.LOGDEBUG)

        if not skip_genres:
            xbmc.log("No genres to skip, keeping all films.", xbmc.LOGDEBUG)
            return

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
        self, film: Film, base_url: str, plugin_userdata_path: Path
    ) -> Optional[bool]:
        """
        Prepare the necessary files for a given film. Creates NFO and STRM files.
        The NFO file country availability is always updated on each sync.
        Full NFO creation is only done if NFO doesn't exist (expensive due to OMDB API calls).

        :param film: The Film object to process.
        :param base_url: The base URL for the STRM file.
        :param plugin_userdata_path: The path where film folders are stored.
        :return:
            - True if files were created/updated successfully.
            - False if file creation failed.
            - None if NFO already exists and only availability was updated.
        """
        film_folder_name = film.get_sanitized_folder_name()
        film_path = plugin_userdata_path / film_folder_name

        # Define file paths
        strm_file = film_path / f"{film_folder_name}.strm"
        nfo_file = film_path / f"{film_folder_name}.nfo"

        try:
            # Check if NFO already exists (skip expensive NFO creation but always update availability)
            nfo_exists = nfo_file.exists()
            if nfo_exists:
                # Update country availability in NFO file (quick operation)
                xbmc.log(f"Updating availability for '{film.title}' (NFO exists).", xbmc.LOGDEBUG)
                film.update_nfo_availability(nfo_file)
                return None  # Indicate availability was updated (not a new film)
        except PermissionError as e:
            xbmc.log(f"PermissionError when accessing files for film '{film.title}': {e}", xbmc.LOGERROR)
            return False  # Indicate failure due to permission error

        try:
            # Create the movie folder if it doesn't exist
            film_path.mkdir(parents=True, exist_ok=True)
            xbmc.log(f"Created folder '{film_path}'.", xbmc.LOGDEBUG)

            # Attempt to create the NFO file first
            xbmc.log(f"Creating NFO file for film '{film.title}'.", xbmc.LOGDEBUG)
            film.create_nfo_file(film_path, base_url)

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

            # BUG #9 FIX: Verify that the STRM file was actually created
            if not strm_file.exists():
                xbmc.log(
                    f"STRM file creation failed for '{film.title}' - file does not exist after creation.",
                    xbmc.LOGERROR
                )
                # Remove the movie folder since STRM creation failed
                shutil.rmtree(film_path)
                xbmc.log(f"Removed folder '{film_path}' due to failed STRM creation.", xbmc.LOGDEBUG)
                return False  # Indicate failure in file creation

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
        for folder in plugin_userdata_path.iterdir():
            if folder.is_dir() and folder.name not in current_film_folders:
                # Remove the folder if it's not in the current films
                shutil.rmtree(folder)
                obsolete_folders_count += 1

        return obsolete_folders_count

