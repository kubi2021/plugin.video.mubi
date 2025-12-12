import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import webbrowser
from urllib.parse import urlencode
import xbmcvfs
from pathlib import Path
import threading
from typing import Optional
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
            # Get client country for sync menu label
            sync_label, sync_description = self._get_sync_menu_label()
            worldwide_label, worldwide_description = self._get_sync_worldwide_menu_label()
            return [
                {"label": "Browse your Mubi watchlist", "description": "Browse your Mubi watchlist", "action": "watchlist", "is_folder": True},
                {"label": sync_label, "description": sync_description, "action": "sync_locally", "is_folder": False},
                {"label": worldwide_label, "description": worldwide_description, "action": "sync_worldwide", "is_folder": False},
                {"label": "Log Out", "description": "Log out from your Mubi account", "action": "log_out", "is_folder": False}
            ]
        else:
            return [
                {"label": "Log In", "description": "Log in to your Mubi account", "action": "log_in", "is_folder": False}
            ]

    def _get_sync_menu_label(self) -> tuple:
        """
        Get the sync menu label with the client country name.
        Returns a tuple of (label, description with help info).
        """
        from .countries import COUNTRIES
        try:
            country_code = self.plugin.getSetting("client_country")
            if country_code:
                country_data = COUNTRIES.get(country_code.lower(), {})
                country_name = country_data.get("name", country_code.upper())
            else:
                country_name = "your country"
            label = f"Sync MUBI catalogue from {country_name}"
            # Include help info in description - shown when item is selected
            description = (
                f"Sync films available in {country_name} to your Kodi library.\n\n"
                f"Note: MUBI films not available in the {country_name} catalogue "
                f"will be removed from your library.\n\n"
                f"You can change your country in Settings."
            )
            return label, description
        except Exception:
            return "Sync MUBI catalogue", "Sync films to your Kodi library"

    def _get_sync_worldwide_menu_label(self) -> tuple:
        """
        Get the worldwide sync menu label and description.
        Returns a tuple of (label, description with help info).
        """
        # Try to get coverage stats for a more informative label
        try:
            from .coverage_optimizer import get_coverage_stats
            country_code = self.plugin.getSetting("client_country") or "CH"
            stats = get_coverage_stats(country_code)
            if stats:
                optimal_count = stats.get('optimal_country_count', 0)
                total_films = stats.get('total_films', 0)
                label = f"Sync MUBI worldwide (about 2k films)"
                description = (
                    f"Sync all {total_films} films from MUBI's worldwide catalogue.\n\n"
                    f"Uses smart optimization: only {optimal_count} countries needed "
                    f"for 100% coverage.\n\n"
                    f"No VPN needed to sync, but a VPN is required to play "
                    f"movies outside of your country."
                )
                return label, description
        except Exception:
            pass

        # Fallback if stats not available
        label = "Sync MUBI catalogue worldwide"
        description = (
            "Sync films from all MUBI catalogues worldwide.\n\n"
            "Note: This will take more time than syncing from a single country.\n\n"
            "No VPN is needed to complete the catalogue, but a VPN will be "
            "required to play movies outside of your country."
        )
        return label, description

    def _get_client_country_name(self) -> str:
        """Get the client country name from settings."""
        from .countries import COUNTRIES
        try:
            country_code = self.plugin.getSetting("client_country")
            if country_code:
                country_data = COUNTRIES.get(country_code.lower(), {})
                return country_data.get("name", country_code.upper())
            return "your country"
        except Exception:
            return "your country"

    def _confirm_sync(self) -> bool:
        """
        Show a confirmation dialog before sync with help information.
        Returns True if user confirms, False otherwise.
        """
        country_name = self._get_client_country_name()

        dialog = xbmcgui.Dialog()
        message = (
            f"This will sync the MUBI catalogue from [B]{country_name}[/B] "
            f"to your Kodi library.\n\n"
            f"[COLOR yellow]Important:[/COLOR]\n"
            f"• Films not available in {country_name} will be removed\n"
            f"• Change your country in Settings if needed"
        )

        # yesno returns True if user clicks Yes, False if No
        result = dialog.yesno(
            "MUBI Sync",
            message,
            yeslabel="Start Sync",
            nolabel="Cancel"
        )

        return result

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

            # Kodi 20+ (Nexus) features: Countries
            if hasattr(film.metadata, 'country') and film.metadata.country:
                countries = film.metadata.country
                if isinstance(countries, str):
                    countries = [countries]
                info_tag.setCountries(countries)  # Expects a list

            # Kodi 20+ (Nexus) features: Premiered date (preferred over year)
            if hasattr(film.metadata, 'premiered') and film.metadata.premiered:
                info_tag.setPremiered(film.metadata.premiered)

            # Kodi 20+ (Nexus) features: Content rating (MPAA)
            if hasattr(film.metadata, 'mpaa') and film.metadata.mpaa:
                info_tag.setMpaa(film.metadata.mpaa)

            # Kodi 20+ (Nexus) features: Content warnings as tags
            if hasattr(film.metadata, 'content_warnings') and film.metadata.content_warnings:
                tags = [str(w).strip() for w in film.metadata.content_warnings if w and str(w).strip()]
                if tags:
                    info_tag.setTags(tags)

            # Kodi 20+ (Nexus) features: Press quote as tagline
            if hasattr(film.metadata, 'tagline') and film.metadata.tagline:
                info_tag.setTagLine(film.metadata.tagline)

            # Kodi 20+ (Nexus) features: Audio and subtitle stream details
            self._add_stream_details(info_tag, film.metadata)

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

    def _add_stream_details(self, info_tag, metadata):
        """
        Add audio and subtitle stream details to InfoTagVideo (Kodi 20+ feature).

        Uses xbmc.AudioStreamDetail and xbmc.SubtitleStreamDetail for proper stream info.
        """
        try:
            # Add audio streams with language and channel information
            if hasattr(metadata, 'audio_languages') and metadata.audio_languages:
                audio_channels = getattr(metadata, 'audio_channels', [])
                for i, lang in enumerate(metadata.audio_languages):
                    if lang and str(lang).strip():
                        # Determine channel count from audio_channels if available
                        channels = 2  # Default to stereo
                        if i < len(audio_channels) and audio_channels[i]:
                            channel_str = str(audio_channels[i]).strip().lower()
                            if channel_str == '5.1':
                                channels = 6
                            elif channel_str == '7.1':
                                channels = 8
                            elif channel_str in ('stereo', '2.0'):
                                channels = 2
                            elif channel_str in ('mono', '1.0'):
                                channels = 1

                        # Create AudioStreamDetail (Kodi 20+)
                        audio_stream = xbmc.AudioStreamDetail(
                            channels=channels,
                            language=str(lang).strip()
                        )
                        info_tag.addAudioStream(audio_stream)

            # Add subtitle streams with language information
            if hasattr(metadata, 'subtitle_languages') and metadata.subtitle_languages:
                for lang in metadata.subtitle_languages:
                    if lang and str(lang).strip():
                        # Create SubtitleStreamDetail (Kodi 20+)
                        subtitle_stream = xbmc.SubtitleStreamDetail(
                            language=str(lang).strip()
                        )
                        info_tag.addSubtitleStream(subtitle_stream)

        except Exception as e:
            xbmc.log(f"Error adding stream details: {e}", xbmc.LOGDEBUG)






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



    def _get_available_countries_from_nfo(self, film_id: str) -> list:
        """
        Read the available countries from the NFO file for a given film.

        :param film_id: The MUBI film ID.
        :return: List of uppercase country codes where the film is available.
        """
        import xml.etree.ElementTree as ET
        import re
        from pathlib import Path

        plugin_userdata_path = Path(xbmcvfs.translatePath(self.plugin.getAddonInfo("profile")))

        # Search for NFO file containing this film_id
        for film_folder in plugin_userdata_path.iterdir():
            if not film_folder.is_dir():
                continue

            # Find NFO file in the folder
            nfo_files = list(film_folder.glob("*.nfo"))
            if not nfo_files:
                continue

            nfo_file = nfo_files[0]
            try:
                tree = ET.parse(nfo_file)
                root = tree.getroot()

                # Check if this NFO matches the film_id (look for the STRM file or film ID)
                # We can check the STRM file content or look for uniqueid
                uniqueid = root.find(".//uniqueid[@type='mubi']")
                if uniqueid is not None and uniqueid.text == film_id:
                    # Found the right film, extract countries
                    mubi_availability = root.find("mubi_availability")
                    if mubi_availability is not None:
                        countries = [c.get("code") for c in mubi_availability.findall("country")]
                        xbmc.log(f"Found NFO for film_id {film_id} via uniqueid: {nfo_file}", xbmc.LOGDEBUG)
                        return [c for c in countries if c]  # Filter out None values
                    return []

                # Alternative: check STRM file for exact film_id match
                # Use regex to match film_id= followed by the exact ID and then & or end of string
                strm_files = list(film_folder.glob("*.strm"))
                if strm_files:
                    strm_content = strm_files[0].read_text()
                    # Match exact film_id parameter (e.g., film_id=90& or film_id=90 at end)
                    pattern = rf"film_id={re.escape(str(film_id))}(&|$)"
                    if re.search(pattern, strm_content):
                        # Found the right film
                        mubi_availability = root.find("mubi_availability")
                        if mubi_availability is not None:
                            countries = [c.get("code") for c in mubi_availability.findall("country")]
                            xbmc.log(f"Found NFO for film_id {film_id} via STRM: {nfo_file}", xbmc.LOGDEBUG)
                            return [c for c in countries if c]
                        return []

            except (ET.ParseError, OSError) as e:
                xbmc.log(f"Error parsing NFO file {nfo_file}: {e}", xbmc.LOGWARNING)
                continue

        xbmc.log(f"No NFO file found for film_id {film_id}", xbmc.LOGWARNING)
        return []

    def _get_vpn_suggestions(self, available_countries: list, max_suggestions: int = 3) -> list:
        """
        Get VPN country suggestions sorted by best VPN tier (fastest infrastructure).

        :param available_countries: List of uppercase country codes where the film is available.
        :param max_suggestions: Maximum number of suggestions to return.
        :return: List of tuples (country_code, country_name, vpn_tier).
        """
        from .countries import COUNTRIES

        suggestions = []
        for code in available_countries:
            code_lower = code.lower()
            if code_lower in COUNTRIES:
                country_data = COUNTRIES[code_lower]
                suggestions.append((
                    code,
                    country_data["name"],
                    country_data.get("vpn_tier", 4)
                ))

        # Sort by VPN tier (lower is better), then alphabetically by name
        suggestions.sort(key=lambda x: (x[2], x[1]))

        return suggestions[:max_suggestions]

    def play_mubi_video(self, film_id: str = None, web_url: str = None, country: str = None):
        """
        Play a Mubi video using the secure URL and DRM handling.
        Checks country availability before playback and suggests VPN if needed.
        If playback fails, prompt the user to open the video in an external web browser.

        :param film_id: Video ID
        :param web_url: Web URL of the film
        :param country: Deprecated - country info is now read from NFO files.
        """
        from .countries import COUNTRIES

        try:
            xbmc.log(f"play_mubi_video called with handle: {self.handle}", xbmc.LOGDEBUG)

            if film_id is None:
                xbmc.log("Error: film_id is missing", xbmc.LOGERROR)
                xbmcgui.Dialog().notification("MUBI", "Error: film_id is missing.", xbmcgui.NOTIFICATION_ERROR)
                return

            # Step 1: Detect current client country from MUBI API
            current_country = self.mubi.get_cli_country()
            xbmc.log(f"Current client country detected: {current_country}", xbmc.LOGINFO)

            # Step 2: Get available countries from NFO file
            available_countries = self._get_available_countries_from_nfo(film_id)
            xbmc.log(f"Film {film_id} available in countries: {available_countries}", xbmc.LOGINFO)

            # Step 3: Check if current country is in available countries
            if available_countries and current_country.upper() not in available_countries:
                # Get country name for display
                current_country_name = COUNTRIES.get(current_country.lower(), {}).get("name", current_country)

                # Get VPN suggestions (top 3 countries sorted by best VPN tier)
                vpn_suggestions = self._get_vpn_suggestions(available_countries)

                if vpn_suggestions:
                    vpn_countries = ", ".join([f"{s[1]}" for s in vpn_suggestions])
                    message = (
                        f"This movie is not available in {current_country_name}.\n\n"
                        f"Connect to a VPN in one of these countries:\n{vpn_countries}"
                    )
                else:
                    message = f"This movie is not available in {current_country_name}."

                xbmc.log(f"Film not available in {current_country}: {message}", xbmc.LOGINFO)
                xbmcgui.Dialog().ok("MUBI - Not Available", message)
                return

            # Step 4: Proceed with playback
            stream_info = self.mubi.get_secure_stream_info(film_id)
            xbmc.log(f"Stream info for film_id {film_id}: {stream_info}", xbmc.LOGDEBUG)

            if 'error' in stream_info:
                error_msg = stream_info['error']
                xbmc.log(f"Error in stream info: {error_msg}", xbmc.LOGERROR)

                # If geo-restriction error and we have availability data, show VPN suggestions
                if 'VPN' in error_msg and available_countries:
                    current_country_name = COUNTRIES.get(current_country.lower(), {}).get("name", current_country)
                    vpn_suggestions = self._get_vpn_suggestions(available_countries)
                    if vpn_suggestions:
                        vpn_countries = ", ".join([s[1] for s in vpn_suggestions])
                        message = (
                            f"This movie is not available in {current_country_name}.\n\n"
                            f"Connect to a VPN in one of these countries:\n{vpn_countries}"
                        )
                        xbmcgui.Dialog().ok("MUBI - Not Available", message)
                        return

                # Check if this is a geo-restriction error (contains VPN message)
                if 'VPN' in error_msg:
                    # Show a dialog for geo-restriction, no browser option
                    xbmcgui.Dialog().ok("MUBI", error_msg)
                    return  # Exit without offering browser option
                else:
                    # For other errors, raise exception to trigger browser option
                    xbmcgui.Dialog().notification("MUBI", f"Error: {error_msg}", xbmcgui.NOTIFICATION_ERROR)
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

            # Prompt the user to open in browser (only for non-geo-restriction errors)
            if web_url:
                if xbmcgui.Dialog().yesno("MUBI", "Failed to play the video. Do you want to open it in a web browser?"):
                    self.play_video_ext(web_url)
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



    def sync_films(self, countries: list, dialog_title: Optional[str] = None):
        """
        Sync MUBI films locally by fetching films from specified countries.
        Creates STRM and NFO files for each film to import into Kodi's library.

        :param countries: List of ISO 3166-1 alpha-2 country codes (uppercase) to sync from.
        :param dialog_title: Optional title for the progress dialog.

        Level 2 Bug Fix: Added concurrency protection to prevent multiple sync operations.
        """
        from .countries import COUNTRIES

        # BUG #7 FIX: Check if sync is already in progress
        with NavigationHandler._sync_lock:
            if NavigationHandler._sync_in_progress:
                xbmcgui.Dialog().notification(
                    "MUBI",
                    "Sync already in progress. Please wait for it to complete.",
                    xbmcgui.NOTIFICATION_INFO,
                    5000
                )
                xbmc.log("Sync operation blocked - another sync already in progress", xbmc.LOGINFO)
                return None

            NavigationHandler._sync_in_progress = True

        try:
            # Check if metadata providers are configured
            from .external_metadata import MetadataProviderFactory

            # Check if configuration is valid and provider is reachable
            provider = MetadataProviderFactory.get_provider()
            
            if not provider:
                dialog = xbmcgui.Dialog()
                # Show a message with options to either go to settings or cancel
                ret = dialog.yesno(
                    "Metadata Provider Required",
                    "To provide rich metadata (posters, ratings, etc.) in your Kodi library, "
                    "you need to configure an external metadata provider.\n\n"
                    "Please execute the Settings to configure TMDB (free) or OMDb API key.",
                    yeslabel="Go to Settings",
                    nolabel="Cancel"
                )

                if ret:
                    MetadataProviderFactory.open_settings()
                    # Re-validate after user closes settings
                    provider = MetadataProviderFactory.get_provider()
                    if not provider:
                         return
                else:
                    return

            # Test connection for the selected provider
            xbmcgui.Dialog().notification("MUBI", f"Verifying {provider.provider_name} API key...", xbmcgui.NOTIFICATION_INFO, 2000)
            if not provider.test_connection():
                xbmcgui.Dialog().notification(
                    "MUBI", 
                    f"Invalid API Key for {provider.provider_name}. Sync aborted.", 
                    xbmcgui.NOTIFICATION_ERROR,
                    5000
                )
                xbmc.log(f"Sync aborted: Invalid API key for {provider.provider_name}", xbmc.LOGERROR)
                
                # Release lock before return since we are inside the 'with lock' logically (handled by caller logic if we used 'with', but here we set boolean)
                # ERROR: The original code sets `_sync_in_progress = True` BEFORE this check (line 790).
                # We simply return, so we MUST reset the lock flag.
                with NavigationHandler._sync_lock:
                    NavigationHandler._sync_in_progress = False
                return

            # Validate countries list
            if not countries:
                xbmcgui.Dialog().notification(
                    "MUBI", "No countries specified for sync.",
                    xbmcgui.NOTIFICATION_ERROR
                )
                return

            # Determine dialog title
            num_countries = len(countries)
            if dialog_title is None:
                if num_countries == 1:
                    country_data = COUNTRIES.get(countries[0].lower(), {})
                    country_name = country_data.get("name", countries[0])
                    dialog_title = f"Syncing MUBI from {country_name}"
                else:
                    dialog_title = f"Syncing MUBI from {num_countries} countries"

            xbmc.log(f"Starting film sync from {num_countries} countries: {countries}", xbmc.LOGINFO)

            # Proceed with the sync process
            pDialog = xbmcgui.DialogProgress()
            pDialog.create(dialog_title, "Initializing...")

            # Define progress callback for dynamic updates
            def update_fetch_progress(current_films, total_films, current_country, total_countries, country_code):
                if pDialog.iscanceled():
                    raise Exception("User canceled sync operation")

                # Calculate percentage based on country progress for multi-country,
                # or film count for single country
                # Use full 0-100% range since file creation has its own dialog
                if total_countries > 1:
                    percent = min(int((current_country / total_countries) * 100), 99)
                    country_name = COUNTRIES.get(country_code.lower(), {}).get("name", country_code)
                    message = f"Fetching from {country_name} ({current_country}/{total_countries})...\n{current_films} films found"
                else:
                    percent = min(int((current_films / 1000) * 100), 99) if current_films > 0 else 0
                    country_name = COUNTRIES.get(country_code.lower(), {}).get("name", country_code)
                    message = f"Fetching films from {country_name}...\n{current_films} films found"

                pDialog.update(percent, message)

            # Sync from specified countries
            try:
                all_films_library = self.mubi.get_all_films(
                    playable_only=True,
                    progress_callback=update_fetch_progress,
                    countries=countries
                )
            except Exception as e:
                if "canceled" in str(e).lower():
                    pDialog.close()
                    xbmc.log("User canceled the sync process during film fetching.", xbmc.LOGDEBUG)
                    return None
                else:
                    raise

            # Update progress dialog for file creation phase
            filtered_films_count = len(all_films_library.films)
            if num_countries > 1:
                pDialog.update(100, f"Fetched {filtered_films_count} films from {num_countries} countries, creating local files...")
            else:
                pDialog.update(100, f"Fetched {filtered_films_count} films, creating local files...")
            xbmc.log(f"Successfully fetched {filtered_films_count} films", xbmc.LOGINFO)

            if pDialog.iscanceled():
                pDialog.close()
                xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                return None

            plugin_userdata_path = Path(xbmcvfs.translatePath(self.plugin.getAddonInfo("profile")))

            # Close the progress dialog before starting file creation
            pDialog.close()

            # Small delay to ensure dialog is fully closed before next phase
            import time
            time.sleep(0.1)

            # Sync files locally
            all_films_library.sync_locally(
                self.base_url, plugin_userdata_path
            )

            # Trigger library operations
            monitor = LibraryMonitor()
            self.clean_kodi_library(monitor)
            self.update_kodi_library()

        except Exception as e:
            xbmc.log(f"Error during sync: {e}", xbmc.LOGERROR)
        finally:
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

