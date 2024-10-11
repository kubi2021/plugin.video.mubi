# Kodi plugin that integrates with the Mubi API to display films and categories within the Kodi interface.
# It allows users to browse Mubi films, sync film metadata locally, 
# and play films or trailers externally using a web browser.
# The plugin handles navigation, builds the user interface for displaying categories and films, 
# and manages interactions with the Mubi API.



from resources.lib.session_manager import SessionManager
from resources.lib.navigation_handler import NavigationHandler
from resources.lib.mubi import Mubi
import xbmcaddon
from urllib.parse import parse_qsl
import sys
import xbmc

if __name__ == "__main__":
    plugin = xbmcaddon.Addon()
    handle = int(sys.argv[1])
    base_url = sys.argv[0]
    session = SessionManager(plugin)
    mubi = Mubi(session)

    # Log the handle and base URL for debugging purposes
    xbmc.log(f"Addon initialized with handle: {handle} and base_url: {base_url}", xbmc.LOGDEBUG)


    # Fetch and set client country if it's not already set
    if not session.client_country:
        client_country = mubi.get_cli_country()
        session.set_client_country(client_country)

    navigation = NavigationHandler(handle, base_url, mubi, session)

    # Parse parameters from the URL
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get("action")

    if action == "list_categories":
        xbmc.log(f"Calling list_categories with handle: {handle}", xbmc.LOGDEBUG)
        navigation.list_categories()
    elif action == "log_in":
        xbmc.log(f"Calling log_in with handle: {handle}", xbmc.LOGDEBUG)
        navigation.log_in()
    elif action == "log_out":
        xbmc.log(f"Calling log_out with handle: {handle}", xbmc.LOGDEBUG)
        navigation.log_out()
    elif action == "listing":
        xbmc.log(f"Calling listing with handle: {handle}", xbmc.LOGDEBUG)
        navigation.list_videos(params['type'], params['id'], params['category_name'])
    elif action == "play_ext":
        xbmc.log(f"Calling play_ext with handle: {handle}", xbmc.LOGDEBUG)
        navigation.play_video_ext(params['web_url'])
    elif action == "play_trailer":
        xbmc.log(f"Calling play_trailer with handle: {handle}", xbmc.LOGDEBUG)
        navigation.play_trailer(params['url'])
    elif action == "sync_locally":
        xbmc.log(f"Calling sync_locally with handle: {handle}", xbmc.LOGDEBUG)
        navigation.sync_locally()
    elif action == "play_mubi_video":
        xbmc.log(f"Calling play_mubi_video with handle: {handle}", xbmc.LOGDEBUG)
        navigation.play_mubi_video(params['film_id'])
    else:
        navigation.main_navigation()

