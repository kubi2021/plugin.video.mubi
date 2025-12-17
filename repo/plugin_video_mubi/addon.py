# Kodi plugin that integrates with the Mubi API to display films and categories within the Kodi interface.
# It allows users to browse Mubi films, sync film metadata locally, 
# and play films or trailers externally using a web browser.
# The plugin handles navigation, builds the user interface for displaying categories and films, 
# and manages interactions with the Mubi API.



from resources.lib.session_manager import SessionManager
from resources.lib.navigation_handler import NavigationHandler
from resources.lib.mubi import Mubi
import xbmcaddon
import xbmcplugin
from urllib.parse import parse_qsl
import sys
import xbmc
from urllib.parse import parse_qsl, unquote_plus
import xbmcgui
from resources.lib.migrations import (
    add_mubi_source, is_first_run, mark_first_run, migrate_genre_settings
)

if __name__ == "__main__":
    plugin = xbmcaddon.Addon()
    handle = int(sys.argv[1])
    base_url = sys.argv[0]
    session = SessionManager(plugin)
    mubi = Mubi(session)

    # Log the handle and base URL for debugging purposes
    xbmc.log(f"Addon initialized with handle: {handle} and base_url: {base_url}", xbmc.LOGDEBUG)

    # First run logic: Check and add the MUBI source if this is the first run
    if is_first_run(plugin):
        xbmc.log("First run detected: Adding MUBI source", xbmc.LOGINFO)
        add_mubi_source()
        mark_first_run(plugin)
        xbmc.log("First run completed: MUBI source added and first run marked", xbmc.LOGINFO)
    else:
        xbmc.log("Not the first run: Skipping MUBI source addition", xbmc.LOGINFO)

    # Migrate old text-based genre settings to new toggle-based settings
    # This only runs once if the old skip_genres setting has a value
    migrate_genre_settings(plugin)



    # Fetch and set client country if it's not already set
    if not session.client_country:
        client_country = mubi.get_cli_country()
        session.set_client_country(client_country)

    # Fetch and set client language if it's not already set
    if not session.client_language:
        client_language = mubi.get_cli_language()  # Assuming you have a similar method for language
        session.set_client_language(client_language)


    navigation = NavigationHandler(handle, base_url, mubi, session)

    # Parse parameters from the URL
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get("action")

    if action == "list_categories":
        xbmc.log(f"Calling list_categories with handle: {handle}", xbmc.LOGDEBUG)
        navigation.list_categories()
    elif action == "log_in":
        xbmc.log(f"Calling log_in with handle: {handle}", xbmc.LOGDEBUG)
        try:
            navigation.log_in()
            xbmcplugin.endOfDirectory(handle, succeeded=True)
        except Exception as e:
            xbmc.log(f"Error in log_in action: {e}", xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
    elif action == "log_out":
        xbmc.log(f"Calling log_out with handle: {handle}", xbmc.LOGDEBUG)
        try:
            navigation.log_out()
            xbmcplugin.endOfDirectory(handle, succeeded=True)
        except Exception as e:
            xbmc.log(f"Error in log_out action: {e}", xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
    elif action == "watchlist":
        xbmc.log(f"Calling list_watchlist with handle: {handle}", xbmc.LOGDEBUG)
        navigation.list_watchlist()

    elif action == "play_ext":
        xbmc.log(f"Calling play_ext with handle: {handle}", xbmc.LOGDEBUG)
        try:
            navigation.play_video_ext(params['web_url'])
            xbmcplugin.endOfDirectory(handle, succeeded=True)
        except Exception as e:
            xbmc.log(f"Error in play_ext action: {e}", xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
    elif action == "play_trailer":
        xbmc.log(f"Calling play_trailer with handle: {handle}", xbmc.LOGDEBUG)
        try:
            navigation.play_trailer(params['url'])
            xbmcplugin.endOfDirectory(handle, succeeded=True)
        except Exception as e:
            xbmc.log(f"Error in play_trailer action: {e}", xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
    elif action == "sync_locally":
        xbmc.log(f"Calling sync_films (local) with handle: {handle}", xbmc.LOGDEBUG)
        try:
            # Sync only from client's country
            client_country = plugin.getSetting("client_country")
            if client_country:
                navigation.sync_films(countries=[client_country.upper()])
            else:
                xbmcgui.Dialog().notification(
                    "MUBI", "No country configured. Please set your country in Settings.",
                    xbmcgui.NOTIFICATION_ERROR
                )
            # Sync is a one-shot action, not a directory listing.
            # Refresh the container to return to the main menu after sync completes.
            xbmc.executebuiltin('Container.Refresh')
        except Exception as e:
            xbmc.log(f"Error in sync_locally action: {e}", xbmc.LOGERROR)
            xbmc.executebuiltin('Container.Refresh')
    elif action == "sync_worldwide":
        xbmc.log(f"Calling sync_films (worldwide) with handle: {handle}", xbmc.LOGDEBUG)
        try:
            # Use coverage optimizer to find minimum countries for 100% coverage
            from resources.lib.coverage_optimizer import get_optimal_countries
            client_country = plugin.getSetting("client_country") or "CH"

            optimal_countries = get_optimal_countries(client_country)

            if optimal_countries:
                xbmc.log(
                    f"Worldwide sync: Using {len(optimal_countries)} optimized countries "
                    f"(starting with {client_country.upper()})",
                    xbmc.LOGINFO
                )
                dialog_title = f"Syncing MUBI Worldwide ({len(optimal_countries)} countries)"
                navigation.sync_films(countries=optimal_countries, dialog_title=dialog_title)
            else:
                # Fallback: if no catalogue available, use all countries
                xbmc.log("No country catalogue found, falling back to all countries", xbmc.LOGWARNING)
                from resources.lib.countries import COUNTRIES
                all_countries = [c.upper() for c in COUNTRIES.keys()]
                navigation.sync_films(countries=all_countries, dialog_title="Syncing MUBI Worldwide")

            # Refresh the container to return to the main menu after sync completes.
            xbmc.executebuiltin('Container.Refresh')
        except Exception as e:
            xbmc.log(f"Error in sync_worldwide action: {e}", xbmc.LOGERROR)
            xbmc.executebuiltin('Container.Refresh')
    elif action == "sync_github":
        xbmc.log(f"Calling sync_from_github with handle: {handle}", xbmc.LOGDEBUG)
        try:
            navigation.sync_from_github()
            xbmc.executebuiltin('Container.Refresh')
        except Exception as e:
            xbmc.log(f"Error in sync_github action: {e}", xbmc.LOGERROR)
            xbmc.executebuiltin('Container.Refresh')
    elif action == "play_mubi_video":
        xbmc.log(f"Calling play_mubi_video with handle: {handle}", xbmc.LOGDEBUG)
        film_id = params.get('film_id')
        web_url = params.get('web_url')
        if web_url:
            web_url = unquote_plus(web_url)
        try:
            # Country availability is now checked from NFO files, not passed as parameter
            navigation.play_mubi_video(film_id, web_url)
            # Note: play_mubi_video handles its own response via setResolvedUrl()
        except Exception as e:
            xbmc.log(f"Error in play_mubi_video action: {e}", xbmc.LOGERROR)
            # If playback fails, we need to signal failure to Kodi
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
    else:
        navigation.main_navigation()

