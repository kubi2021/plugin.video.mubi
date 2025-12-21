# -*- coding: utf-8 -*-
import xbmc
import xbmcvfs
import requests
import xml.etree.ElementTree as ET
import tempfile
import os
from urllib.parse import urlparse

class MPDPatcher:
    """
    Patches MPEG-DASH (MPD) manifests to improve compatibility with Kodi.
    Specifically, it injects explicit Labels for audio streams based on their channel configuration,
    allowing Kodi to correctly prioritize Stereo vs Surround tracks based on system settings.
    """
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()

    def patch(self, stream_url, headers):
        """
        Downloads, patches, and saves the MPD manifest.
        
        :param stream_url: The original secure URL of the MPD manifest.
        :param headers: Dictionary of headers to use for the request.
        :return: Path to the local patched MPD file, or None if patching failed.
        """
        try:
            xbmc.log(f"MPDPatcher: Downloading manifest from {stream_url}", xbmc.LOGDEBUG)
            
            # Download manifest
            response = requests.get(stream_url, headers=headers, timeout=10)
            if response.status_code != 200:
                xbmc.log(f"MPDPatcher: Failed to download manifest (Status: {response.status_code})", xbmc.LOGERROR)
                return None
            
            manifest_content = response.text
            
            # Parse XML
            # Register namespaces to prevent 'ns0' prefixes
            ET.register_namespace('', "urn:mpeg:dash:schema:mpd:2011")
            # Some MPDs might use other namespaces, but this is the standard one
            
            try:
                root = ET.fromstring(manifest_content)
            except ET.ParseError as e:
                xbmc.log(f"MPDPatcher: Failed to parse XML: {e}", xbmc.LOGERROR)
                return None
            
            patched = False
            
            # Iterate through AdaptationSets
            # Namespace handling in ElementTree is verbose, so we use logic to handle it
            ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
            
            for adaptation_set in root.iter('{urn:mpeg:dash:schema:mpd:2011}AdaptationSet'):
                mime_type = adaptation_set.get('mimeType')
                adaptation_id = adaptation_set.get('id', 'unknown')
                xbmc.log(f"MPDPatcher: Inspecting AdaptationSet {adaptation_id} (mime: {mime_type})", xbmc.LOGINFO)
                
                if mime_type == 'audio/mp4':
                    # Look for AudioChannelConfiguration
                    # Standard scheme for channel config
                    acc_scheme = "urn:mpeg:dash:23003:3:audio_channel_configuration:2011"
                    
                    channel_count = None
                    acc_node = None
                    
                    # Log children tags for debugging
                    child_tags = [child.tag for child in adaptation_set]
                    xbmc.log(f"MPDPatcher: Children: {child_tags}", xbmc.LOGINFO)
                    acc_scheme = "urn:mpeg:dash:23003:3:audio_channel_configuration:2011"
                    
                    channel_count = None
                    acc_node = None
                    
                    # Find the AudioChannelConfiguration node
                    for child in adaptation_set:
                        tag_name = child.tag
                        if 'AudioChannelConfiguration' in tag_name:
                             local_scheme = child.get('schemeIdUri')
                             local_value = child.get('value')
                             xbmc.log(f"MPDPatcher: Found ACC node. Scheme: {local_scheme}, Value: {local_value}", xbmc.LOGINFO)
                             
                             # Standard MPEG-DASH scheme
                             if local_scheme == acc_scheme:
                                acc_node = child
                                channel_count = local_value
                                break
                             # Dolby scheme
                             elif local_scheme == "tag:dolby.com,2014:dash:audio_channel_configuration:2011":
                                 # F801 (hex) is the standard Dolby bitmask for 5.1 (L, C, R, Ls, Rs, LFE)
                                 # We can map this specific value to 6 channels
                                 if local_value and local_value.lower() == 'f801':
                                     xbmc.log("MPDPatcher: Detected Dolby 5.1 channel mask (F801)", xbmc.LOGINFO)
                                     acc_node = child
                                     channel_count = "6"
                                     break
                                 else:
                                     xbmc.log(f"MPDPatcher: Unknown Dolby channel mask: {local_value}", xbmc.LOGWARNING)
                             else:
                                xbmc.log(f"MPDPatcher: Scheme mismatch! Expected: {acc_scheme}", xbmc.LOGINFO)
                    
                    if channel_count:
                        # Create Label if missing
                        label_node = None
                        for child in adaptation_set:
                            if 'Label' in child.tag:
                                label_node = child
                                break
                        
                        if label_node is None:
                            label_node = ET.Element('{urn:mpeg:dash:schema:mpd:2011}Label')
                            adaptation_set.insert(0, label_node)
                        
                        # Add Role element to guide default selection
                        # We want Stereo (2.0) to be MAIN, and Surround (5.1) to be ALTERNATE
                        # This helps Kodi select Stereo by default if user preferences are standard
                        
                        role_node = None
                        for child in adaptation_set:
                            if 'Role' in child.tag and child.get('schemeIdUri') == "urn:mpeg:dash:role:2011":
                                role_node = child
                                break
                        
                        if role_node is None:
                            role_node = ET.Element('{urn:mpeg:dash:schema:mpd:2011}Role')
                            role_node.set('schemeIdUri', "urn:mpeg:dash:role:2011")
                            adaptation_set.insert(0, role_node)

                        lang = adaptation_set.get('lang', 'en')
                        
                        if str(channel_count) == "2":
                            label_node.text = "Stereo (2.0)"
                            role_node.set('value', 'main')
                            xbmc.log(f"MPDPatcher: Added Label 'Stereo (2.0)' and Role 'main' to audio track ({lang})", xbmc.LOGDEBUG)
                            patched = True # Mark as patched if we modified
                        elif str(channel_count) == "6":
                            label_node.text = "Surround (5.1)"
                            role_node.set('value', 'alternate')
                            xbmc.log(f"MPDPatcher: Added Label 'Surround (5.1)' and Role 'alternate' to audio track ({lang})", xbmc.LOGDEBUG)
                            patched = True # Mark as patched if we modified
                        else:
                            label_node.text = f"Audio ({channel_count}ch)"
                            # For other channel counts, we don't assign a specific role
                            xbmc.log(f"MPDPatcher: Added Label 'Audio ({channel_count}ch)' to audio track ({lang})", xbmc.LOGDEBUG)
                            patched = True # Mark as patched if we modified
                            # No 'else' for role_node.set('value') here, as we only set for 2 and 6.

            if patched:
                # Ensure BaseURL is absolute
                # If the manifest uses relative segments, we need an absolute BaseURL 
                # pointing to the original location so resolving continues to work from the local file
                
                # Check for existing BaseURL
                base_url_node = root.find('{urn:mpeg:dash:schema:mpd:2011}BaseURL')
                
                if base_url_node is None:
                    # Create BaseURL pointing to the directory of the stream_url
                    import os.path
                    
                    # Logic to get base path from URL
                    # e.g. https://example.com/stream/manifest.mpd -> https://example.com/stream/
                    base_path = stream_url.rsplit('/', 1)[0] + '/'
                    
                    new_base = ET.Element('{urn:mpeg:dash:schema:mpd:2011}BaseURL')
                    new_base.text = base_path
                    root.insert(0, new_base)
                    xbmc.log(f"MPDPatcher: Injected BaseURL: {base_path}", xbmc.LOGDEBUG)
                
                # Save to Kodi's temp directory
                temp_dir = xbmcvfs.translatePath("special://temp/")
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)

                fd, abs_path = tempfile.mkstemp(suffix='.mpd', prefix='mubi_patched_', dir=temp_dir)
                
                # Write back
                with os.fdopen(fd, 'wb') as f:
                    tree = ET.ElementTree(root)
                    tree.write(f, encoding='UTF-8', xml_declaration=True)
                
                # Convert absolute path back to special:// URI for Kodi
                filename = os.path.basename(abs_path)
                special_path = f"special://temp/{filename}"
                
                xbmc.log(f"MPDPatcher: Saved patched manifest to {special_path} ({abs_path})", xbmc.LOGINFO)
                return special_path
            
            else:
                xbmc.log("MPDPatcher: No audio tracks found to patch. Returning original.", xbmc.LOGDEBUG)
                return None

        except Exception as e:
            xbmc.log(f"MPDPatcher: Error during patching: {e}", xbmc.LOGERROR)
            return None
