# Kodi plugin that integrates with the Mubi API to display films and categories within the Kodi interface.
# It allows users to browse Mubi films, sync film metadata locally, 
# and play films or trailers externally using a web browser.
# The plugin handles navigation, builds the user interface for displaying categories and films, 
# and manages interactions with the Mubi API.


from __future__ import absolute_import, division, unicode_literals
import sys
from resources.lib.mubi import Mubi
import resources.lib.library as library
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc
import xbmcvfs
from urllib.parse import urlencode, parse_qsl
from pathlib import Path
import os
import re
from resources.lib.session_manager import SessionManager




# In order to load the movie in the external browser
import webbrowser


plugin = xbmcaddon.Addon()
plugin_handle = int(sys.argv[1])
plugin_userdata_path = Path(xbmcvfs.translatePath(plugin.getAddonInfo("profile")))



# Instantiate the session manager
session = SessionManager(plugin)
mubi = Mubi(session)

# if not session.client_country:
#     session.set_client_country(mubi.settings['client_country'])

# Get the plugin url in plugin:// notation.
_URL = sys.argv[0]
# Get the plugin handle as an integer number.
_HANDLE = int(sys.argv[1])


def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return "{}?{}".format(_URL, urlencode(kwargs))


def main_navigation():

    session.is_logged_in = plugin.getSettingBool('logged') and session.token

    xbmcplugin.setPluginCategory(_HANDLE, "Mubi")
    xbmcplugin.setContent(_HANDLE, "videos")

    if session.is_logged_in:
        main_navigation_items = [
            {"label": "Browse Mubi films by category", "description": "Browse Mubi films by category", "action": "list_categories", "is_folder": True},
            {"label": "Sync all Mubi films locally", "description": "Sync Mubi films locally", "action": "sync_locally", "is_folder": True},
            {"label": "Log Out", "description": "Log out from your Mubi account", "action": "log_out", "is_folder": False}
        ]
    else:
        main_navigation_items = [{"label": "Log In", "description": "Log in to your Mubi account", "action": "log_in", "is_folder": False}]

    for item in main_navigation_items:
        list_item = xbmcgui.ListItem(label=item["label"])
        list_item.setInfo("video", {"title": item["label"], "plot": item["description"], "mediatype": "video"})
        url = get_url(action=item["action"])
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, item["is_folder"])

    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(_HANDLE)





def sync_locally():

    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Syncing with Mubi", "Fetching all categories ...")

    # fetch all cagetories
    categories = mubi.get_film_groups()

    # category = categories[0]
    # all_films = mubi.get_film_list(category["type"], category["id"], category["title"])

    # build up the entire list of films
    all_films = []
    for idx, category in enumerate(categories):
        percent = int(idx / len(categories) * 100)
        pDialog.update(percent, "Fetching " + category["title"])

        films = mubi.get_film_list(category["type"], category["id"], category["title"])
        all_films.extend(films)

        if pDialog.iscanceled():
            pDialog.close()
            return None

    # create plugin folder if not existing
    if not os.path.exists(plugin_userdata_path):
        os.makedirs(plugin_userdata_path)

    # merge the duplicates, keep multiple categories per film
    merged_films = library.merge_duplicates(all_films)

    # Create files (STRM and NFO)
    for idx, film in enumerate(merged_films):
        percent = int(idx / len(merged_films) * 100)
        pDialog.update(
            percent,
            "Creating local data for movie "
            + str(idx)
            + " of "
            + str(len(merged_films))
            + ":\n"
            + film["title"],
        )

        # prepare file name and path
        clean_title = (film["title"]).replace("/", " ")
        film_folder_name = Path(clean_title + " (" + str(film["metadata"].year) + ")")
        film_path = plugin_userdata_path / film_folder_name

        ## Create the folder
        try:
            os.mkdir(film_path)

            # create strm file
            film_file_name = clean_title + " (" + str(film["metadata"].year) + ").strm"
            film_strm_file = film_path / film_file_name
            kodi_movie_url = get_url(action="play_ext", web_url=film["web_url"])
            library.write_strm_file(film_strm_file, film, kodi_movie_url)

            # create nfo file
            nfo_file_name = clean_title + " (" + str(film["metadata"].year) + ").nfo"
            nfo_file = film_path / nfo_file_name
            kodi_trailer_url = get_url(action="play_trailer", url=film["metadata"].trailer)
            library.write_nfo_file(
                nfo_file, film, kodi_trailer_url, plugin.getSetting("omdbapiKey")
            )
        except OSError as error:
            xbmc.log("Error while creating the library: %s" % error, 2)

        if pDialog.iscanceled():
            pDialog.close()
            return None

    pDialog.close()


def list_categories():
    """
    Create the list of video categories in the Kodi interface.
    Each video category will result in a line in the plug-in interface.
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_HANDLE, "Browsing Mubi")
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, "videos")

    # Get the video categories from Mubi.
    categories = mubi.get_film_groups()

    # Iterate through categories
    for category in categories:

        # Create a list item with a text label and a thumbnail image.
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

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = get_url(
            action="listing",
            type=category["type"],
            id=category["id"],
            category_name=category["title"],
        )

        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)


def list_videos(type, id, category_name):
    """
    Create the list of playable videos in the Kodi interface.

    :param category: Category name
    :type category: str
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.

    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, "videos")

    # Get the list of films in the selected category.
    films = mubi.get_film_list(type, id, category_name)

    # Iterate through the films
    for film in films:

        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=film.title)

        # Set additional info for the list item.
        list_item.setInfo(
            "video",
            {
                "title": film.title,
                "originaltitle": film.metadata.originaltitle,
                "genre": film.metadata.genre,
                # 'country': str(film.metadata.country),
                # 'year': film.metadata.year,
                # 'rating': film.metadata.rating,
                # 'director': str(film.metadata.director),
                "plot": film.metadata.plot,
                # 'plotoutline': film.metadata.plotoutline,
                # 'duration': film.metadata.duration,
                # 'trailer': film.metadata.trailer,
                # 'dateadded': film.metadata.dateadded,
                "mediatype": "video",
            },
        )

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
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

        # Currently, the plugin is not able to load films within kodi
        # because of the DRMs. Therefore we load the films in the browser.
        url = get_url(action="play_ext", web_url=film.web_url)

        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)


def play_video_ext(web_url):
    """
    Play a video: load the browser with the film URL.

    :param path: Fully-qualified video URL
    :type path: str
    """
    webbrowser.open_new_tab(web_url)


def play_trailer(url):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=url)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)




def log_in():
    code_info = mubi.get_link_code()
    if 'auth_token' in code_info and 'link_code' in code_info:
        link_code = code_info['link_code']
        auth_token = code_info['auth_token']
        xbmcgui.Dialog().ok("Log In", f"Enter code [COLOR=yellow][B]{link_code}[/B][/COLOR] on [B]https://mubi.com/android[/B]")
        auth_response = mubi.authenticate(auth_token)
        if 'token' in auth_response:
            session.set_logged_in(auth_response['token'])
            xbmcgui.Dialog().notification("MUBI", "Successfully logged in!", xbmcgui.NOTIFICATION_INFO)
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcgui.Dialog().notification('MUBI', f"Error: {auth_response.get('message', 'Unknown error')}", xbmcgui.NOTIFICATION_ERROR)
    else:
        xbmcgui.Dialog().notification('MUBI', 'Error during code generation.', xbmcgui.NOTIFICATION_ERROR)

def log_out():
    success = mubi.log_out()
    if success:
        session.set_logged_out()
        xbmcgui.Dialog().notification("MUBI", "Successfully logged out!", xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('MUBI', 'Error during logout. You are still logged in.', xbmcgui.NOTIFICATION_ERROR)




def router(paramstring):
    params = dict(parse_qsl(paramstring))
    action = params.get("action")

    if action == "list_categories":
        list_categories()
    elif action == "sync_locally":
        sync_locally()
    elif action == "log_in":
        log_in()
    elif action == "log_out":
        log_out()
    else:
        main_navigation()



if __name__ == "__main__":
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    _URL = sys.argv[0]
    _HANDLE = int(sys.argv[1])
    router(sys.argv[2][1:])

