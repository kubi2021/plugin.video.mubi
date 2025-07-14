# resources/lib/utils.py
import xml.etree.ElementTree as ET
import xbmc
import xbmcvfs
import xbmcgui

def add_mubi_sources():
    """Add both MUBI Movies and MUBI Series sources to Kodi."""
    movies_added = add_mubi_movies_source()
    series_added = add_mubi_series_source()

    # Show message if any source was added
    if movies_added or series_added:
        show_sources_added_message()

def add_mubi_movies_source():
    """Add MUBI Movies source to Kodi video library."""
    sources_file = xbmcvfs.translatePath('special://profile/sources.xml')
    mubi_source_name = "MUBI Movies"
    mubi_path = 'special://userdata/addon_data/plugin.video.mubi/films'

    try:
        # Check if the sources.xml file exists
        if not xbmcvfs.exists(sources_file):
            # Create a new sources.xml file with the basic structure
            root = ET.Element("sources")
            ET.SubElement(root, "video")
            tree = ET.ElementTree(root)
            write_xml(tree, sources_file)
            xbmc.log("Created new sources.xml file", level=xbmc.LOGINFO)

        # Read and parse the sources.xml file
        tree = read_xml(sources_file)
        if tree is None:
            return  # Exit if the XML could not be read

        root = tree.getroot()

        # Check if the MUBI Movies source already exists
        mubi_exists = False
        for source in root.findall("./video/source"):
            path_element = source.find("path")
            if path_element is not None and path_element.text == mubi_path:
                xbmc.log("MUBI Movies source already exists", level=xbmc.LOGINFO)
                mubi_exists = True
                break

        if not mubi_exists:
            # Add the new MUBI Movies source
            video_sources = root.find("video")
            if video_sources is None:
                video_sources = ET.SubElement(root, "video")

            new_source = ET.SubElement(video_sources, "source")

            name = ET.SubElement(new_source, "name")
            name.text = mubi_source_name

            path = ET.SubElement(new_source, "path")
            path.text = mubi_path
            path.set("pathversion", "1")

            allowsharing = ET.SubElement(new_source, "allowsharing")
            allowsharing.text = "true"

            # Write the updated XML back to the sources.xml file
            write_xml(tree, sources_file)
            xbmc.log("MUBI Movies source added successfully", level=xbmc.LOGINFO)

            # Show message only after both sources are processed
            return True  # Indicate source was added

        return False  # Source already exists or wasn't added

    except Exception as e:
        xbmc.log(f"An error occurred in add_mubi_movies_source: {e}", level=xbmc.LOGERROR)
        return False

def add_mubi_series_source():
    """Add MUBI Series source to Kodi video library (same as movies, but in series subfolder)."""
    sources_file = xbmcvfs.translatePath('special://profile/sources.xml')
    mubi_source_name = "MUBI Series"
    mubi_path = 'special://userdata/addon_data/plugin.video.mubi/series'

    try:
        # Check if the sources.xml file exists
        if not xbmcvfs.exists(sources_file):
            # Create a new sources.xml file with the basic structure
            root = ET.Element("sources")
            ET.SubElement(root, "video")
            tree = ET.ElementTree(root)
            write_xml(tree, sources_file)
            xbmc.log("Created new sources.xml file", level=xbmc.LOGINFO)

        # Read and parse the sources.xml file
        tree = read_xml(sources_file)
        if tree is None:
            return False  # Exit if the XML could not be read

        root = tree.getroot()

        # Add to video sources (same as movies) - Kodi handles TV shows in video sources too
        video_sources = root.find("video")
        if video_sources is None:
            video_sources = ET.SubElement(root, "video")

        # Check if the MUBI Series source already exists
        mubi_exists = False
        for source in video_sources.findall("source"):
            path_element = source.find("path")
            if path_element is not None and path_element.text == mubi_path:
                xbmc.log("MUBI Series source already exists", level=xbmc.LOGINFO)
                mubi_exists = True
                break

        if not mubi_exists:
            # Add the new MUBI Series source to video sources
            new_source = ET.SubElement(video_sources, "source")

            name = ET.SubElement(new_source, "name")
            name.text = mubi_source_name

            path = ET.SubElement(new_source, "path")
            path.text = mubi_path
            path.set("pathversion", "1")

            allowsharing = ET.SubElement(new_source, "allowsharing")
            allowsharing.text = "true"

            # Write the updated XML back to the sources.xml file
            write_xml(tree, sources_file)
            xbmc.log("MUBI Series source added successfully", level=xbmc.LOGINFO)

            return True  # Indicate source was added

        return False  # Source already exists or wasn't added

    except Exception as e:
        xbmc.log(f"An error occurred in add_mubi_series_source: {e}", level=xbmc.LOGERROR)
        return False

def read_xml(file_path):
    try:
        if xbmcvfs.exists(file_path):
            with xbmcvfs.File(file_path, 'r') as f:
                content = f.read()
            tree = ET.ElementTree(ET.fromstring(content))
            xbmc.log(f"Successfully read XML file: {file_path}", level=xbmc.LOGDEBUG)
            return tree
        else:
            xbmc.log(f"XML file does not exist: {file_path}", level=xbmc.LOGWARNING)
            return None
    except Exception as e:
        xbmc.log(f"Error reading XML file {file_path}: {e}", level=xbmc.LOGERROR)
        return None

def write_xml(tree, file_path):
    try:
        content = ET.tostring(tree.getroot(), encoding='unicode', method='xml')
        with xbmcvfs.File(file_path, 'w') as f:
            f.write(content)
        xbmc.log(f"Successfully wrote XML file: {file_path}", level=xbmc.LOGDEBUG)
    except Exception as e:
        xbmc.log(f"Error writing XML file {file_path}: {e}", level=xbmc.LOGERROR)


def show_sources_added_message():
    """Show message about both MUBI sources being added."""
    dialog = xbmcgui.Dialog()
    message = (
        "MUBI sources have been added to your video library:\n\n"
        "• MUBI Movies - Points to /films folder\n"
        "• MUBI Series - Points to /series folder\n\n"
        "Restart Kodi for the sources to be visible, then configure them in:\n"
        "Settings > Media > Library > Video Sources\n\n"
        "IMPORTANT: Set the correct content types:\n"
        "• MUBI Movies: Set content type to 'Movies'\n"
        "• MUBI Series: Set content type to 'TV Shows'\n\n"
        "This ensures proper metadata scraping for each type."
    )
    dialog.ok("MUBI Sources Added", message)

def is_first_run(plugin):
    # Check if the addon is running for the first time by checking a setting
    try:
        return plugin.getSetting('first_run_completed') != 'true'
    except Exception:
        return True  # If setting doesn't exist, assume first run

def mark_first_run(plugin):
    # Mark that the first run has been completed
    try:
        plugin.setSetting('first_run_completed', 'true')
    except Exception as e:
        xbmc.log(f"Error marking first run: {e}", xbmc.LOGERROR)

# Backward compatibility - maintain old function name
def add_mubi_source():
    """Backward compatibility wrapper for add_mubi_sources()."""
    add_mubi_sources()

def ensure_series_source_exists(plugin):
    """
    Ensure the MUBI Series source exists, even for existing installations.
    This can be called to add the series source if it was missed in previous versions.
    """
    try:
        # Check if we've already added the series source
        series_source_added_key = 'series_source_added'

        # Use getSetting() with string comparison for safer handling
        series_already_added = plugin.getSetting(series_source_added_key)
        if series_already_added == 'true':
            return False  # Already added

        # Try to add the series source
        series_added = add_mubi_series_source()

        if series_added:
            # Mark that we've added the series source
            plugin.setSetting(series_source_added_key, 'true')
            xbmc.log("Series source added for existing installation", xbmc.LOGINFO)

            # Show a specific message for series source
            dialog = xbmcgui.Dialog()
            message = (
                "MUBI Series source has been added to your video library!\n\n"
                "Restart Kodi to see the new source, then configure it in:\n"
                "Settings > Media > Library > Video Sources\n\n"
                "Set the content type to 'TV Shows' for proper metadata."
            )
            dialog.ok("MUBI Series Added", message, xbmcgui.NOTIFICATION_INFO, 8000)

            return True

        return False

    except Exception as e:
        xbmc.log(f"Error in ensure_series_source_exists: {e}", xbmc.LOGERROR)
        return False
