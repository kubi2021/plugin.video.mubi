# resources/lib/utils.py
import xml.etree.ElementTree as ET
import xbmc
import xbmcvfs
import xbmcgui

def add_mubi_source():
    sources_file = xbmcvfs.translatePath('special://profile/sources.xml')
    mubi_source_name = "MUBI Movies"
    mubi_path = 'special://userdata/addon_data/plugin.video.mubi'

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

        # Check if the MUBI source already exists
        mubi_exists = False
        for source in root.findall("./video/source"):
            path_element = source.find("path")
            if path_element is not None and path_element.text == mubi_path:
                xbmc.log("MUBI source already exists", level=xbmc.LOGINFO)
                mubi_exists = True
                break

        if not mubi_exists:
            # Add the new MUBI source
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
            xbmc.log("MUBI source added successfully", level=xbmc.LOGINFO)

            # Display a message to the user
            show_source_added_message()
    except Exception as e:
        xbmc.log(f"An error occurred in add_mubi_source: {e}", level=xbmc.LOGERROR)

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


def show_source_added_message():
    dialog = xbmcgui.Dialog()
    message = (
        "The MUBI Movies source has been added to your movies library. Kodi needs to be restarted for the source to be visible."
        "Reastart Kodi and configure the source in Kodi settings > Media > Video:\n"
        "1. Set the content type to 'Video'.\n"
        "2. Configure the scraper to fetch metadata for this source."
    )
    dialog.ok("MUBI Source Added", message)

def is_first_run(plugin):
    # Check if the addon is running for the first time by checking a setting
    return not plugin.getSettingBool('first_run_completed')

def mark_first_run(plugin):
    # Mark that the first run has been completed
    plugin.setSettingBool('first_run_completed', True)
