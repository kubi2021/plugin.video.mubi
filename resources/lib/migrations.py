# resources/lib/utils.py
import os
import xml.etree.ElementTree as ET
import xbmc
import xbmcvfs
import xbmcgui

def add_mubi_source():
    # Use xbmcvfs.translatePath instead of xbmc.translatePath
    sources_file = xbmcvfs.translatePath('special://profile/sources.xml')
    mubi_source_name = "MUBI Movies"
    mubi_path = 'special://userdata/addon_data/plugin.video.mubi'

    # If the sources.xml file does not exist, create it
    if not os.path.exists(sources_file):
        root = ET.Element("sources")
        videos = ET.SubElement(root, "video")
        tree = ET.ElementTree(root)
        tree.write(sources_file)

    # Parse the sources.xml file
    tree = ET.parse(sources_file)
    root = tree.getroot()

    # Check if the MUBI source already exists
    for source in root.findall("./video/source"):
        if source.find("path").text == mubi_path:
            xbmc.log("MUBI source already exists", level=xbmc.LOGINFO)
            return

    # Add the new MUBI source
    video_sources = root.find("video")
    new_source = ET.SubElement(video_sources, "source")

    name = ET.SubElement(new_source, "name")
    name.text = mubi_source_name

    path = ET.SubElement(new_source, "path")
    path.text = mubi_path
    path.set("pathversion", "1")

    allowsharing = ET.SubElement(new_source, "allowsharing")
    allowsharing.text = "true"

    # Save the updated sources.xml file
    tree.write(sources_file)
    xbmc.log("MUBI source added successfully", level=xbmc.LOGINFO)

    # Display a message to the user
    show_source_added_message()

def show_source_added_message():
    dialog = xbmcgui.Dialog()
    message = (
        "The MUBI Movies source has been added to your movies library.\n\n"
        "Please configure the source in Kodi settings > Media > Video:\n"
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
