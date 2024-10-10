import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import webbrowser
from urllib.parse import urlencode
import xbmcvfs
from pathlib import Path
from resources.lib.library import Library


class NavigationHandler:
    """
    Handles all navigation and UI interactions within Kodi for the Mubi plugin.
    """

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
                {"label": "Browse Mubi films by category", "description": "Browse Mubi films by category", "action": "list_categories", "is_folder": True},
                {"label": "Sync all Mubi films locally", "description": "Sync Mubi films locally", "action": "sync_locally", "is_folder": True},
                {"label": "Log Out", "description": "Log out from your Mubi account", "action": "log_out", "is_folder": False}
            ]
        else:
            return [
                {"label": "Log In", "description": "Log in to your Mubi account", "action": "log_in", "is_folder": False}
            ]

    def _add_menu_item(self, item: dict):
        """ Helper method to add a menu item to Kodi """
        try:
            list_item = xbmcgui.ListItem(label=item["label"])
            list_item.setInfo("video", {"title": item["label"], "plot": item["description"], "mediatype": "video"})
            url = self.get_url(action=item["action"])
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, item["is_folder"])
        except Exception as e:
            xbmc.log(f"Error adding menu item {item['label']}: {e}", xbmc.LOGERROR)

    def list_categories(self):
        """
        List categories fetched from the Mubi API.
        """
        try:
            xbmcplugin.setPluginCategory(self.handle, "Browsing Mubi")
            xbmcplugin.setContent(self.handle, "videos")

            categories = self.mubi.get_film_groups()

            for category in categories:
                self._add_category_item(category)

            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            xbmc.log(f"Error listing categories: {e}", xbmc.LOGERROR)

    def _add_category_item(self, category: dict):
        """ Helper method to add a category to the Kodi directory """
        try:
            list_item = xbmcgui.ListItem(label=category["title"])
            list_item.setInfo("video", {"title": category["title"], "plot": category["description"], "mediatype": "video"})
            list_item.setArt({"thumb": category["image"], "poster": category["image"], "banner": category["image"], "fanart": category["image"]})
            url = self.get_url(action="listing", type=category["type"], id=category["id"], category_name=category["title"])
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)
        except Exception as e:
            xbmc.log(f"Error adding category item {category['title']}: {e}", xbmc.LOGERROR)

    def list_videos(self, type: str, id: int, category_name: str):
        """
        List videos in a selected category.

        :param type: Type of the category
        :param id: ID of the category
        :param category_name: Name of the category
        """
        try:
            xbmcplugin.setContent(self.handle, "videos")

            library = self.mubi.get_film_list(type, id, category_name)

            for film in library.films:
                self._add_film_item(film)

            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            xbmc.log(f"Error listing videos: {e}", xbmc.LOGERROR)

    def _add_film_item(self, film):
        """ Helper method to add a film item to the Kodi directory """
        try:
            list_item = xbmcgui.ListItem(label=film.title)
            list_item.setInfo("video", {"title": film.title, "originaltitle": film.metadata.originaltitle, "genre": ', '.join(film.metadata.genre), "plot": film.metadata.plot, "mediatype": "video"})
            list_item.setArt({"thumb": film.metadata.image, "poster": film.metadata.image, "fanart": film.metadata.image, "landscape": film.metadata.image})
            url = self.get_url(action="play_ext", web_url=film.web_url)
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, False)
        except Exception as e:
            xbmc.log(f"Error adding film item {film.title}: {e}", xbmc.LOGERROR)

    def play_video_ext(self, web_url: str):
        """
        Play a video externally by opening it in a web browser.

        :param web_url: Web URL of the video
        """
        try:
            webbrowser.open_new_tab(web_url)
        except Exception as e:
            xbmc.log(f"Error opening external video: {e}", xbmc.LOGERROR)

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
                if 'token' in auth_response:
                    self.session.set_logged_in(auth_response['token'])
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

    def sync_locally(self):
        """
        Sync all Mubi films locally by fetching all categories and creating STRM and NFO files for each film.
        This allows the films to be imported into Kodi's standard media library.
        """
        try:
            pDialog = xbmcgui.DialogProgress()
            pDialog.create("Syncing with Mubi", "Fetching all categories...")

            categories = self.mubi.get_film_groups()
            all_films_library = Library()
            total_categories = len(categories)

            for idx, category in enumerate(categories):
                percent = int((idx / total_categories) * 100)
                pDialog.update(percent, f"Fetching {category['title']}")

                try:
                    films_in_category = self.mubi.get_film_list(category["type"], category["id"], category["title"])
                    for film in films_in_category.films:
                        all_films_library.add_film(film)

                except Exception as e:
                    xbmc.log(f"Error fetching films for category '{category['title']}': {e}", xbmc.LOGERROR)
                    continue

                if pDialog.iscanceled():
                    pDialog.close()
                    xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                    return None

            plugin_userdata_path = Path(xbmcvfs.translatePath(self.plugin.getAddonInfo("profile")))
            omdb_api_key = self.plugin.getSetting("omdbapiKey")
            all_films_library.sync_locally(self.base_url, plugin_userdata_path, omdb_api_key)

            pDialog.close()
            xbmcgui.Dialog().notification("MUBI", "Sync completed successfully!", xbmcgui.NOTIFICATION_INFO)

        except Exception as e:
            xbmc.log(f"Error during sync: {e}", xbmc.LOGERROR)
