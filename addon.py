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

if __name__ == "__main__":
    plugin = xbmcaddon.Addon()
    handle = int(sys.argv[1])
    base_url = sys.argv[0]
    session = SessionManager(plugin)
    mubi = Mubi(session)
    navigation = NavigationHandler(handle, base_url, mubi, session)

    # Parse parameters from the URL
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get("action")

    if action == "list_categories":
        navigation.list_categories()
    elif action == "log_in":
        navigation.log_in()
    elif action == "log_out":
        navigation.log_out()
    elif action == "listing":
        navigation.list_videos(params['type'], params['id'], params['category_name'])
    elif action == "play_ext":
        navigation.play_video_ext(params['web_url'])
    elif action == "play_trailer":
        navigation.play_trailer(params['url'])
    elif action == "sync_locally":
        navigation.sync_locally()
    else:
        navigation.main_navigation()

