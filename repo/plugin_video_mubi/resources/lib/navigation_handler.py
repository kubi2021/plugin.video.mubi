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
from .library import Library
from .playback import play_with_inputstream_adaptive
import datetime
import dateutil.parser

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
            # Check fast sync setting
            enable_fast_sync = self.plugin.getSettingBool('enable_fast_sync')
            
            # Get client country for sync menu label
            sync_label, sync_description = self._get_sync_menu_label()
            worldwide_label, worldwide_description = self._get_sync_worldwide_menu_label()
            
            # Base menu items
            menu_items = [
                {"label": "Browse your Mubi watchlist", "description": "Browse your Mubi watchlist", "action": "watchlist", "is_folder": True}
            ]
            
            # Conditionally add sync options based on fast sync setting
            if enable_fast_sync:
                # Fast sync enabled: only show GitHub sync
                menu_items.append(
                    {"label": "Sync worldwide catalogue", "description": "Fast sync using pre-computed database from GitHub (database/v1/films.json.gz).", "action": "sync_github", "is_folder": False}
                )
            else:
                # Fast sync disabled: show traditional MUBI sync options
                menu_items.extend([
                    {"label": sync_label, "description": sync_description, "action": "sync_locally", "is_folder": False},
                    {"label": worldwide_label, "description": worldwide_description, "action": "sync_worldwide", "is_folder": False}
                ])
            
            # Add logout option
            menu_items.append(
                {"label": "Log Out", "description": "Log out from your Mubi account", "action": "log_out", "is_folder": False}
            )
            
            return menu_items
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



    def _get_available_countries_data_from_nfo(self, film_id: str) -> dict:
        """
        Read the available countries and their availability details from the NFO file.

        :param film_id: The MUBI film ID.
        :return: Dict {country_code: {'availability': 'live', ...}}
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

                # Helper to extract availability dict from availability element
                def extract_availability(mubi_availability_node) -> dict:
                    if mubi_availability_node is None:
                         return {}
                    
                    data = {}
                    for country in mubi_availability_node.findall("country"):
                        code = country.get("code")
                        if not code:
                             continue
                        
                        details = {}
                        # Extract availability status
                        avail_node = country.find("availability")
                        if avail_node is not None and avail_node.text:
                            details['availability'] = avail_node.text
                        else:
                            details['availability'] = 'live' # Default if missing but country present
                        
                        # Extract other fields if needed
                        for field in ['available_at', 'expires_at', 'availability_ends_at']:
                            node = country.find(field)
                            if node is not None and node.text:
                                details[field] = node.text
                        
                        data[code] = details
                    return data
                
                # Check if this NFO matches the film_id (look for the STRM file or film ID)
                uniqueid = root.find(".//uniqueid[@type='mubi']")
                if uniqueid is not None and uniqueid.text == film_id:
                    # Found the right film
                    mubi_availability = root.find("mubi_availability")
                    xbmc.log(f"Found NFO for film_id {film_id} via uniqueid: {nfo_file}", xbmc.LOGDEBUG)
                    return extract_availability(mubi_availability)

                # Alternative: check STRM file for exact film_id match
                strm_files = list(film_folder.glob("*.strm"))
                if strm_files:
                    strm_content = strm_files[0].read_text()
                    pattern = rf"film_id={re.escape(str(film_id))}(&|$)"
                    if re.search(pattern, strm_content):
                        # Found the right film
                        mubi_availability = root.find("mubi_availability")
                        xbmc.log(f"Found NFO for film_id {film_id} via STRM: {nfo_file}", xbmc.LOGDEBUG)
                        return extract_availability(mubi_availability)

            except (ET.ParseError, OSError) as e:
                xbmc.log(f"Error parsing NFO file {nfo_file}: {e}", xbmc.LOGWARNING)
                continue

        xbmc.log(f"No NFO file found for film_id {film_id}", xbmc.LOGWARNING)
        return {}

    def _is_country_available(self, details: dict) -> bool:
        """
        Check if the film is available in a country based on date ranges.
        Falls back to 'live' status check if dates are missing.

        :param details: Availability details dict for a country
        :return: True if available, False otherwise
        """
        # 1. Check date range if available
        available_at = details.get('available_at')
        expires_at = details.get('expires_at')

        if available_at or expires_at:
            try:
                # Use UTC for comparison as API dates are typically UTC
                now = datetime.datetime.now(datetime.timezone.utc)
                
                is_available = True
                
                if available_at:
                    start_dt = dateutil.parser.parse(available_at)
                    # ensure timezone awareness
                    if not start_dt.tzinfo:
                        start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
                    if now < start_dt:
                        is_available = False
                
                if expires_at:
                    end_dt = dateutil.parser.parse(expires_at)
                    # ensure timezone awareness
                    if not end_dt.tzinfo:
                        end_dt = end_dt.replace(tzinfo=datetime.timezone.utc)
                    if now > end_dt:
                        is_available = False
                
                return is_available
            except Exception as e:
                xbmc.log(f"Error parsing dates for availability check: {e}", xbmc.LOGWARNING)
                # Fall through to legacy check on error

        # 2. Legacy/Simple check: availability == 'live'
        return details.get('availability') == 'live'

    def _get_vpn_suggestions(self, available_countries_data: dict, max_suggestions: int = 3) -> list:
        """
        Get VPN country suggestions sorted by best VPN tier (fastest infrastructure).
        Only suggests countries where status is 'live'.

        :param available_countries_data: Dict of {code: details}
        :param max_suggestions: Maximum number of suggestions to return.
        :return: List of tuples (country_code, country_name, vpn_tier).
        """
        from .countries import COUNTRIES

        suggestions = []
        
        # Handle if list is passed (legacy fallback)
        if isinstance(available_countries_data, list):
             available_countries_data = {c: {'availability': 'live'} for c in available_countries_data}

        for code, details in available_countries_data.items():
            code_lower = code.lower()
            
            # Filter: must be currently available (date check or 'live' status)
            if not self._is_country_available(details):
                continue

            if code_lower in COUNTRIES:
                country_data = COUNTRIES[code_lower]
                suggestions.append((
                    code.upper(),
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
        
        MAX COMPATIBILITY UPDATE (2024-12):
        Handles old NFOs (list of countries) and new NFOs (detailed availability dict).

        :param film_id: Video ID
        :param web_url: Web URL of the film
        :param country: Deprecated - country info is now read from NFO files.
        """
        import xbmc
        import xbmcgui
        import xbmcaddon
        from .countries import COUNTRIES
        from .playback import play_with_inputstream_adaptive

        if not film_id:
            xbmc.log("play_mubi_video: No film_id provided", xbmc.LOGERROR)
            xbmcgui.Dialog().notification("MUBI", "Internal Error: No Film ID", xbmcgui.NOTIFICATION_ERROR)
            return

        # Step 1: Get current client country (from settings or auto-detect logic)
        # Step 1: Get current client country (Live check for VPN support)
        # We check the actual IP location to support users who switch VPNs before playback
        current_country = self.mubi.get_cli_country()
        xbmc.log(f"Current client country detected via IP: {current_country}", xbmc.LOGINFO)

        # Step 2: Get available countries from NFO file
        # Returns a dict of {country_code: availability_details}
        available_countries_data = self._get_available_countries_data_from_nfo(film_id)
        
        # Derive simple list of availability for basic check
        available_country_codes = list(available_countries_data.keys())

        xbmc.log(f"Film {film_id} available in countries: {available_country_codes}", xbmc.LOGINFO)

        # Step 3: Check availability logic
        is_available = False
        availability_status = "unknown"
        
        if not available_countries_data:
            # Optimistic fallback: if no data (e.g. not in library), assume available and let backend decide
            xbmc.log(f"No availability data found for {film_id}. Assuming available.", xbmc.LOGINFO)
            is_available = True
        elif current_country.upper() in available_country_codes:
            # Check detailed availability
            details = available_countries_data.get(current_country.upper(), {})
            
            if self._is_country_available(details):
                is_available = True
            else:
                availability_status = details.get('availability', 'unknown')
                xbmc.log(f"Film {film_id} in {current_country} is not currently available (Status: {availability_status})", xbmc.LOGINFO)
        
        if not is_available:
            # Get country name for display
            current_country_name = COUNTRIES.get(current_country.lower(), {}).get("name", current_country)

            # Get VPN suggestions (top 3 countries sorted by best VPN tier AND live availability)
            vpn_suggestions = self._get_vpn_suggestions(available_countries_data)

            if vpn_suggestions:
                vpn_countries = ", ".join([f"{s[1]}" for s in vpn_suggestions])
                message = f"This movie is not available in {current_country_name}. Connect to a VPN and try again. Available countries: {vpn_countries}"
            else:
                extra_msg = ""
                if availability_status != "unknown" and availability_status != "live":
                     extra_msg = f" (Status: {availability_status})"
                message = f"This movie is not available in {current_country_name}{extra_msg}."

            xbmc.log(f"Film not available in {current_country}: {message}", xbmc.LOGINFO)
            xbmcgui.Dialog().ok("MUBI - Not Available", message)
            # Tell Kodi we failed so it stops loading, hopefully suppressing the timeout error
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem())
            return

        # Step 4: Proceed with playback
        try:
            stream_info = self.mubi.get_secure_stream_info(film_id)
            xbmc.log(f"Stream info for film_id {film_id}: {stream_info}", xbmc.LOGDEBUG)

            if 'error' in stream_info:
                error_msg = stream_info['error']
                xbmc.log(f"Error in stream info: {error_msg}", xbmc.LOGERROR)

                # If geo-restriction error and we have availability data, show VPN suggestions
                if 'VPN' in error_msg and available_countries_data:
                    current_country_name = COUNTRIES.get(current_country.lower(), {}).get("name", current_country)
                    vpn_suggestions = self._get_vpn_suggestions(available_countries_data)
                    if vpn_suggestions:
                        vpn_countries = ", ".join([s[1] for s in vpn_suggestions])
                        message = f"This movie is not available in {current_country_name}. Connect to a VPN and try again. Available countries: {vpn_countries}"
                        xbmcgui.Dialog().ok("MUBI - Not Available", message)
                        xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem())
                        return

                # Check if this is a geo-restriction error (contains VPN message)
                if 'VPN' in error_msg:
                    # Show a dialog for geo-restriction, no browser option
                    xbmcgui.Dialog().ok("MUBI", error_msg)
                    xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem())
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
        """
        # Validate countries list
        if not countries:
            xbmcgui.Dialog().notification("MUBI", "No countries specified for sync.", xbmcgui.NOTIFICATION_ERROR)
            return

        from .countries import COUNTRIES
        # Determine dialog title
        if dialog_title is None:
            num_countries = len(countries)
            if num_countries == 1:
                country_data = COUNTRIES.get(countries[0].lower(), {})
                country_name = country_data.get("name", countries[0])
                dialog_title = f"Syncing MUBI from {country_name}"
            else:
                dialog_title = f"Syncing MUBI from {num_countries} countries"

        self._perform_sync(dialog_title=dialog_title, countries=countries)

    def sync_from_github(self):
        """
        Sync MUBI films locally by downloading a pre-computed database from GitHub.
        """
        from .data_source import GithubDataSource
        github_source = GithubDataSource()
        # Skip external metadata checks/fetches for GitHub sync as the JSON is already enriched
        self._perform_sync(dialog_title="Syncing...", data_source=github_source, skip_external_metadata=True)

    def _perform_sync(self, dialog_title: str, countries: list = None, data_source=None, skip_external_metadata: bool = False):
        """
        Helper method to execute the common sync logic (locking, provider check, fetching, library update).
        """
        from .external_metadata import MetadataProviderFactory
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
                return

            NavigationHandler._sync_in_progress = True

        try:
            # Check if metadata providers are configured, unless skipping
            if not skip_external_metadata:
                provider = MetadataProviderFactory.get_provider()
                
                if not provider:
                    dialog = xbmcgui.Dialog()
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
                        provider = MetadataProviderFactory.get_provider()
                        if not provider: return
                    else:
                        return

                if not provider.test_connection():
                    xbmcgui.Dialog().notification(
                        "MUBI", 
                        f"Invalid API Key for {provider.provider_name}. Sync aborted.", 
                        xbmcgui.NOTIFICATION_ERROR,
                        5000
                    )
                    xbmc.log(f"Sync aborted: Invalid API key for {provider.provider_name}", xbmc.LOGERROR)
                    return

            xbmc.log(f"Starting sync: {dialog_title}", xbmc.LOGINFO)

            # Proceed with the sync process
            pDialog = xbmcgui.DialogProgress()
            pDialog.create(dialog_title, "Initializing...")

            # Define progress callback for dynamic updates
            def update_fetch_progress(current_films, total_films, current_country, total_countries, country_code):
                if pDialog.iscanceled():
                    raise Exception("User canceled sync operation")

                # Calculate percentage
                if total_countries > 1:
                    percent = min(int((current_country / total_countries) * 100), 99)
                    country_name = COUNTRIES.get(country_code.lower(), {}).get("name", country_code)
                    message = f"Fetching from {country_name} ({current_country}/{total_countries})...\n{current_films} films found"
                elif total_countries == 1:
                    # Single country sync
                    percent = min(int((current_films / 1000) * 100), 99) if current_films > 0 else 0
                    country_name = COUNTRIES.get(country_code.lower(), {}).get("name", country_code)
                    message = f"Fetching films from {country_name}...\n{current_films} films found"
                else:
                    # GitHub sync (no total countries usually, or treated differently)
                    percent = 50 # Indeterminate or based on generic progress
                    message = f"Fetching database..."

                pDialog.update(percent, message)

            # Sync films
            try:
                all_films_library = self.mubi.get_all_films(
                    playable_only=True,
                    progress_callback=update_fetch_progress,
                    countries=countries,
                    data_source=data_source
                )
            except (ValueError, Exception) as e:
                # Handle specific known errors (ValueError might be MD5 or validation)
                msg = str(e)
                
                # Check for cancellation first (raised as general Exception sometimes)
                if "canceled" in msg.lower():
                    pDialog.close()
                    xbmc.log("User canceled the sync process during film fetching.", xbmc.LOGDEBUG)
                    return None
                
                # Identify error type for cleaner notification
                error_title = "Sync Failed"
                if "MD5" in msg:
                    error_body = "Download integrity check failed."
                elif "JSON" in msg or "parsing" in msg.lower():
                    error_body = "Data format error from server."
                elif "HTTP" in msg or "Connection" in msg or "Max retries" in msg:
                        error_body = "Network error or server unavailable."
                else:
                        error_body = f"Error: {msg}"

                import traceback
                xbmc.log(f"Sync failed with error: {e}", xbmc.LOGERROR)
                xbmc.log(f"Full traceback:\n{traceback.format_exc()}", xbmc.LOGERROR)
                pDialog.close()
                
                xbmcgui.Dialog().notification(
                    "MUBI", 
                    error_body,
                    xbmcgui.NOTIFICATION_ERROR,
                    5000
                )
                return None

            # Update progress dialog for file creation phase
            filtered_films_count = len(all_films_library.films)
            pDialog.update(100, f"Fetched {filtered_films_count} films, creating local files...")
            xbmc.log(f"Successfully fetched {filtered_films_count} films", xbmc.LOGINFO)

            if pDialog.iscanceled():
                pDialog.close()
                xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                return None

            plugin_userdata_path = Path(xbmcvfs.translatePath(self.plugin.getAddonInfo("profile")))
            pDialog.close()
            
            # Small delay
            import time
            time.sleep(0.1)

            # Sync files locally
            all_films_library.sync_locally(
                self.base_url, plugin_userdata_path, skip_external_metadata=skip_external_metadata
            )

            # Trigger library operations
            monitor = LibraryMonitor()
            if self.plugin.getSettingBool("auto_clean_library"):
                self.clean_kodi_library(monitor)
            else:
                    xbmc.log("Library cleaning disabled by setting", xbmc.LOGDEBUG)
            self.update_kodi_library()

        except Exception as e:
            xbmc.log(f"Error during sync: {e}", xbmc.LOGERROR)
            import traceback
            xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
            xbmcgui.Dialog().notification("MUBI", "An unexpected error occurred during sync.", xbmcgui.NOTIFICATION_ERROR)
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

