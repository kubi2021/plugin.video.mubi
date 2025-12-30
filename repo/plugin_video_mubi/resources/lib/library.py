from pathlib import Path
import sys
import xbmc
import xbmcgui
import xbmcaddon
from .film import Film
from typing import List, Optional, Tuple, Union
import os
import shutil
from typing import Set
import re
import json

class Library:
    def __init__(self):
        self.films = {}  # Dictionary mapping mubi_id to Film object

    def add_film(self, film: Film):
        if not film or not film.mubi_id or not film.title or not film.metadata:
            raise ValueError("Invalid film: missing required fields (mubi_id, title, or metadata).")
        
        if film.mubi_id in self.films:
            # Film exists, merge availability data
            existing_film = self.films[film.mubi_id]
            if film.available_countries:
                existing_film.available_countries.update(film.available_countries)
        else:
            # New film, add to library
            self.films[film.mubi_id] = film

    def __len__(self):
        return len(self.films)

    def sync_locally(self, base_url: str, plugin_userdata_path: Path, skip_external_metadata: bool = False):
        """
        Synchronize the local library with fetched film data from MUBI.

        :param base_url: The base URL for creating STRM files.
        :param plugin_userdata_path: The path where film folders are stored.
        :param skip_external_metadata: If True, skip attempting to fetch external metadata (IMDB/TMDB) for new films.
        """
        # Films are expected to be already filtered by the time they are added to Library

        # Log films that contain problematic characters for debugging
        for film in self.films.values():
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
        rating_updated = 0
        films_to_kodi_update = []
        films_to_process = len(self.films)

        # Initialize progress dialog
        pDialog = xbmcgui.DialogProgress()
        pDialog.create("Syncing with MUBI 2/2", f"Processing {films_to_process} films...")

        import concurrent.futures

        # Get concurrency setting (default to 5 for safety on low-end devices)
        # 1 = Serial, 5 = Standard, 10+ = High Performance
        try:
             import xbmcaddon
             max_workers = xbmcaddon.Addon().getSettingInt("sync_concurrency")
             
             if max_workers == 0:
                 # Auto mode: 90% of threads
                 cpu_count = os.cpu_count() or 1
                 max_workers = max(1, int(cpu_count * 0.9))
                 xbmc.log(f"MUBI Sync: Auto-concurrency detected {cpu_count} CPUs. Using {max_workers} threads (90%).", xbmc.LOGINFO)
             elif max_workers < 1:
                 # Fallback for invalid negative values
                 max_workers = 5
        except Exception:
             max_workers = 5
             
        xbmc.log(f"Starting sync with {max_workers} worker threads.", xbmc.LOGDEBUG)
        
        processed_count = 0

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_film = {
                    executor.submit(self.prepare_files_for_film, film, base_url, plugin_userdata_path, skip_external_metadata): film
                    for film in self.films.values()
                    if self.is_film_valid(film)
                }

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_film):
                    # Check cancel
                    if pDialog.iscanceled():
                        xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                        # cancel_futures was added in Python 3.9
                        if sys.version_info >= (3, 9):
                            executor.shutdown(wait=False, cancel_futures=True)
                        else:
                            executor.shutdown(wait=False)
                        break

                    film = future_to_film[future]
                    processed_count += 1
                    
                    # Update progress
                    percent = int((processed_count / films_to_process) * 100)
                    progress_msg = f"Processing movie {processed_count} of {films_to_process}:\n{film.title}"
                    pDialog.update(percent, progress_msg)

                    try:
                        result = future.result()
                        if result is True:
                            newly_added += 1
                        elif result is False:
                            failed_to_add += 1
                        elif result == "RATING_UPDATED":
                            rating_updated += 1
                            # Construct path for individual update
                            # film.get_sanitized_folder_name() is reliable
                            fname = film.get_sanitized_folder_name()
                            fpath = plugin_userdata_path / fname
                            # Store the FULL path to the STRM file for accurate finding
                            strm_path = fpath / f"{fname}.strm"
                            films_to_kodi_update.append(strm_path)
                        elif result is None:
                            availability_updated += 1
                    except Exception as e:
                        xbmc.log(f"Unhandled exception processing film '{film.title}': {e}", xbmc.LOGERROR)
                        failed_to_add += 1

            # Final cleanup of obsolete files
            obsolete_films_count = self.remove_obsolete_files(plugin_userdata_path)

            # Construct summary message
            message = (
                f"Sync completed successfully!\n"
                f"New movies added: {newly_added}\n"
                f"Metadata updated: {rating_updated}\n"
                f"Failed to add: {failed_to_add}\n"
                f"Obsolete movies removed: {obsolete_films_count}"
            )
            
            # Trigger individual updates for modified ratings
            if films_to_kodi_update:
                xbmc.log(f"Triggering metadata refresh for {len(films_to_kodi_update)} films...", xbmc.LOGINFO)
                xbmc.log(f"Triggering metadata refresh for {len(films_to_kodi_update)} films...", xbmc.LOGINFO)
                for strm_path in films_to_kodi_update:
                    self.refresh_film_metadata(strm_path)
            
            # Log results
            xbmc.log(
                f"Sync completed. New: {newly_added}, Updated: {rating_updated}, Failed: {failed_to_add}, "
                f"Obsolete removed: {obsolete_films_count}",
                xbmc.LOGDEBUG
            )
            
            # Show summary dialog
            xbmcgui.Dialog().ok("MUBI", message)
        finally:
            # Ensure the dialog is closed in the end
            pDialog.close()



    def is_film_valid(self, film: Film) -> bool:
        # Check that film has all necessary attributes AND at least one available country
        if not film.mubi_id or not film.title or not film.metadata:
            return False
            
        # Check integrity of available_countries
        # Case 1: Empty dictionary (True Zombie) - Caught by 'and film.available_countries'
        # Case 2: Keys with empty values (Semi-Zombie) - e.g. {'DK': {}} due to null consumable
        if not film.available_countries:
            return False
            
        # Ensure film is actually playable based on date ranges
        return film.is_playable()

    def prepare_files_for_film(
        self, film: Film, base_url: str, plugin_userdata_path: Path, skip_external_metadata: bool = False
    ) -> Union[bool, str, None]:
        """
        Prepare the necessary files for a given film. Creates NFO and STRM files.
        The NFO file country availability is always updated on each sync.
        Full NFO creation is only done if NFO doesn't exist (expensive due to OMDB API calls).

        :param film: The Film object to process.
        :param base_url: The base URL for the STRM file.
        :param plugin_userdata_path: The path where film folders are stored.
        :param skip_external_metadata: If True, do not attempt to fetch external metadata.
        :return:
            - True if files were created (new film).
            - False if file creation failed.
            - "RATING_UPDATED" if NFO exists but rating mismatches (metadata updated).
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
                # Check if rating needs update (only for GitHub sync/when we have Bayesian data)
                # If rating is NOT synced, we shouldn't return None; we should proceed to overwrite NFO.
                rating_synced = film.is_rating_synced(nfo_file)
                
                if rating_synced:
                    # Update country availability in NFO file (quick operation)
                    xbmc.log(f"Updating availability for '{film.title}' (NFO exists & rating synced).", xbmc.LOGDEBUG)
                    film.update_nfo_availability(nfo_file)
                    return None  # Indicate availability was updated (not a new film)
                else:
                     xbmc.log(f"Forcing NFO update for '{film.title}' due to rating change.", xbmc.LOGINFO)
                     # Fall through to create_nfo_file which overwrites
                     # We will return special status later if successful
        except PermissionError as e:
            xbmc.log(f"PermissionError when accessing files for film '{film.title}': {e}", xbmc.LOGERROR)
            return False  # Indicate failure due to permission error

        try:
            # Create the movie folder if it doesn't exist
            film_path.mkdir(parents=True, exist_ok=True)
            xbmc.log(f"Created folder '{film_path}'.", xbmc.LOGDEBUG)

            # Attempt to create the NFO file first
            xbmc.log(f"Creating NFO file for film '{film.title}'.", xbmc.LOGDEBUG)
            film.create_nfo_file(film_path, base_url, skip_external_metadata=skip_external_metadata)

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
            xbmc.log(f"Successfully created STRM file for '{film.title}'.", xbmc.LOGDEBUG)
            
            if nfo_exists:
                return "RATING_UPDATED"
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
        current_film_folders = {film.get_sanitized_folder_name() for film in self.films.values() if self.is_film_valid(film)}

        # Track obsolete folder count
        obsolete_folders_count = 0

        # Loop through each directory in plugin_userdata_path
        for folder in plugin_userdata_path.iterdir():
            if folder.is_dir() and folder.name not in current_film_folders:
                # Remove the folder if it's not in the current films
                shutil.rmtree(folder)
                obsolete_folders_count += 1

        return obsolete_folders_count

    def refresh_film_metadata(self, strm_path: Path):
        """
        Force a metadata refresh for a specific film using JSON-RPC.
        This is more reliable than UpdateLibrary for existing items where only metadata changed.
        
        :param strm_path: Absolute path to the .strm file of the film.
        """
        try:
            # 1. Find the movieid using VideoLibrary.GetMovies filtering by file path
            # We must use the string path.
            path_str = str(strm_path)
            
            # Construct JSON-RPC request to find the movie
            # We filter by 'file' to find the specific item
            find_req = {
                "jsonrpc": "2.0", 
                "method": "VideoLibrary.GetMovies", 
                "params": {
                    "filter": {"field": "file", "operator": "is", "value": path_str},
                    "properties": ["title"] 
                }, 
                "id": 1
            }
            
            find_resp_str = xbmc.executeJSONRPC(json.dumps(find_req))
            find_resp = json.loads(find_resp_str)
            
            movie_id = None
            if "result" in find_resp and "movies" in find_resp["result"]:
                movies = find_resp["result"]["movies"]
                if movies:
                    movie_id = movies[0].get("movieid")
            
            # 2. Fallback: Search by filename if exact path match failed
            if not movie_id:
                xbmc.log(f"Exact path match failed for '{path_str}', trying filename match...", xbmc.LOGDEBUG)
                filename = strm_path.name
                find_req_fallback = {
                    "jsonrpc": "2.0", 
                    "method": "VideoLibrary.GetMovies", 
                    "params": {
                        "filter": {"field": "filename", "operator": "is", "value": filename},
                        "properties": ["title", "file"] 
                    }, 
                    "id": 2
                }
                find_resp_str_fallback = xbmc.executeJSONRPC(json.dumps(find_req_fallback))
                find_resp_fallback = json.loads(find_resp_str_fallback)
                
                if "result" in find_resp_fallback and "movies" in find_resp_fallback["result"]:
                    movies = find_resp_fallback["result"]["movies"]
                    if movies:
                        # If multiple matches, we should be careful. 
                        # But typically filename contains Title (Year) so it's unique.
                        movie_id = movies[0].get("movieid")
                        xbmc.log(f"Found movieid {movie_id} via filename match for '{filename}'", xbmc.LOGINFO)

            if movie_id:
                xbmc.log(f"Found movieid {movie_id} for '{path_str}'. Refreshing...", xbmc.LOGDEBUG)
                
                # 3. Refresh the specific movie using VideoLibrary.RefreshMovie
                # ignorenfo=false is default, so it will read our newly updated NFO
                refresh_req = {
                    "jsonrpc": "2.0",
                    "method": "VideoLibrary.RefreshMovie",
                    "params": {
                        "movieid": movie_id,
                        "ignorenfo": False 
                    },
                    "id": 1
                }
                xbmc.executeJSONRPC(json.dumps(refresh_req))
                xbmc.log(f"Triggered RefreshMovie for movieid {movie_id}", xbmc.LOGINFO)
            else:
                xbmc.log(f"Could not find movieid for '{path_str}'. Fallback to UpdateLibrary scan.", xbmc.LOGWARNING)
                # Fallback: scan the parent folder
                parent_dir = strm_path.parent
                xbmc.executebuiltin(f'UpdateLibrary(video, {parent_dir})')

        except Exception as e:
            xbmc.log(f"Error refreshing metadata for '{strm_path}': {e}", xbmc.LOGERROR)

