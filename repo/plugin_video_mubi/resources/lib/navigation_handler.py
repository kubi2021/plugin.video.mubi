import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import webbrowser
from urllib.parse import urlencode
import xbmcvfs
from pathlib import Path
import threading
from .library import Library
from .playback import play_with_inputstream_adaptive

class LibraryMonitor(xbmc.Monitor):
    def __init__(self):
        super(LibraryMonitor, self).__init__()
        self.clean_finished = False
        self.scan_finished = False

    def onCleanFinished(self, library):
        if library == 'video':
            xbmc.log("Library clean finished.", xbmc.LOGDEBUG)
            self.clean_finished = True

    def onScanFinished(self, library):
        if library == 'video':
            xbmc.log("Library scan (update) finished.", xbmc.LOGDEBUG)
            self.scan_finished = True

class NavigationHandler:
    """
    Handles all navigation and UI interactions within Kodi for the Mubi plugin.
    """

    # Class-level lock for sync operations (shared across all instances)
    _sync_lock = threading.Lock()
    _sync_in_progress = False

    def __init__(self, handle: int, base_url: str, mubi, session):
        """
        Initialize the NavigationHandler with necessary dependencies.

        :param handle: Plugin handle provided by Kodi
        :param base_url: Base URL of the plugin
        :param mubi: Instance of the Mubi API interaction class
        :param session: Instance of the session manager
        """
        self.handle = handle
        self.base_url = base_url
        self.mubi = mubi
        self.session = session
        self.plugin = xbmcaddon.Addon()

        # Log the handle when NavigationHandler is initialized
        xbmc.log(f"NavigationHandler initialized with handle: {self.handle}", xbmc.LOGDEBUG)


    def get_url(self, **kwargs) -> str:
        """
        Create a plugin URL with the given keyword arguments.

        :param kwargs: Keyword arguments for the URL
        :return: Formatted URL string
        """
        return f"{self.base_url}?{urlencode(kwargs)}"

    def main_navigation(self):
        """
        Build the main navigation menu presented to the user.
        """
        try:
            self.session.is_logged_in = self.plugin.getSettingBool('logged') and self.session.token
            xbmcplugin.setPluginCategory(self.handle, "Mubi")
            xbmcplugin.setContent(self.handle, "videos")

            main_navigation_items = self._get_main_menu_items()
            
            for item in main_navigation_items:
                self._add_menu_item(item)

            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            xbmc.log(f"Error in main navigation: {e}", xbmc.LOGERROR)

    def _get_main_menu_items(self) -> list:
        """ Helper method to retrieve main menu items based on login status. """
        if self.session.is_logged_in:
            return [
                {"label": "Browse your Mubi watchlist", "description": "Browse your Mubi watchlist", "action": "watchlist", "is_folder": True},
                {"label": "Sync all Mubi films locally", "description": "Sync Mubi films locally", "action": "sync_locally", "is_folder": True},
                {"label": "Log Out", "description": "Log out from your Mubi account", "action": "log_out", "is_folder": False}
            ]
        else:
            return [
                {"label": "Log In", "description": "Log in to your Mubi account", "action": "log_in", "is_folder": False}
            ]

    def _add_menu_item(self, item: dict):
        try:
            list_item = xbmcgui.ListItem(label=item["label"])
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(item["label"])
            info_tag.setPlot(item["description"])
            info_tag.setMediaType("video")
            url = self.get_url(action=item["action"])
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, item["is_folder"])
        except Exception as e:
            xbmc.log(f"Error adding menu item {item['label']}: {e}", xbmc.LOGERROR)





    def list_watchlist(self):
        """
        List videos in your watchlist.

        """
        try:
            xbmcplugin.setContent(self.handle, "videos")

            library = self.mubi.get_watch_list()

            for film in library.films:
                self._add_film_item(film)

            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            xbmc.log(f"Error listing videos: {e}", xbmc.LOGERROR)



    def _add_film_item(self, film):
        try:
            list_item = xbmcgui.ListItem(label=film.title)
            info_tag = list_item.getVideoInfoTag()

            # Set basic metadata
            info_tag.setTitle(film.title)

            if hasattr(film.metadata, 'originaltitle') and film.metadata.originaltitle:
                info_tag.setOriginalTitle(film.metadata.originaltitle)

            if hasattr(film.metadata, 'genre') and film.metadata.genre:
                genres = film.metadata.genre
                if isinstance(genres, str):
                    genres = [genres]
                info_tag.setGenres(genres)  # Expects a list

            if hasattr(film.metadata, 'plot') and film.metadata.plot:
                info_tag.setPlot(film.metadata.plot)

            if hasattr(film.metadata, 'year') and film.metadata.year:
                info_tag.setYear(int(film.metadata.year))

            if hasattr(film.metadata, 'duration') and film.metadata.duration:
                info_tag.setDuration(int(film.metadata.duration))  # Duration in seconds

            if hasattr(film.metadata, 'director') and film.metadata.director:
                directors = film.metadata.director
                if isinstance(directors, str):
                    directors = [directors]
                info_tag.setDirectors(directors)  # Expects a list

            if hasattr(film.metadata, 'cast') and film.metadata.cast:
                info_tag.setCast(film.metadata.cast)  # Expects a list of dicts with 'name' keys

            if hasattr(film.metadata, 'rating') and film.metadata.rating:
                info_tag.setRating(float(film.metadata.rating))

            if hasattr(film.metadata, 'votes') and film.metadata.votes:
                info_tag.setVotes(int(film.metadata.votes))

            if hasattr(film.metadata, 'imdb_id') and film.metadata.imdb_id:
                info_tag.setUniqueID(film.metadata.imdb_id, 'imdb')

            info_tag.setMediaType('movie')

            # Set artwork
            if hasattr(film.metadata, 'image') and film.metadata.image:
                list_item.setArt({
                    "thumb": film.metadata.image,
                    "poster": film.metadata.image,
                    "fanart": film.metadata.image,
                    "landscape": film.metadata.image
                })

            # Set 'IsPlayable' property to inform Kodi this is a playable item
            list_item.setProperty('IsPlayable', 'true')

            # Set the URL and path to the plugin URL
            url = self.get_url(action="play_mubi_video", film_id=film.mubi_id)
            list_item.setPath(url)

            # Add the item to the directory with isFolder=False
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, isFolder=False)

        except Exception as e:
            xbmc.log(f"Error adding film item {film.title}: {e}", xbmc.LOGERROR)
            import traceback
            xbmc.log(traceback.format_exc(), xbmc.LOGERROR)






    def _is_safe_url(self, url: str) -> bool:
        """
        Validate if a URL is safe to open externally.

        :param url: URL to validate
        :return: True if URL is safe, False otherwise
        """
        try:
            from urllib.parse import urlparse

            # Parse the URL
            parsed = urlparse(url)

            # Check for valid scheme (http/https only)
            if parsed.scheme not in ['http', 'https']:
                xbmc.log(f"Unsafe URL scheme: {parsed.scheme}", xbmc.LOGWARNING)
                return False

            # Check for valid hostname
            if not parsed.netloc:
                xbmc.log("URL missing hostname", xbmc.LOGWARNING)
                return False

            # Block localhost and private IP ranges for security
            hostname = parsed.hostname
            netloc = parsed.netloc.lower() if parsed.netloc else ""

            # Check for dangerous characters in netloc (hostname:port)
            dangerous_chars = [';', '|', '&', '`', '$']
            # Note: Parentheses might appear in some valid URLs
            for char in dangerous_chars:
                if char in netloc:
                    xbmc.log(f"Blocked URL with dangerous character '{char}' in netloc", xbmc.LOGWARNING)
                    return False

            if hostname:
                hostname = hostname.lower()
                if hostname in ['localhost', '127.0.0.1', '::1', '0.0.0.0', '[::]']:
                    xbmc.log(f"Blocked localhost URL: {hostname}", xbmc.LOGWARNING)
                    return False

                # Block private IP ranges and cloud metadata services
                blocked_prefixes = [
                    '192.168.',  # Private Class C
                    '10.',       # Private Class A
                    '172.16.', '172.17.', '172.18.', '172.19.',  # Private Class B
                    '172.20.', '172.21.', '172.22.', '172.23.',
                    '172.24.', '172.25.', '172.26.', '172.27.',
                    '172.28.', '172.29.', '172.30.', '172.31.',
                    '169.254.',  # Link-local (AWS/Azure metadata)
                    '100.64.',   # Carrier-grade NAT
                ]

                for prefix in blocked_prefixes:
                    if hostname.startswith(prefix):
                        xbmc.log(f"Blocked private/metadata IP URL: {hostname}", xbmc.LOGWARNING)
                        return False

            # Check for dangerous characters in URL path that could indicate injection
            if parsed.path:
                dangerous_chars = [';', '|', '&', '`', '$']
                # Note: Parentheses are common in URLs and generally safe
                for char in dangerous_chars:
                    if char in parsed.path:
                        xbmc.log(f"Blocked URL with dangerous character '{char}' in path", xbmc.LOGWARNING)
                        return False

            return True

        except Exception as e:
            xbmc.log(f"Error validating URL safety: {e}", xbmc.LOGERROR)
            return False

    def play_video_ext(self, web_url: str):
        """
        Open a web URL using the appropriate system command.

        :param web_url: Web URL of the video
        """
        try:
            xbmc.log(f"Opening external video URL: {web_url}", xbmc.LOGDEBUG)

            # Validate URL safety
            if not self._is_safe_url(web_url):
                xbmcgui.Dialog().ok("MUBI", "Invalid or unsafe URL provided.")
                return
            
            import subprocess
            import os
            
            if xbmc.getCondVisibility('System.Platform.Windows'):
                # Windows platform
                os.startfile(web_url)
            elif xbmc.getCondVisibility('System.Platform.OSX'):
                # macOS platform
                subprocess.Popen(['open', web_url], shell=False)
            elif xbmc.getCondVisibility('System.Platform.Linux'):
                # Linux platform
                subprocess.Popen(['xdg-open', web_url], shell=False)
            elif xbmc.getCondVisibility('System.Platform.Android'):
                # Android platform
                xbmc.executebuiltin(f'StartAndroidActivity("", "", "android.intent.action.VIEW", "{web_url}")')
            else:
                # Unsupported platform
                xbmcgui.Dialog().ok("MUBI", "Cannot open web browser on this platform.")
        except Exception as e:
            xbmc.log(f"Error opening external video: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("MUBI", f"Error opening external video: {e}")



    def play_mubi_video(self, film_id: str = None, web_url: str = None):
        """
        Play a Mubi video using the secure URL and DRM handling.
        If playback fails, prompt the user to open the video in an external web browser.

        :param film_id: Video ID
        :param web_url: Web URL of the film
        """
        try:
            xbmc.log(f"play_mubi_video called with handle: {self.handle}", xbmc.LOGDEBUG)

            if film_id is None:
                xbmc.log(f"Error: film_id is missing", xbmc.LOGERROR)
                xbmcgui.Dialog().notification("MUBI", "Error: film_id is missing.", xbmcgui.NOTIFICATION_ERROR)
                return

            # Get secure stream info from Mubi API
            stream_info = self.mubi.get_secure_stream_info(film_id)
            xbmc.log(f"Stream info for film_id {film_id}: {stream_info}", xbmc.LOGDEBUG)

            if 'error' in stream_info:
                xbmc.log(f"Error in stream info: {stream_info['error']}", xbmc.LOGERROR)
                xbmcgui.Dialog().notification("MUBI", f"Error: {stream_info['error']}", xbmcgui.NOTIFICATION_ERROR)
                raise Exception("Error in stream info")

            # Select the best stream URL
            best_stream_url = self.mubi.select_best_stream(stream_info)
            xbmc.log(f"Selected best stream URL: {best_stream_url}", xbmc.LOGDEBUG)

            if not best_stream_url:
                xbmc.log("Error: No suitable stream found.", xbmc.LOGERROR)
                xbmcgui.Dialog().notification("MUBI", "Error: No suitable stream found.", xbmcgui.NOTIFICATION_ERROR)
                raise Exception("No suitable stream found")

            # Extract subtitle tracks
            subtitles = stream_info.get('text_track_urls', [])
            xbmc.log(f"Available subtitles: {subtitles}", xbmc.LOGDEBUG)

            # Play video using InputStream Adaptive
            xbmc.log(f"Calling play_with_inputstream_adaptive with handle: {self.handle}, stream URL: {best_stream_url}", xbmc.LOGDEBUG)
            play_with_inputstream_adaptive(self.handle, best_stream_url, stream_info['license_key'], subtitles,
                                         self.session.token, self.session.user_id)

        except Exception as e:
            xbmc.log(f"Error playing Mubi video: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification("MUBI", "An unexpected error occurred.", xbmcgui.NOTIFICATION_ERROR)

            # Prompt the user
            if web_url:
                if xbmcgui.Dialog().yesno("MUBI", "Failed to play the video. Do you want to open it in a web browser?"):
                    self.play_video_ext(web_url)
                else:
                    pass  # User chose not to open in web browser
            else:
                xbmcgui.Dialog().notification("MUBI", "Unable to open in web browser. Web URL is missing.", xbmcgui.NOTIFICATION_ERROR)





    def play_trailer(self, url: str):
        """
        Play a trailer video within Kodi.

        :param url: URL of the trailer video
        """
        try:
            play_item = xbmcgui.ListItem(path=url)
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)
        except Exception as e:
            xbmc.log(f"Error playing trailer: {e}", xbmc.LOGERROR)



    def log_in(self):
        """
        Handle user login by generating a link code and authenticating with Mubi.
        """
        try:
            code_info = self.mubi.get_link_code()
            if 'auth_token' in code_info and 'link_code' in code_info:
                self._display_login_code(code_info)
                auth_response = self.mubi.authenticate(code_info['auth_token'])

                if auth_response and 'token' in auth_response:
                    # Token and user ID are already set in session inside authenticate method
                    xbmcgui.Dialog().notification("MUBI", "Successfully logged in!", xbmcgui.NOTIFICATION_INFO)
                    xbmc.executebuiltin('Container.Refresh')
                else:
                    self._handle_login_error(auth_response)
            else:
                xbmcgui.Dialog().notification('MUBI', 'Error during code generation.', xbmcgui.NOTIFICATION_ERROR)

        except Exception as e:
            xbmc.log(f"Exception during login: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('MUBI', 'An unexpected error occurred during login.', xbmcgui.NOTIFICATION_ERROR)



    def _display_login_code(self, code_info: dict):
        """ Helper method to display login code to the user """
        link_code = code_info['link_code']
        xbmcgui.Dialog().ok("Log In", f"Enter code [COLOR=yellow][B]{link_code}[/B][/COLOR] on [B]https://mubi.com/android[/B]")

    def _handle_login_error(self, auth_response: dict):
        """ Handle login errors from the Mubi API """
        error_message = auth_response.get('message', 'Unknown error')
        xbmcgui.Dialog().notification('MUBI', f"Error: {error_message}", xbmcgui.NOTIFICATION_ERROR)

    def log_out(self):
        """
        Handle user logout from Mubi.
        """
        try:
            success = self.mubi.log_out()
            if success:
                self.session.set_logged_out()
                xbmcgui.Dialog().notification("MUBI", "Successfully logged out!", xbmcgui.NOTIFICATION_INFO)
                xbmc.executebuiltin('Container.Refresh')
            else:
                xbmcgui.Dialog().notification('MUBI', 'Error during logout. You are still logged in.', xbmcgui.NOTIFICATION_ERROR)
        except Exception as e:
            xbmc.log(f"Error during logout: {e}", xbmc.LOGERROR)

    def _check_omdb_api_key(self):
        """
        Check if OMDb API key is configured and handle missing key scenario.

        :return: OMDb API key if present, None if missing or user cancels
        """
        try:
            # Retrieve the OMDb API key from the settings
            omdb_api_key = self.plugin.getSetting("omdbapiKey")

            # Check if the OMDb API key is missing
            if not omdb_api_key:
                dialog = xbmcgui.Dialog()

                # Show a message with options to either go to settings or cancel
                ret = dialog.yesno(
                    "OMDb API Key Missing",
                    "OMDB Key is needed to provide rich metadata in your Kodi library. Get it for free here [B]omdbapi.com/apikey.aspx[/B]\n"
                    "Would you like to go to the plugin settings now?",
                    yeslabel="Go to Settings",
                    nolabel="Cancel"
                )

                if ret:  # If the user clicks 'Go to Settings'
                    self.plugin.openSettings()  # Opens the settings for the user to add the OMDb API key
                return None  # Return None if the OMDb API key is missing or the user cancels

            return omdb_api_key
        except Exception as e:
            xbmc.log(f"Error during OMDb API key check: {e}", xbmc.LOGERROR)
            return None

    def sync_locally(self):
        """
        Sync all Mubi films locally by fetching all films directly and creating STRM and NFO files for each film.
        This allows the films to be imported into Kodi's standard media library.

        Level 2 Bug Fix: Added concurrency protection to prevent multiple sync operations.
        """
        # BUG #7 FIX: Check if sync is already in progress
        with NavigationHandler._sync_lock:
            if NavigationHandler._sync_in_progress:
                # User-friendly notification about sync already running
                xbmcgui.Dialog().notification(
                    "MUBI",
                    "Sync already in progress. Please wait for it to complete.",
                    xbmcgui.NOTIFICATION_INFO,
                    5000
                )
                xbmc.log("Sync operation blocked - another sync already in progress", xbmc.LOGINFO)
                return None

            # Mark sync as in progress
            NavigationHandler._sync_in_progress = True

        try:
            # Check OMDb API key
            omdb_api_key = self._check_omdb_api_key()
            if not omdb_api_key:
                return  # Exit if no API key

            # Proceed with the sync process if OMDb API key is provided
            pDialog = xbmcgui.DialogProgress()
            pDialog.create("Syncing with MUBI 1/2", "Initializing...")

            # Define progress callback for dynamic updates
            def update_fetch_progress(current_films, total_films, current_page, total_pages):
                if pDialog.iscanceled():
                    # Raise an exception to signal cancellation to get_all_films
                    raise Exception("User canceled sync operation")

                # Calculate percentage based on pages processed (use full 100% for fetching phase)
                if total_pages > 0:
                    percent = int((current_page / total_pages) * 100)  # Use full progress bar
                else:
                    percent = 50  # Fallback percentage

                # Update dialog with dynamic information - keep it simple without any counts
                message = "Fetching playable films..."
                pDialog.update(percent, message)

            # Use the new direct approach to fetch all films with progress tracking
            xbmc.log("Starting direct film sync using /browse/films endpoint", xbmc.LOGINFO)
            # For sync, we want only playable films (streamable content)
            try:
                all_films_library = self.mubi.get_all_films(playable_only=True, progress_callback=update_fetch_progress)
            except Exception as e:
                if "canceled" in str(e).lower():
                    pDialog.close()
                    xbmc.log("User canceled the sync process during film fetching.", xbmc.LOGDEBUG)
                    return None
                else:
                    raise  # Re-raise if it's not a cancellation

            # Update progress dialog for file creation phase
            filtered_films_count = len(all_films_library.films)
            pDialog.update(50, f"Fetched {filtered_films_count} films, creating local files...")
            xbmc.log(f"Successfully fetched {filtered_films_count} films using direct API approach", xbmc.LOGINFO)

            if pDialog.iscanceled():
                pDialog.close()
                xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                return None

            plugin_userdata_path = Path(xbmcvfs.translatePath(self.plugin.getAddonInfo("profile")))

            # Close the first progress dialog before starting file creation
            pDialog.close()

            # Small delay to ensure dialog is fully closed before next phase
            import time
            time.sleep(0.1)

            # Start file creation phase (no total count shown to avoid confusion)
            all_films_library.sync_locally(self.base_url, plugin_userdata_path, omdb_api_key)

            # Check if auto clean library is enabled in settings
            auto_clean_enabled = self.plugin.getSetting('auto_clean_library') == 'true'

            if auto_clean_enabled:
                # Create a monitor instance for library operations
                monitor = LibraryMonitor()

                # Trigger Kodi library clean first and wait for it to complete (blocking)
                self.clean_kodi_library(monitor)
                xbmc.log("Auto clean library is enabled - library cleaned", xbmc.LOGINFO)
            else:
                xbmc.log("Auto clean library is disabled - skipping clean", xbmc.LOGDEBUG)

            # Trigger Kodi library update in background (non-blocking)
            self.update_kodi_library()

        except Exception as e:
            xbmc.log(f"Error during sync: {e}", xbmc.LOGERROR)
        finally:
            # BUG #7 FIX: Always clear the sync flag, even if an error occurs
            with NavigationHandler._sync_lock:
                NavigationHandler._sync_in_progress = False
                xbmc.log("Sync operation completed - flag cleared", xbmc.LOGDEBUG)


    def update_kodi_library(self):
        """
        Triggers a Kodi library update to scan for new movies after the sync process.
        Library update runs in the background without blocking the UI.
        """
        try:
            xbmc.log("Triggering Kodi library update...", xbmc.LOGDEBUG)
            xbmc.executebuiltin('UpdateLibrary(video)')
            xbmc.log("Library update triggered successfully - running in background", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"Error triggering Kodi library update: {e}", xbmc.LOGERROR)


    def clean_kodi_library(self, monitor):
        """
        Triggers a Kodi library clean to remove items from the library that are not found locally.
        Waits for the clean operation to complete before returning (blocking).
        """
        try:
            xbmc.log("Triggering Kodi library clean...", xbmc.LOGDEBUG)
            xbmc.executebuiltin('CleanLibrary(video)')

            # Wait for the clean operation to finish
            xbmc.log("Waiting for library clean to complete...", xbmc.LOGDEBUG)
            while not monitor.clean_finished:
                if monitor.waitForAbort(1):  # Wait for 1 second intervals
                    xbmc.log("Abort requested during library clean wait.", xbmc.LOGDEBUG)
                    break
            xbmc.log("Library clean completed", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"Error triggering Kodi library clean: {e}", xbmc.LOGERROR)

