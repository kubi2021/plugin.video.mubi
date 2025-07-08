from pathlib import Path
import xbmc
import xbmcgui
import xbmcaddon
from resources.lib.episode import Episode
from typing import List, Optional, Tuple
import os
import shutil
from typing import Set
import re

class Serie_Library:
    def __init__(self):
        self.episodes: List[Episode] = []

    def add_episode(self, episode: Episode):
        if not episode or not episode.mubi_id or not episode.title:
            raise ValueError("Invalid episode: missing required fields (mubi_id, title).")
            xbmc.log(f"Not able to add '{episode.title}' to the library", xbmc.LOGERROR)
        if episode not in self.episodes:
            self.episodes.append(episode)
            xbmc.log(f"'{episode.title}' successfully added to the library", xbmc.LOGINFO)

    def __len__(self):
        return len(self.episodes)

    def sync_locally(self, base_url: str, plugin_userdata_path: Path, omdb_api_key: Optional[str]):
        """
        Synchronize the local library with fetched film/serie data from MUBI.

        :param base_url: The base URL for creating STRM files.
        :param plugin_userdata_path: The path where object folders are stored.
        :param omdb_api_key: The OMDb API key for fetching additional metadata.
        """
        # Initialize counters
        newly_added = 0
        failed_to_add = 0
        total_episodes = len(self.episodes)

        # Initialize progress dialog
        pDialog = xbmcgui.DialogProgress()
        pDialog.create("Syncing with MUBI", "Starting the sync...")
        xbmc.log(f"Syncing with MUBI", xbmc.LOGINFO)

        try:
            # create basefolder if it doesn't exist
            basefolder = plugin_userdata_path / "series"
            if not os.path.isdir(basefolder):
                os.makedirs(basefolder)                 

            # Process each film and update progress
            for idx, episode in enumerate(self.episodes):
                percent = int(((idx + 1) / total_episodes) * 100)  # Ensuring 100% on last episode
                pDialog.update(percent, f"Processing episode {idx + 1} of {total_episodes}:\n{episode.title}")
                xbmc.log(f"Processing episode '{episode.title}'", xbmc.LOGDEBUG)
                
                # Check if user canceled
                if pDialog.iscanceled():
                    xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                    break

                # Process episode if valid
                if self.is_episode_valid(episode):
                    result = self.prepare_files_for_episode(episode, base_url, plugin_userdata_path, omdb_api_key)
                    if result is True:
                        newly_added += 1
                    elif result is False:
                        failed_to_add += 1
                    # If result is None, the film was skipped because files already exist

            # Final cleanup of obsolete files
            obsolete_episodes_count = self.remove_obsolete_files(plugin_userdata_path)

            # Construct summary message
            message = (
                f"Sync completed successfully!\n"
                f"New episodes added: {newly_added}\n"
                f"Failed to add: {failed_to_add}\n"
                f"Obsolete episodes removed: {obsolete_episodes_count}"
            )
            
            # Log results
            xbmc.log(
                f"Sync completed. New episodes: {newly_added}, Failed episodes: {failed_to_add}, "
                f"Obsolete episodes removed: {obsolete_episodes_count}",
                xbmc.LOGDEBUG
            )
            
            # Show summary dialog
            xbmcgui.Dialog().ok("MUBI", message)
        finally:
            # Ensure the dialog is closed in the end
            pDialog.close()


    def is_episode_valid(self, episode: Episode) -> bool:
        # Check that episode has all necessary attributes
        return episode.mubi_id and episode.title

    def prepare_files_for_episode(
        self, episode: Episode, base_url: str, plugin_userdata_path: Path, omdb_api_key: Optional[str]
    ) -> Optional[bool]:
        """
        Prepare the necessary files for a given film. Creates NFO and STRM files.
        The STRM file is only created if the NFO file is successfully created.
        If the NFO file creation fails, the STRM file is not created, and the movie folder is removed.

        :param episode: The Episode object to process.
        :param base_url: The base URL for the STRM file.
        :param plugin_userdata_path: The path where Mubi folders are stored.
        :param omdb_api_key: The OMDb API key for fetching additional metadata.
        :return:
            - True if both NFO and STRM files were created successfully.
            - False if file creation failed.
            - None if files already exist and were skipped.
        """
        try:
            serie_folder_name = episode.get_sanitized_folder_name()
        except ValueError as e:
            xbmc.log(f"Invalid folder name for episode '{episode.title}': {e}", xbmc.LOGERROR)
            return False

        episode_path = plugin_userdata_path / "series" / serie_folder_name

        # Security check: Ensure the episode_path is within the expected directory
        try:
            episode_path.resolve().relative_to(plugin_userdata_path.resolve())
        except ValueError:
            xbmc.log(f"Security: Path traversal attempt blocked for episode '{episode.title}'", xbmc.LOGERROR)
            return False

        # Define file paths with additional validation
        strm_file = episode_path / f"{serie_folder_name} S{episode.season:02d}E{episode.episode_number:02d}.strm"
        nfo_file = episode_path / f"{serie_folder_name} S{episode.season:02d}E{episode.episode_number:02d}.nfo"

        # Validate that the file paths are still within the expected directory
        try:
            strm_file.resolve().relative_to(plugin_userdata_path.resolve())
            nfo_file.resolve().relative_to(plugin_userdata_path.resolve())
        except ValueError:
            xbmc.log(f"Security: File path traversal attempt blocked for episode '{episode.title}'", xbmc.LOGERROR)
            return False

        try:
            # Check if both STRM and NFO files already exist
            if strm_file.exists() and nfo_file.exists():
                xbmc.log(f"Skipping episode '{episode.title}' - files already exist.", xbmc.LOGDEBUG)
                return None  # Files already exist; no action needed
        except PermissionError as e:
            xbmc.log(f"PermissionError when accessing files for episode '{episode.title}': {e}", xbmc.LOGERROR)
            return False  # Indicate failure due to permission error

        try:
            # Create the movie folder if it doesn't exist
            episode_path.mkdir(parents=True, exist_ok=True)
            xbmc.log(f"Created folder '{episode_path}'.", xbmc.LOGDEBUG)

            # Attempt to create the NFO file first
            xbmc.log(f"Creating NFO file for episode '{episode.title}'.", xbmc.LOGDEBUG)
            episode.create_nfo_file(episode_path, base_url, omdb_api_key)

            # Verify if the NFO file was created successfully
            if not nfo_file.exists():
                xbmc.log(
                    f"Skipping creation of STRM file for '{episode.title}' as NFO file was not created.",
                    xbmc.LOGWARNING
                )
                return False  # Indicate failure in file creation

            # If NFO was created successfully, proceed to create the STRM file
            xbmc.log(f"Creating STRM file for episode '{episode.title}'.", xbmc.LOGDEBUG)
            episode.create_strm_file(episode_path, base_url)
            xbmc.log(f"Successfully created STRM file for '{episode.title}'.", xbmc.LOGDEBUG)

            return True  # Indicate successful creation of both files

        except Exception as e:
            xbmc.log(f"Error processing episode '{episode.title}': {e}", xbmc.LOGERROR)
            return False  # Indicate failure due to exception


    def remove_obsolete_files(self, plugin_userdata_path: Path) -> int:
        """
        Remove folders in plugin_userdata_path that do not correspond to any film in the library.

        :param plugin_userdata_path: Path where the film folders are stored.
        :return: The number of obsolete film folders removed.
        """
        # Get a set of sanitized folder names for the current films in the library
        current_episodes_folders = set()
        for episode in self.episodes:
            try:
                folder_name = episode.get_sanitized_folder_name()
                current_episodes_folders.add(folder_name)
            except ValueError as e:
                xbmc.log(f"Skipping episode with invalid folder name: {e}", xbmc.LOGWARNING)
                continue

        # Track obsolete folder count
        obsolete_folders_count = 0

        # Validate series directory
        series_dir = plugin_userdata_path / "series"

        # Ensure we're only operating within the expected directory
        if not series_dir.exists() or not series_dir.is_dir():
            xbmc.log("Series directory does not exist or is not a directory", xbmc.LOGWARNING)
            return 0

        # Validate that series_dir is actually within plugin_userdata_path
        try:
            series_dir.resolve().relative_to(plugin_userdata_path.resolve())
        except ValueError:
            xbmc.log("Security: Series directory is outside expected path", xbmc.LOGERROR)
            return 0

        # Loop through each directory in series_dir
        try:
            for folder in series_dir.iterdir():
                if not folder.is_dir():
                    continue

                # Additional security check for each folder
                try:
                    folder.resolve().relative_to(series_dir.resolve())
                except ValueError:
                    xbmc.log(f"Security: Skipping folder outside series directory: {folder}", xbmc.LOGWARNING)
                    continue

                # Check if folder name contains suspicious characters
                if '..' in folder.name or '/' in folder.name or '\\' in folder.name:
                    xbmc.log(f"Security: Skipping folder with suspicious name: {folder.name}", xbmc.LOGWARNING)
                    continue

                if folder.name not in current_episodes_folders:
                    try:
                        # Remove the folder if it's not in the current episodes
                        shutil.rmtree(folder)
                        obsolete_folders_count += 1
                        xbmc.log(f"Removed obsolete folder: {folder.name}", xbmc.LOGDEBUG)
                    except (OSError, PermissionError) as e:
                        xbmc.log(f"Failed to remove folder {folder.name}: {e}", xbmc.LOGERROR)
        except (OSError, PermissionError) as e:
            xbmc.log(f"Error accessing series directory: {e}", xbmc.LOGERROR)

        return obsolete_folders_count

