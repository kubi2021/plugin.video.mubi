import os
from pathlib import Path
import xbmc
import xml.etree.ElementTree as ET
import requests
from requests.exceptions import RequestException
import json
import time
import re
from typing import Optional, List
import re
from pathlib import Path





class Film:
    def __init__(self, mubi_id: str, title: str, artwork: str, web_url: str, metadata):
        if not mubi_id or not metadata:
            raise ValueError("Film must have a mubi_id and metadata")

        # Handle edge case where title might be empty or only prohibited characters
        if not title or not title.strip():
            title = "Unknown Movie"

        self.mubi_id = mubi_id
        self.title = title  # Keep original title for NFO content
        self.artwork = artwork
        self.web_url = web_url
        self.metadata = metadata

    def __eq__(self, other):
        if not isinstance(other, Film):
            return False
        return self.mubi_id == other.mubi_id

    def __hash__(self):
        return hash(self.mubi_id)




    def _sanitize_filename(self, filename: str) -> str:
        """
        LEVEL 2 FILESYSTEM SAFETY PROTECTION

        Sanitize filename by removing only filesystem-dangerous characters while
        preserving normal punctuation for good user experience.

        LEVEL 2 REMOVES:
        - Filesystem-dangerous: < > : " / \ | ? *
        - Path traversal: .. ... ....
        - Windows reserved names: CON, PRN, etc.
        - Control characters and dangerous Unicode

        LEVEL 2 PRESERVES:
        - Normal punctuation: ' & , ( ) + = @ # ~ ! $ % ^ [ ] { }
        - International characters: Amélie, 東京物語, etc.
        - Common symbols that are filesystem-safe

        :param filename: The original file name.
        :return: A Level 2 sanitized file name.
        """
        if not filename:
            return "unknown"

        # Convert to string and handle None
        sanitized = str(filename) if filename is not None else "unknown"

        # LEVEL 2: Remove path traversal sequences (security)
        # Remove any sequence of 2 or more consecutive dots
        sanitized = re.sub(r'\.{2,}', '', sanitized)

        # LEVEL 2: Remove ONLY filesystem-dangerous characters
        # These characters cause issues on Windows/Mac/Linux filesystems
        sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)

        # LEVEL 2: Remove control characters (security)
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)

        # LEVEL 2: Remove dangerous Unicode sequences (security)
        sanitized = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', sanitized)  # Control chars
        # Zero-width and directional characters
        sanitized = re.sub(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F]', '', sanitized)
        sanitized = re.sub(r'[\uFEFF\uFFFE\uFFFF]', '', sanitized)  # BOM and non-characters

        # LEVEL 2: Handle Windows reserved names
        reserved_names = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
            "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        if sanitized.upper() in reserved_names:
            sanitized = f"{sanitized}_"  # Add suffix to avoid reserved name conflict

        # LEVEL 2: Normalize whitespace (preserve single spaces)
        sanitized = re.sub(r'\s+', ' ', sanitized)  # Replace multiple spaces with single space

        # Strip trailing periods and spaces
        sanitized = sanitized.rstrip(". ")

        # Strip leading spaces
        sanitized = sanitized.lstrip(" ")

        # Ensure we have some content
        if not sanitized or sanitized.isspace():
            sanitized = "unknown_file"

        # Enforce length limit (255 characters for most filesystems)
        max_length = 255
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip(". ")

        # Final safety check: ensure we never return empty filename
        final_result = sanitized.strip()
        if not final_result or final_result.isspace():
            final_result = "unknown_file"

        return final_result

    def _sanitize_xml_content(self, content) -> str:
        """
        LEVEL 2 NFO CONTENT PROTECTION

        For NFO content, Level 2 preserves normal punctuation and movie title characters
        while removing only truly dangerous patterns that could break XML or cause security issues.

        LEVEL 2 NFO PRESERVES:
        - Normal punctuation: ? : & , ' " ( ) etc.
        - International characters: Amélie, 東京物語, etc.
        - Movie title formatting: "Movie: Subtitle", "What's Up?", etc.

        LEVEL 2 NFO REMOVES:
        - Only truly dangerous injection patterns
        - Control characters that break XML

        :param content: Content to sanitize for NFO
        :return: Level 2 sanitized content safe for XML
        """
        if content is None:
            return ""

        # Convert to string
        sanitized = str(content)

        # LEVEL 2: Remove only truly dangerous patterns for NFO content
        # Note: ElementTree automatically escapes XML special characters (&, <, >, etc.)

        # Remove control characters that could break XML parsing
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)

        # Remove dangerous Unicode sequences
        sanitized = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', sanitized)
        sanitized = re.sub(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F]', '', sanitized)
        sanitized = re.sub(r'[\uFEFF\uFFFE\uFFFF]', '', sanitized)

        # LEVEL 2: Preserve all normal punctuation for movie titles
        # This includes: ? : & , ' " ( ) + = @ # ~ ! $ % ^ [ ] { } etc.
        # Only remove truly dangerous patterns if needed for security

        # SECURITY FIX: Remove dangerous Unicode sequences
        sanitized = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', sanitized)  # Control chars
        sanitized = re.sub(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F]', '', sanitized)  # Zero-width and directional
        sanitized = re.sub(r'[\uFEFF\uFFFE\uFFFF]', '', sanitized)  # BOM and non-characters

        # Remove script tags and javascript URLs
        sanitized = re.sub(r'(?i)<script[^>]*>.*?</script>', '', sanitized)
        sanitized = re.sub(r'(?i)javascript:', '', sanitized)

        # Remove XML processing instructions and DOCTYPE declarations
        sanitized = re.sub(r'<\?xml[^>]*\?>', '', sanitized)
        sanitized = re.sub(r'<!DOCTYPE[^>]*>', '', sanitized)
        sanitized = re.sub(r'<!ENTITY[^>]*>', '', sanitized)

        # The XML library will handle proper escaping of &, <, >, etc.
        # when we assign to .text, so we don't need to manually escape those

        return sanitized.strip()

    def get_sanitized_folder_name(self) -> str:
        """
        Generate a consistent, sanitized folder name for the film, using the title and year.

        :return: A sanitized folder name in the format "Title (Year)".
        """
        # First sanitize the title to remove problematic characters including trailing periods
        sanitized_title = self._sanitize_filename(self.title)
        year = self.metadata.year if self.metadata.year else "Unknown"
        folder_name = f"{sanitized_title} ({year})"

        # Enforce length limit on the final folder name
        max_length = 255
        if len(folder_name) > max_length:
            # Calculate how much space we need for " (year)"
            year_suffix = f" ({year})"
            available_length = max_length - len(year_suffix)
            if available_length > 0:
                sanitized_title = sanitized_title[:available_length].rstrip()
                folder_name = f"{sanitized_title} ({year})"
            else:
                # If even the year suffix is too long, just truncate everything
                folder_name = folder_name[:max_length]

        return folder_name


    def create_strm_file(self, film_path: Path, base_url: str):
        """Create the .strm file for the film."""
        from urllib.parse import urlencode

        # Use sanitized folder name for consistent file naming
        film_folder_name = self.get_sanitized_folder_name()
        film_file_name = f"{film_folder_name}.strm"
        film_strm_file = film_path / film_file_name

        # Build the query parameters
        query_params = {
            'action': 'play_mubi_video',
            'film_id': self.mubi_id,
            'web_url': self.web_url
        }
        encoded_params = urlencode(query_params)
        kodi_movie_url = f"{base_url}?{encoded_params}"

        try:
            with open(film_strm_file, "w") as f:
                f.write(kodi_movie_url)
        except OSError as error:
            xbmc.log(f"Error while creating STRM file for {self.title}: {error}", xbmc.LOGERROR)
            # BUG #9 FIX: Re-raise the exception so caller knows the operation failed
            raise

    def create_nfo_file(self, film_path: Path, base_url: str, omdb_api_key: str):
        """Create the .nfo file for the film."""
        # Use sanitized folder name for consistent file naming
        film_folder_name = self.get_sanitized_folder_name()
        nfo_file_name = f"{film_folder_name}.nfo"
        nfo_file = film_path / nfo_file_name
        kodi_trailer_url = f"{base_url}?action=play_trailer&url={self.metadata.trailer}"

        # Download all available artwork locally for offline access
        artwork_paths = self._download_all_artwork(film_path, film_folder_name)

        try:
            imdb_url = ""
            if omdb_api_key:
                time.sleep(2)
                imdb_url = self._get_imdb_url(self.metadata.originaltitle, self.title, self.metadata.year, omdb_api_key)

                if imdb_url is None:
                    xbmc.log(f"Creating NFO file for '{self.title}' without IMDb URL due to API errors.", xbmc.LOGWARNING)
                    # Still create NFO file without IMDb URL rather than failing completely
                    imdb_url = ""

            nfo_tree = self._get_nfo_tree(self.metadata, kodi_trailer_url, imdb_url, artwork_paths)
            with open(nfo_file, "wb") as f:
                if isinstance(nfo_tree, str):
                    nfo_tree = nfo_tree.encode("utf-8")
                f.write(nfo_tree)

            if not nfo_file.exists():
                xbmc.log(f"Failed to create NFO file for '{self.title}'", xbmc.LOGWARNING)
            else:
                xbmc.log(f"NFO file successfully created at {nfo_file}", xbmc.LOGDEBUG)

        except (OSError, ValueError) as error:
            xbmc.log(f"Error while creating NFO file for {self.title}: {error}", xbmc.LOGERROR)



    def _get_nfo_tree(self, metadata, kodi_trailer_url: str, imdb_url: str, artwork_paths: dict = None) -> bytes:
        """Generate the NFO XML tree structure, including IMDb URL if available."""
        if not metadata.title:
            raise ValueError("Metadata must contain a title")

        movie = ET.Element("movie")

        # SECURITY FIX: Sanitize all text content before adding to XML
        ET.SubElement(movie, "title").text = self._sanitize_xml_content(metadata.title)
        ET.SubElement(movie, "originaltitle").text = self._sanitize_xml_content(metadata.originaltitle)

        ratings = ET.SubElement(movie, "ratings")
        rating = ET.SubElement(ratings, "rating")
        rating.set("name", "MUBI")
        rating.set("max", "10")  # Specify 10-point scale for Kodi
        ET.SubElement(rating, "value").text = str(metadata.rating)
        ET.SubElement(rating, "votes").text = str(metadata.votes)

        ET.SubElement(movie, "plot").text = self._sanitize_xml_content(metadata.plot)
        ET.SubElement(movie, "outline").text = self._sanitize_xml_content(metadata.plotoutline)
        ET.SubElement(movie, "runtime").text = str(metadata.duration)

        # Add content rating (age rating)
        if metadata.mpaa:
            ET.SubElement(movie, "mpaa").text = self._sanitize_xml_content(metadata.mpaa)

        # Add tagline from press_quote (if available)
        if hasattr(metadata, 'tagline') and metadata.tagline:
            ET.SubElement(movie, "tagline").text = self._sanitize_xml_content(metadata.tagline)

        # Support multiple country tags (previously only used first)
        if metadata.country:
            for country in metadata.country:
                ET.SubElement(movie, "country").text = self._sanitize_xml_content(country)

        for genre in metadata.genre:
            ET.SubElement(movie, "genre").text = self._sanitize_xml_content(genre)

        for director in metadata.director:
            ET.SubElement(movie, "director").text = self._sanitize_xml_content(director)

        ET.SubElement(movie, "year").text = str(metadata.year)

        # Add premiered date (Kodi v20+ prefers this over deprecated <year>)
        if hasattr(metadata, 'premiered') and metadata.premiered:
            ET.SubElement(movie, "premiered").text = self._sanitize_xml_content(metadata.premiered)

        # Add content warnings as library tags
        if hasattr(metadata, 'content_warnings') and metadata.content_warnings:
            for warning in metadata.content_warnings:
                if warning and str(warning).strip():
                    ET.SubElement(movie, "tag").text = self._sanitize_xml_content(str(warning).strip())
        # SECURITY FIX: Sanitize trailer URL to prevent injection
        ET.SubElement(movie, "trailer").text = self._sanitize_xml_content(kodi_trailer_url)

        # Add all available artwork types
        if artwork_paths is None:
            artwork_paths = {}

        # Thumbnail/Landscape artwork
        thumb = ET.SubElement(movie, "thumb")
        thumb.set("aspect", "landscape")
        if 'thumb' in artwork_paths and Path(artwork_paths['thumb']).exists():
            thumb.text = Path(artwork_paths['thumb']).name
            xbmc.log(f"Using local thumbnail: {Path(artwork_paths['thumb']).name}", xbmc.LOGDEBUG)
        else:
            thumb.text = metadata.image
            xbmc.log(f"Using remote thumbnail URL: {metadata.image}", xbmc.LOGDEBUG)

        # Poster artwork (vertical)
        if artwork_paths and 'poster' in artwork_paths and Path(artwork_paths['poster']).exists():
            poster = ET.SubElement(movie, "poster")
            poster.text = Path(artwork_paths['poster']).name
            xbmc.log(f"Using local poster: {Path(artwork_paths['poster']).name}", xbmc.LOGDEBUG)

        # Fanart artwork (background)
        if artwork_paths and 'fanart' in artwork_paths and Path(artwork_paths['fanart']).exists():
            fanart = ET.SubElement(movie, "fanart")
            fanart_thumb = ET.SubElement(fanart, "thumb")
            fanart_thumb.text = Path(artwork_paths['fanart']).name
            xbmc.log(f"Using local fanart: {Path(artwork_paths['fanart']).name}", xbmc.LOGDEBUG)

        # Clear logo (transparent title)
        if (artwork_paths and 'clearlogo' in artwork_paths
                and Path(artwork_paths['clearlogo']).exists()):
            clearlogo = ET.SubElement(movie, "clearlogo")
            clearlogo.text = Path(artwork_paths['clearlogo']).name
            clearlogo_name = Path(artwork_paths['clearlogo']).name
            xbmc.log(f"Using local clearlogo: {clearlogo_name}", xbmc.LOGDEBUG)

        # Audio and subtitle language information using official Kodi structure
        # Only add fileinfo/streamdetails if we have audio or subtitle data
        if ((hasattr(metadata, 'audio_languages') and metadata.audio_languages) or
            (hasattr(metadata, 'subtitle_languages') and metadata.subtitle_languages)):

            fileinfo = ET.SubElement(movie, "fileinfo")
            streamdetails = ET.SubElement(fileinfo, "streamdetails")

            # Audio streams - create separate <audio> element for each language
            # Include channel information if available
            if hasattr(metadata, 'audio_languages') and metadata.audio_languages:
                audio_channels = getattr(metadata, 'audio_channels', [])
                for i, lang in enumerate(metadata.audio_languages):
                    if lang and str(lang).strip():  # Skip empty/None values
                        audio_elem = ET.SubElement(streamdetails, "audio")
                        audio_lang = ET.SubElement(audio_elem, "language")
                        # SECURITY FIX: Sanitize language content
                        audio_lang.text = self._sanitize_xml_content(str(lang).strip())

                        # Add channel info if available (convert "5.1" -> 6, "stereo" -> 2)
                        if i < len(audio_channels) and audio_channels[i]:
                            channel_str = str(audio_channels[i]).strip().lower()
                            channels_elem = ET.SubElement(audio_elem, "channels")
                            # Convert channel format to number
                            if channel_str == '5.1':
                                channels_elem.text = '6'
                            elif channel_str == '7.1':
                                channels_elem.text = '8'
                            elif channel_str in ('stereo', '2.0'):
                                channels_elem.text = '2'
                            elif channel_str in ('mono', '1.0'):
                                channels_elem.text = '1'
                            else:
                                # Keep original value if not a recognized format
                                channels_elem.text = self._sanitize_xml_content(channel_str)

            # Subtitle streams - create separate <subtitle> element for each language
            if hasattr(metadata, 'subtitle_languages') and metadata.subtitle_languages:
                for lang in metadata.subtitle_languages:
                    if lang and str(lang).strip():  # Skip empty/None values
                        subtitle_elem = ET.SubElement(streamdetails, "subtitle")
                        subtitle_lang = ET.SubElement(subtitle_elem, "language")
                        # SECURITY FIX: Sanitize language content
                        subtitle_lang.text = self._sanitize_xml_content(str(lang).strip())



        ET.SubElement(movie, "dateadded").text = self._sanitize_xml_content(str(metadata.dateadded))

        # Add IMDb URL if available
        if imdb_url:
            # SECURITY FIX: Sanitize IMDb URL to prevent injection
            ET.SubElement(movie, "imdbid").text = self._sanitize_xml_content(imdb_url)

        return ET.tostring(movie)

    def _download_thumbnail(self, film_path: Path, film_folder_name: str) -> Optional[str]:
        """
        Download the thumbnail image locally for offline access.

        :param film_path: Path to the film folder
        :param film_folder_name: Sanitized folder name for the film
        :return: Local path to downloaded thumbnail or None if failed
        """
        if not self.metadata.image:
            xbmc.log(f"No thumbnail URL available for '{self.title}'", xbmc.LOGDEBUG)
            return None

        try:
            # Determine file extension from URL
            image_url = self.metadata.image
            if '.jpg' in image_url.lower():
                extension = '.jpg'
            elif '.png' in image_url.lower():
                extension = '.png'
            elif '.jpeg' in image_url.lower():
                extension = '.jpeg'
            else:
                extension = '.jpg'  # Default fallback

            # Create local thumbnail filename following Kodi conventions
            thumbnail_filename = f"{film_folder_name}-thumb{extension}"
            local_thumbnail_path = film_path / thumbnail_filename

            # Skip download if file already exists
            if local_thumbnail_path.exists():
                xbmc.log(f"Thumbnail already exists for '{self.title}': {local_thumbnail_path}", xbmc.LOGDEBUG)
                return str(local_thumbnail_path)

            # Download the thumbnail
            xbmc.log(f"Downloading thumbnail for '{self.title}' from {image_url}", xbmc.LOGDEBUG)
            response = requests.get(image_url, timeout=30, stream=True)
            response.raise_for_status()

            # Save the thumbnail locally
            with open(local_thumbnail_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            xbmc.log(f"Successfully downloaded thumbnail for '{self.title}' to {local_thumbnail_path}", xbmc.LOGDEBUG)
            return str(local_thumbnail_path)

        except Exception as e:
            xbmc.log(f"Failed to download thumbnail for '{self.title}': {e}", xbmc.LOGWARNING)
            return None

    def _download_all_artwork(self, film_path: Path, film_folder_name: str) -> dict:
        """
        Download all available artwork types locally for offline access.

        :param film_path: Path to the film folder
        :param film_folder_name: Sanitized folder name for the film
        :return: Dictionary mapping artwork types to local file paths
        """
        artwork_paths = {}

        try:
            # Get artwork URLs from metadata
            artwork_urls = self._get_all_artwork_urls()

            for artwork_type, url in artwork_urls.items():
                if not url:
                    continue

                try:
                    # Determine file extension
                    if '.jpg' in url.lower():
                        extension = '.jpg'
                    elif '.png' in url.lower():
                        extension = '.png'
                    elif '.jpeg' in url.lower():
                        extension = '.jpeg'
                    else:
                        extension = '.jpg'  # Default fallback

                    # Create filename following Kodi conventions
                    if artwork_type == 'thumb':
                        filename = f"{film_folder_name}-thumb{extension}"
                    elif artwork_type == 'poster':
                        filename = f"{film_folder_name}-poster{extension}"

                    elif artwork_type == 'clearlogo':
                        filename = f"{film_folder_name}-clearlogo{extension}"
                    else:
                        filename = f"{film_folder_name}-{artwork_type}{extension}"

                    local_path = film_path / filename

                    # Skip download if file already exists
                    if local_path.exists():
                        xbmc.log(f"{artwork_type.title()} already exists for '{self.title}': {local_path}", xbmc.LOGDEBUG)
                        artwork_paths[artwork_type] = str(local_path)
                        continue

                    # Download the artwork
                    xbmc.log(f"Downloading {artwork_type} for '{self.title}' from {url}", xbmc.LOGDEBUG)
                    response = requests.get(url, timeout=30, stream=True)
                    response.raise_for_status()

                    # Save the artwork locally
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    artwork_paths[artwork_type] = str(local_path)
                    xbmc.log(f"Successfully downloaded {artwork_type} for '{self.title}' to {local_path}", xbmc.LOGDEBUG)

                except Exception as e:
                    xbmc.log(f"Failed to download {artwork_type} for '{self.title}': {e}", xbmc.LOGWARNING)
                    continue

            return artwork_paths

        except Exception as e:
            xbmc.log(f"Error downloading artwork for '{self.title}': {e}", xbmc.LOGERROR)
            return {}

    def _get_all_artwork_urls(self) -> dict:
        """
        Get all available artwork URLs from metadata.

        :return: Dictionary mapping artwork types to URLs
        """
        artwork_urls = {}

        # Get artwork URLs from metadata
        if hasattr(self.metadata, 'artwork_urls') and self.metadata.artwork_urls:
            artwork_urls.update(self.metadata.artwork_urls)

        # Always include the main image as thumb
        if self.metadata.image:
            artwork_urls['thumb'] = self.metadata.image

        return artwork_urls





    def _get_imdb_url(self, original_title: str, english_title: str, year: str, omdb_api_key: str) -> Optional[str]:
        """Fetch the IMDb URL using the OMDb API with retry logic and alternative spelling handling."""
        max_retries = 10  # Maximum number of retries per title
        backoff_factor = 1  # Start with a 1-second delay and double with each retry

        # Step 1: If original and English titles are the same, skip the original title
        use_original_title = self._should_use_original_title(original_title, english_title)

        # Step 2: Normalize the English title by removing "and" and "&"
        english_title_cleaned = self._normalize_title(english_title)

        # Try with original title, then clean English title, then try alternative spellings
        imdb_url = self._attempt_fetch_with_titles(original_title, english_title_cleaned, year, omdb_api_key, max_retries, backoff_factor)
    
        return imdb_url or ""
    
    def _should_use_original_title(self, original_title: str, english_title: str) -> bool:
        """Determine whether to use the original title based on its similarity to the English title."""
        if original_title.strip().lower() == english_title.strip().lower():
            xbmc.log(f"Original and English title are the same: '{original_title}'. Skipping the original title.", xbmc.LOGDEBUG)
            return False
        return True

    def _attempt_fetch_with_titles(
        self,
        original_title: str,
        english_title: str,
        year: str,
        omdb_api_key: str,
        max_attempts: int,
        initial_backoff: float = 1.0
    ) -> Optional[str]:
        """Attempt to fetch IMDb URL with the original, cleaned English, and alternative spellings."""

        # Prepare the list of titles to try
        titles_to_try = []

        # If original title and English title are different, add original title
        if original_title.strip().lower() != english_title.strip().lower():
            titles_to_try.append(original_title.strip())

        # Normalize the English title by removing 'and' and '&'
        english_title_cleaned = self._normalize_title(english_title.strip())
        titles_to_try.append(english_title_cleaned)

        # Generate alternative titles by applying word variations
        alternative_titles = self._generate_alternative_titles(english_title_cleaned)
        titles_to_try.extend(alternative_titles)

        total_attempts = 0
        backoff = initial_backoff

        for title in titles_to_try:
            if total_attempts >= max_attempts:
                break  # Exit if max attempts reached

            params = {"apikey": omdb_api_key, "t": title, "type": "movie", "y": year}

            while total_attempts < max_attempts:
                try:
                    xbmc.log(f"Attempt {total_attempts + 1} to fetch IMDb URL for '{title}' ({year})", xbmc.LOGDEBUG)

                    # Make the OMDb API request
                    response = requests.get("http://www.omdbapi.com/", params=params, timeout=10)
                    response.raise_for_status()

                    data = response.json()
                    xbmc.log(f"OMDb API response for title '{title}': {json.dumps(data, indent=4)}", xbmc.LOGDEBUG)

                    # Check if IMDb ID is found
                    if "imdbID" in data:
                        imdb_id = data["imdbID"]
                        xbmc.log(f"IMDb URL found: {imdb_id} for title '{title}' ({year})", xbmc.LOGINFO)
                        return f"https://www.imdb.com/title/{imdb_id}/"
                    else:
                        xbmc.log(f"IMDb ID not found in response for '{title}' ({year})", xbmc.LOGDEBUG)
                        break  # Break to try the next title

                except requests.exceptions.HTTPError as http_err:
                    status_code = http_err.response.status_code
                    if status_code in [401, 402, 429]:
                        xbmc.log(f"Received HTTP {status_code}. Retrying after {backoff:.1f} seconds...", xbmc.LOGWARNING)
                        time.sleep(backoff)  # Apply backoff delay
                        backoff *= 1.5  # Increase backoff by a factor of 1.5
                        total_attempts += 1
                        continue  # Retry the same title
                    elif status_code == 404:
                        xbmc.log(f"Title '{title}' not found (HTTP 404). Skipping to next title.", xbmc.LOGDEBUG)
                        total_attempts += 1
                        break  # Break to try the next title
                    else:
                        xbmc.log(f"HTTP error {status_code} occurred while fetching IMDb URL: {http_err}", xbmc.LOGERROR)
                        total_attempts += 1
                        break  # Break to try the next title

                except requests.exceptions.RequestException as req_err:
                    xbmc.log(f"Request error occurred while fetching IMDb URL: {req_err}", xbmc.LOGERROR)
                    total_attempts += 1
                    break  # Break to try the next title

                except (ValueError, KeyError) as err:
                    xbmc.log(f"Error processing OMDb API response: {err}", xbmc.LOGERROR)
                    total_attempts += 1
                    break  # Break to try the next title

                total_attempts += 1  # Increment total attempts after each try

            # Reset backoff delay when moving to the next title
            backoff = initial_backoff

        # If all attempts are exhausted
        xbmc.log(f"Max attempts reached. IMDb URL not fetched for '{original_title}' or any alternative titles", xbmc.LOGWARNING)
        return None


    def _generate_alternative_titles(self, title: str) -> List[str]:
        """Generate alternative titles by applying common spelling variations."""
        alternative_titles = []
        for word, replacement in self.WORD_VARIATIONS.items():
            if word in title:
                new_title = title.replace(word, replacement)
                if new_title != title and new_title not in alternative_titles:
                    alternative_titles.append(new_title)
        return alternative_titles

    def _is_unauthorized_request(self, response) -> bool:
        """Check if the response indicates a 401 Unauthorized error."""
        if response is None:
            return False
        return response.status_code == 401

    def _make_omdb_request(self, params: dict) -> Optional[dict]:
        """Make a request to the OMDb API and handle the response."""
        data_url = "http://www.omdbapi.com/"
        try:
            response = requests.get(data_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as req_err:
            xbmc.log(f"Request error occurred while fetching IMDb URL: {req_err}", xbmc.LOGERROR)
            return None

    def _normalize_title(self, title: str) -> str:
        """Normalize the title by removing 'and' and '&'."""
        title = re.sub(r'\b(and|&)\b', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s+', ' ', title).strip()
        return title
    

    WORD_VARIATIONS = {
        # Spelling variations (British vs. American)
        "color": "colour",
        "colour": "color",
        "theater": "theatre",
        "theatre": "theater",
        "honor": "honour",
        "honour": "honor",
        "realize": "realise",
        "realise": "realize",
        "organize": "organise",
        "organise": "organize",
        "analyze": "analyse",
        "analyse": "analyze",
        "apologize": "apologise",
        "apologise": "apologize",
        "center": "centre",
        "centre": "center",
        "meter": "metre",
        "metre": "meter",
        "defense": "defence",
        "defence": "defense",
        "offense": "offence",
        "offence": "offense",
        "travelling": "traveling",
        "traveling": "travelling",
        "jewelry": "jewellery",
        "jewellery": "jewelry",
        "catalog": "catalogue",
        "catalogue": "catalog",
        "dialog": "dialogue",
        "dialogue": "dialog",
        "practice": "practise",
        "practise": "practice",  # "Practise" (verb) vs. "practice" (noun) in British English
        "license": "licence",
        "licence": "license",  # Same distinction as practice/practise
        "check": "cheque",
        "cheque": "check",

        # Regional terminology differences
        "elevator": "lift",
        "lift": "elevator",
        "truck": "lorry",
        "lorry": "truck",
        "apartment": "flat",
        "flat": "apartment",
        "cookie": "biscuit",
        "biscuit": "cookie",
        "soccer": "football",
        "football": "soccer",  # Could depend on context; may need more handling
        "fall": "autumn",
        "autumn": "fall",
        "diaper": "nappy",
        "nappy": "diaper",
        "flashlight": "torch",
        "torch": "flashlight",
        "garbage": "rubbish",
        "rubbish": "garbage",
        "sneakers": "trainers",
        "trainers": "sneakers",
        "vacation": "holiday",
        "holiday": "vacation",
        "hood": "bonnet",  # As in a car hood
        "bonnet": "hood",
        "trunk": "boot",  # As in a car trunk
        "boot": "trunk",
        "mail": "post",
        "post": "mail",
        "zip code": "postcode",
        "postcode": "zip code",
    }