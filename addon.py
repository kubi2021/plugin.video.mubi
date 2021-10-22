from __future__ import absolute_import, division, unicode_literals
import sys
from resources.lib.mubi import Mubi
import resources.lib.library as library
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc
from urllib.parse import urlencode, parse_qsl
from pathlib import Path

# In order to load the movie in the external browser
import webbrowser



plugin = xbmcaddon.Addon()

# xbmc.translatePath is deprecated and might be removed in future kodi versions. Please use xbmcvfs.translatePath instead.
plugin_userdata_path = Path(xbmc.translatePath( plugin.getAddonInfo('profile') ))


if not plugin.getSetting("username") or not plugin.getSetting("password"):
    plugin.openSettings()

mubi = Mubi(plugin.getSetting("username"), plugin.getSetting("password"))

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
    return '{}?{}'.format(_URL, urlencode(kwargs))

def main_navigation():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_HANDLE, 'Mubi')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, 'videos')

    main_navigation_items = [
        {
            "label": "Browse Mubi films by category",
            "description": "Browse Mubi films by category",
            "action": "list_categories"
        },
        {
            "label": "Sync all Mubi films locally",
            "description": "This will create a local folder with all films information, such that it can be imported in the standard Kodi media library. After sync make sure to add the video source special://userdata/addon_data/plugin.video.mubi and update your library.",
            "action": "sync_locally"
        }
    ]

    for item in main_navigation_items:

        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=item['label'])

        list_item.setInfo('video', {'title': item['label'],
                                    'plot': item['description'],
                                    'mediatype': 'video'})

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = get_url(action=item['action'])

        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)

def sync_locally():

    pDialog = xbmcgui.DialogProgress()

    pDialog.create('Syncing with Mubi', 'Fetching all categories ...')

    # fetch all cagetories
    categories = mubi.get_film_groups()

    # category = categories[0]
    # all_films = mubi.get_film_list(category["type"], category["id"], category["title"])

    # build up the entire list of films
    all_films = []
    for idx,category in enumerate(categories):
        percent = int(idx / len(categories) * 100)
        pDialog.update(percent, 'Fetching ' + category["title"])

        films = mubi.get_film_list(category["type"], category["id"], category["title"])
        all_films.extend(films)

        if (pDialog.iscanceled()):
            pDialog.close()
            return None

    ## Add action URL to the films so that they can be launched by Mubi
    films_with_kodi_url=[]
    for film in all_films:
        film_with_kodi_url = {
            'film': film,
            'url': get_url(action='play_ext', web_url=film.web_url)
        }
        films_with_kodi_url.append(film_with_kodi_url)

    # merge the duplicates, keep multiple categories per film
    merged_films = library.merge_duplicates(films_with_kodi_url)

    # write the files one by one
    for idx,film in enumerate(merged_films):
        percent = int(idx / len(merged_films) * 100)
        pDialog.update(percent, 'Creating local data for movie ' + str(idx) + ' of ' + str(len(merged_films)) + ':\n' + film["title"])
        library.write_files(plugin_userdata_path, film)

        if (pDialog.iscanceled()):
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
    xbmcplugin.setPluginCategory(_HANDLE, 'Browsing Mubi')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, 'videos')

    # Get the video categories from Mubi.
    categories = mubi.get_film_groups()

    # Iterate through categories
    for category in categories:

        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=category['title'])

        list_item.setInfo('video', {'title': category['title'],
                                    'plot': category['description'],
                                    'mediatype': 'video'})
        list_item.setArt({
            'thumb': category['image'],
            'poster': category['image'],
            'banner': category['image'],
            'fanart': category['image'],
            'landscape': category['image'],
            'icon': category['image']
            })

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = get_url(action='listing', type=category["type"], id=category["id"], category_name=category['title'])

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
    xbmcplugin.setContent(_HANDLE, 'videos')

    # Get the list of films in the selected category.
    films = mubi.get_film_list(type, id, category_name)

    # Iterate through the films
    for film in films:

        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=film.title)

        # Set additional info for the list item.
        list_item.setInfo('video', {'title': film.title,
                                    'originaltitle': film.metadata.originaltitle,
                                    'genre': film.metadata.genre,
                                    # 'country': str(film.metadata.country),
                                    # 'year': film.metadata.year,
                                    # 'rating': film.metadata.rating,
                                    # 'director': str(film.metadata.director),
                                    'plot': film.metadata.plot,
                                    # 'plotoutline': film.metadata.plotoutline,
                                    # 'duration': film.metadata.duration,
                                    # 'trailer': film.metadata.trailer,
                                    # 'dateadded': film.metadata.dateadded,
                                    'mediatype': 'video'})

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        list_item.setArt({
            'thumb': film.metadata.image,
            'poster': film.metadata.image,
            'banner': film.metadata.image,
            'fanart': film.metadata.image,
            'landscape': film.metadata.image,
            'icon': film.metadata.image
            })

        # Currently, the plugin is not able to load films within kodi
        # because of the DRMs. Therefore we load the films in the browser.
        url = get_url(action='play_ext', web_url=film.web_url)

        # The lines below would need to be uncommented
        # to load the kodi player with DRM.

        # This is mandatory for playable items!
        # list_item.setProperty('IsPlayable', 'true')

        # Create a URL for a plugin recursive call.
        # url = get_url(action='play', identifier=film.mubi_id)

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


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'list_categories':
            # Display the list of videos in a provided category.
            list_categories()
        elif params['action'] == 'sync_locally':
            # Display the list of videos in a provided category.
            sync_locally()
        elif params['action'] == 'listing':
            # Display the list of videos in a provided category.
            list_videos(params['type'], params['id'], params['category_name'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['identifier'])
        elif params['action'] == 'play_ext':
            # Play a video from a provided URL.
            play_video_ext(params['web_url'])
        else:
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        main_navigation()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])



## DRM section
# The code below is an attempt to load the videos within Kodi.
# For it to work, we need to be able to read with DRMs.
# Unfortunately, it's not working yet so the code remains commented.


# DRM Licenses are issued by: https://lic.drmtoday.com/license-proxy-widevine/cenc/
# The header data has to contain the field dt-custom-data
# This field includes a base64-encoded string with the following data: {"userId":[userId],"sessionId":"[sessionToken]","merchant":"mubi"}
# The user id and session token can be obtained with the login

# LICENSE_URL = 'https://lic.drmtoday.com/license-proxy-widevine/cenc/'

## update header according to mobile app packets
# LICENSE_URL_HEADERS = (
#     # 'User-Agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.123 Safari/537.36&'
#     'Accept=*/*&'
#     'Accept-Encoding=gzip, deflate, br&'
#     'Accept-Language=en-US,en;q=0.9,fr;q=0.8,de;q=0.7,es;q=0.6,pt;q=0.5&'
#     'Cache-Control=no-cache&'
#     'Connection=keep-alive&'
#     'Content-Length=4023&'
#     'DNT=1&'
#     'Host=lic.drmtoday.com&'
#     'Origin=https://mubi.com&'
#     'Pragma=no-cache&'
#     'Referer=https://mubi.com/&'
#     'sec-ch-ua= "Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"&'
#     'sec-ch-ua-mobile=?0&'
#     'sec-ch-ua-platform="macOS"&'
#     'Sec-Fetch-Dest=empty&'
#     'Sec-Fetch-Mode=cors&'
#     'Sec-Fetch-Site=cross-site&'
#     'User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36'
#     # 'Content-Type=application/json;charset=utf-8'
# )


# Function to play video within Mubi. Currently not working because of DRMs
# def play_video(identifier):
#     """
#     Play a video by the provided path.
#
#     :param path: Fully-qualified video URL
#     :type path: str
#     """
#     # Create a playable item with a path to play.
#     # play_item = xbmcgui.ListItem(path=path)
#     # Pass the item to the Kodi player.
#     # xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)
#
#     mubi_resolved_info = mubi.get_play_url(identifier)
#     mubi_film = xbmcgui.ListItem(path=mubi_resolved_info['url'])
#
#     if mubi_resolved_info['is_mpd']:
#
#         mubi_film.setProperty('inputstream', 'inputstream.adaptive')
#         mubi_film.setProperty('inputstream.adaptive.manifest_type', 'mpd')
#
#         if mubi_resolved_info['drm_header'] is not None:
#             xbmc.log('DRM Header: %s' %mubi_resolved_info['drm_header'].decode(), 2)
#             xbmc.log('LICENSE_URL_HEADERS: %s' % LICENSE_URL_HEADERS, 2)
#             mubi_film.setProperty('inputstream.adaptive.license_type', "com.widevine.alpha")
#             mubi_film.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '|' + LICENSE_URL_HEADERS + '&CL-KEY=' + mubi_resolved_info['drm_header'].decode() + '&CL-USER-ID='+ str(mubi_resolved_info['userId']) +'&CL-SESSION-ID='+ str(mubi_resolved_info['token']) + '&CL-ASSET-ID='+ str(mubi_resolved_info['drm_asset_id']) +'|R{SSM}|JBlicense')
#             # mubi_film.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '|' + LICENSE_URL_HEADERS + '&dt-custom-data=' + mubi_resolved_info['drm_header'].decode() + '|R{SSM}|JBlicense')
#             # mubi_film.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '|' + LICENSE_URL_HEADERS + '&dt-custom-data=' + mubi_resolved_info['drm_header'] + '|R{SSM}|JBlicense')
#             mubi_film.setMimeType('application/dash+xml')
#             mubi_film.setContentLookup(False)
#     return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem=mubi_film)
