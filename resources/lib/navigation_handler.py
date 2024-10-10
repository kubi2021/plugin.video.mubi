# navigation_handler.py

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

    def __init__(self, handle, base_url, mubi, session):
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

    def get_url(self, **kwargs):
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
        self.session.is_logged_in = self.plugin.getSettingBool('logged') and self.session.token

        xbmcplugin.setPluginCategory(self.handle, "Mubi")
        xbmcplugin.setContent(self.handle, "videos")

        if self.session.is_logged_in:
            main_navigation_items = [
                {
                    "label": "Browse Mubi films by category",
                    "description": "Browse Mubi films by category",
                    "action": "list_categories",
                    "is_folder": True,
                },
                {
                    "label": "Sync all Mubi films locally",
                    "description": "Sync Mubi films locally",
                    "action": "sync_locally",
                    "is_folder": True,
                },
                {
                    "label": "Log Out",
                    "description": "Log out from your Mubi account",
                    "action": "log_out",
                    "is_folder": False,
                },
            ]
        else:
            main_navigation_items = [
                {
                    "label": "Log In",
                    "description": "Log in to your Mubi account",
                    "action": "log_in",
                    "is_folder": False,
                }
            ]

        for item in main_navigation_items:
            list_item = xbmcgui.ListItem(label=item["label"])
            list_item.setInfo(
                "video",
                {
                    "title": item["label"],
                    "plot": item["description"],
                    "mediatype": "video",
                },
            )
            url = self.get_url(action=item["action"])
            xbmcplugin.addDirectoryItem(
                self.handle, url, list_item, item["is_folder"]
            )

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(self.handle)



    def list_categories(self):
        """
        List categories fetched from the Mubi API.
        """
        xbmcplugin.setPluginCategory(self.handle, "Browsing Mubi")
        xbmcplugin.setContent(self.handle, "videos")

        categories = self.mubi.get_film_groups()

        for category in categories:
            list_item = xbmcgui.ListItem(label=category["title"])

            list_item.setInfo(
                "video",
                {
                    "title": category["title"],
                    "plot": category["description"],
                    "mediatype": "video",
                },
            )
            list_item.setArt(
                {
                    "thumb": category["image"],
                    "poster": category["image"],
                    "banner": category["image"],
                    "fanart": category["image"],
                    "landscape": category["image"],
                    "icon": category["image"],
                }
            )

            url = self.get_url(
                action="listing",
                type=category["type"],
                id=category["id"],
                category_name=category["title"],
            )

            is_folder = True
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(self.handle)

    def list_videos(self, type, id, category_name):
        """
        List videos in a selected category.

        :param type: Type of the category
        :param id: ID of the category
        :param category_name: Name of the category
        """
        xbmcplugin.setContent(self.handle, "videos")

        # Get the Library instance with films
        library = self.mubi.get_film_list(type, id, category_name)

        # Iterate through the films in the Library and display them
        for film in library.films:  # Access the films attribute from the Library
            list_item = xbmcgui.ListItem(label=film.title)

            # Access metadata fields via the Metadata class
            list_item.setInfo(
                "video",
                {
                    "title": film.title,
                    "originaltitle": film.metadata.originaltitle,
                    "genre": ', '.join(film.metadata.genre),  # Genre as a comma-separated string
                    "plot": film.metadata.plot,
                    "mediatype": "video",
                },
            )

            list_item.setArt(
                {
                    "thumb": film.metadata.image,
                    "poster": film.metadata.image,
                    "banner": film.metadata.image,
                    "fanart": film.metadata.image,
                    "landscape": film.metadata.image,
                    "icon": film.metadata.image,
                }
            )

            url = self.get_url(action="play_ext", web_url=film.web_url)

            is_folder = False
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(self.handle)




    def play_video_ext(self, web_url):
        """
        Play a video externally by opening it in a web browser.

        :param web_url: Web URL of the video
        """
        webbrowser.open_new_tab(web_url)

    def play_trailer(self, url):
        """
        Play a trailer video within Kodi.

        :param url: URL of the trailer video
        """
        play_item = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)

    def log_in(self):
        """
        Handle user login by generating a link code and authenticating with Mubi.
        """
        try:
            code_info = self.mubi.get_link_code()
            if 'auth_token' in code_info and 'link_code' in code_info:
                link_code = code_info['link_code']
                auth_token = code_info['auth_token']
                xbmcgui.Dialog().ok(
                    "Log In",
                    f"Enter code [COLOR=yellow][B]{link_code}[/B][/COLOR] on [B]https://mubi.com/android[/B]",
                )
                auth_response = self.mubi.authenticate(auth_token)
                if 'token' in auth_response:
                    self.session.set_logged_in(auth_response['token'])
                    xbmcgui.Dialog().notification(
                        "MUBI",
                        "Successfully logged in!",
                        xbmcgui.NOTIFICATION_INFO,
                    )
                    xbmc.executebuiltin('Container.Refresh')
                else:
                    error_message = auth_response.get('message', 'Unknown error')
                    xbmcgui.Dialog().notification(
                        'MUBI',
                        f"Error: {error_message}",
                        xbmcgui.NOTIFICATION_ERROR,
                    )
            else:
                xbmcgui.Dialog().notification(
                    'MUBI',
                    'Error during code generation.',
                    xbmcgui.NOTIFICATION_ERROR,
                )
        except Exception as e:
            xbmc.log(f"Exception during login: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                'MUBI',
                'An unexpected error occurred during login.',
                xbmcgui.NOTIFICATION_ERROR,
            )

    def log_out(self):
        """
        Handle user logout from Mubi.
        """
        success = self.mubi.log_out()
        if success:
            self.session.set_logged_out()
            xbmcgui.Dialog().notification(
                "MUBI",
                "Successfully logged out!",
                xbmcgui.NOTIFICATION_INFO,
            )
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcgui.Dialog().notification(
                'MUBI',
                'Error during logout. You are still logged in.',
                xbmcgui.NOTIFICATION_ERROR,
            )


    def sync_locally(self):
        """
        Sync all Mubi films locally by fetching all categories and creating STRM and NFO files
        for each film. This allows the films to be imported into Kodi's standard media library.
        """
        pDialog = xbmcgui.DialogProgress()
        pDialog.create("Syncing with Mubi", "Fetching all categories...")

        # Fetch all categories
        categories = self.mubi.get_film_groups()

        # Create an instance of the Library to manage the collection of films
        all_films_library = Library()

        total_categories = len(categories)
        for idx, category in enumerate(categories):
            percent = int((idx / total_categories) * 100)
            pDialog.update(percent, f"Fetching {category['title']}")

            # Log information about the current category
            xbmc.log(f"Starting to fetch films for category '{category['title']}' (ID: {category['id']})", xbmc.LOGDEBUG)

            try:
                # Fetch film list for the current category
                films_in_category = self.mubi.get_film_list(category["type"], category["id"], category["title"])
                xbmc.log(f"Fetched {len(films_in_category)} films for category '{category['title']}'", xbmc.LOGDEBUG)
                
                # Add films to the main Library instance
                for film in films_in_category.films:
                    all_films_library.add_film(film)

            except Exception as e:
                xbmc.log(f"Error fetching films for category '{category['title']}': {e}", xbmc.LOGERROR)
                continue  # Skip to the next category if an error occurs

            if pDialog.iscanceled():
                pDialog.close()
                xbmc.log("User canceled the sync process.", xbmc.LOGDEBUG)
                return None

        # Sync the library locally using the Library class
        plugin_userdata_path = Path(xbmcvfs.translatePath(self.plugin.getAddonInfo("profile")))
        omdb_api_key = self.plugin.getSetting("omdbapiKey")

        all_films_library.sync_locally(self.base_url, plugin_userdata_path, omdb_api_key)

        pDialog.close()
        xbmcgui.Dialog().notification(
            "MUBI",
            "Sync completed successfully!",
            xbmcgui.NOTIFICATION_INFO,
        )