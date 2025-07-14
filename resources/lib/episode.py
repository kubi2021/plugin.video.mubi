import os
from pathlib import Path
import xbmc
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
import requests
from requests.exceptions import RequestException
import json
import time
import re
from typing import Optional, List
from urllib.parse import urlencode





class Episode:
    def __init__(self, mubi_id: str, season: str, episode_number: str, series_title: str, title: str, artwork: str, web_url: str, metadata):
        # Validate required fields
        if not mubi_id or not title or not metadata:
            raise ValueError("Episode must have a mubi_id, title, and metadata")

        # Validate and sanitize mubi_id (should be alphanumeric)
        if not isinstance(mubi_id, str) or not mubi_id.strip():
            raise ValueError("mubi_id must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9_-]+$', mubi_id):
            raise ValueError("mubi_id contains invalid characters")

        # Validate season and episode numbers
        if not isinstance(season, (int, str)) or not str(season).isdigit():
            raise ValueError("Season must be a valid number")
        if not isinstance(episode_number, (int, str)) or not str(episode_number).isdigit():
            raise ValueError("Episode number must be a valid number")

        season_int = int(season)
        episode_int = int(episode_number)

        # Validate ranges to prevent path traversal and ensure reasonable values
        if not (1 <= season_int <= 999):
            raise ValueError("Season must be between 1 and 999")
        if not (1 <= episode_int <= 9999):
            raise ValueError("Episode number must be between 1 and 9999")

        # Validate series_title and title for basic safety
        if not isinstance(series_title, str) or not series_title.strip():
            raise ValueError("series_title must be a non-empty string")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")

        # Validate web_url format if provided
        if web_url and not isinstance(web_url, str):
            raise ValueError("web_url must be a string")
        if web_url and not (web_url.startswith('http://') or web_url.startswith('https://')):
            xbmc.log(f"Warning: web_url does not appear to be a valid URL: {web_url}", xbmc.LOGWARNING)

        # Store validated values
        self.mubi_id = mubi_id.strip()
        self.season = season_int
        self.episode_number = episode_int
        self.series_title = series_title.strip()
        self.title = title.strip()
        self.artwork = artwork.strip() if artwork else ""
        self.web_url = web_url.strip() if web_url else ""
        self.metadata = metadata

    def __eq__(self, other):
        if not isinstance(other, Episode):
            return False
        return self.mubi_id == other.mubi_id

    def __hash__(self):
        return hash(self.mubi_id)


    def _sanitize_filename(self, filename: str, replacement: str = " ") -> str:
        """
        Sanitize a filename by removing or replacing characters that are unsafe for file names
        and ensuring compatibility across multiple operating systems.
        
        :param filename: The original file name.
        :param replacement: Character to replace invalid characters with.
        :return: A sanitized file name.
        """
        # Replace reserved characters
        sanitized = re.sub(r'[<>:"/\\|?*^%$&\'{}@!]', replacement, filename)

        # Collapse multiple consecutive spaces (including replacement spaces) into a single space
        sanitized = re.sub(r' +', ' ', sanitized)

        # Handle reserved Windows names (e.g., CON, PRN, AUX, NUL, COM1, LPT1, etc.)
        reserved_names = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", 
            "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", 
            "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        if sanitized.upper() in reserved_names:
            sanitized = f"{sanitized}_{replacement}"  # Add suffix to avoid reserved name conflict

        # Strip trailing periods and spaces
        sanitized = sanitized.rstrip(". ")

        # Enforce length limit (255 characters for most filesystems)
        max_length = 255
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized.strip()


    def get_sanitized_folder_name(self) -> str:
        """
        Generate a consistent, sanitized folder name for the serie, using the episode's series_title attribute.

        :return: A sanitized folder name in the format "Title".
        """
        # Check for path traversal in the original series title
        # Look for actual path traversal patterns, not just any occurrence of '..'
        if '../' in self.series_title or '..\\' in self.series_title or self.series_title.startswith('../') or self.series_title.startswith('..\\') or self.series_title.endswith('/..') or self.series_title.endswith('\\..') or self.series_title == '..':
            raise ValueError(f"Invalid characters in folder name - potential path traversal attempt: '{self.series_title}'")

        sanitized = self._sanitize_filename(f"{self.series_title}")

        # Ensure the sanitized name is not empty
        if not sanitized or sanitized.isspace():
            raise ValueError(f"Folder name cannot be empty after sanitization: original='{self.series_title}', sanitized='{sanitized}'")

        return sanitized


    def create_strm_file(self, serie_path: Path, base_url: str):
        """Create the .strm file for the episode."""
        from urllib.parse import urlencode

        # Use sanitized folder name for consistent file naming
        serie_folder_name = self.get_sanitized_folder_name()
        strm_file_name = f"{serie_folder_name} S{self.season:02d}E{self.episode_number:02d}.strm"
        strm_file = serie_path / strm_file_name

        # Build the query parameters
        query_params = {
            'action': 'play_mubi_video',
            'film_id': self.mubi_id,
            'web_url': self.web_url
        }
        encoded_params = urlencode(query_params)
        kodi_movie_url = f"{base_url}?{encoded_params}"

        try:
            with open(strm_file, "w") as f:
                f.write(kodi_movie_url)
        except OSError as error:
            xbmc.log(f"Error while creating STRM file for {self.title}: {error}", xbmc.LOGERROR)

    def create_nfo_file(self, serie_path: Path, base_url: str, omdb_api_key: str):
        """Create the .nfo file for the episode."""
        # Use sanitized folder name for consistent file naming
        serie_folder_name = self.get_sanitized_folder_name()
        nfo_file_name = f"{serie_folder_name} S{self.season:02d}E{self.episode_number:02d}.nfo"
        nfo_file = serie_path / nfo_file_name
        kodi_trailer_url = ""

        try:
            imdb_url = ""
            if omdb_api_key:
                time.sleep(2)
                imdb_url = self._get_imdb_url(self.metadata.originaltitle, self.title, self.metadata.year, omdb_api_key)

                if imdb_url is None:
                    xbmc.log(f"Skipping creation of NFO file for '{self.title}' due to repeated API errors.", xbmc.LOGWARNING)
                    return

            nfo_tree = self._get_nfo_tree(self.metadata, kodi_trailer_url, imdb_url)
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



    def _get_nfo_tree(self, metadata, kodi_trailer_url: str, imdb_url: str) -> bytes:
        """Generate the NFO XML tree structure, including IMDb URL if available."""
        if not metadata.title:
            raise ValueError("Metadata must contain a title")

        episodedetails = ET.Element("episodedetails")

        # Use XML escaping to prevent XML injection
        ET.SubElement(episodedetails, "title").text = saxutils.escape(str(metadata.title))
        ET.SubElement(episodedetails, "originaltitle").text = saxutils.escape(str(metadata.originaltitle))

        ratings = ET.SubElement(episodedetails, "ratings")
        rating = ET.SubElement(ratings, "rating")
        rating.set("name", "MUBI")
        ET.SubElement(rating, "value").text = saxutils.escape(str(metadata.rating))
        ET.SubElement(episodedetails, "runtime").text = saxutils.escape(str(metadata.duration))

        if metadata.country:
            ET.SubElement(episodedetails, "country").text = saxutils.escape(str(metadata.country[0]))

        for genre in metadata.genre:
            ET.SubElement(episodedetails, "genre").text = saxutils.escape(str(genre))

        for director in metadata.director:
            ET.SubElement(episodedetails, "director").text = saxutils.escape(str(director))

        ET.SubElement(episodedetails, "year").text = saxutils.escape(str(metadata.year))
        ET.SubElement(episodedetails, "trailer").text = saxutils.escape(str(kodi_trailer_url))
        thumb = ET.SubElement(episodedetails, "thumb")
        thumb.set("aspect", "landscape")
        thumb.text = saxutils.escape(str(metadata.image))

        ET.SubElement(episodedetails, "dateadded").text = saxutils.escape(str(metadata.dateadded))

        # Add IMDb URL if available (validate URL format)
        if imdb_url:
            # Basic URL validation for IMDb URLs
            if isinstance(imdb_url, str) and (imdb_url.startswith('http://') or imdb_url.startswith('https://')):
                ET.SubElement(episodedetails, "imdbid").text = saxutils.escape(imdb_url)
            else:
                xbmc.log(f"Invalid IMDb URL format: {imdb_url}", xbmc.LOGWARNING)

        return ET.tostring(episodedetails)





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

        # Normalize the English title by removing 'and' and '&' and everything after first colon
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

        # Validate and sanitize parameters
        safe_params = {}
        for key, value in params.items():
            # Only allow expected parameter names
            if key not in ['t', 'y', 'apikey', 'type']:
                xbmc.log(f"Unexpected OMDb parameter: {key}", xbmc.LOGWARNING)
                continue

            # Sanitize parameter values
            if isinstance(value, str):
                # Remove potentially dangerous characters
                sanitized_value = re.sub(r'[<>&"\']', '', str(value))
                safe_params[key] = sanitized_value[:100]  # Limit length
            else:
                safe_params[key] = str(value)[:100]

        try:
            response = requests.get(data_url, params=safe_params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as req_err:
            xbmc.log(f"Request error occurred while fetching IMDb URL: {req_err}", xbmc.LOGERROR)
            return None

    def _normalize_title(self, title: str) -> str:
        """Normalize the title by removing 'and' and '&' and everything behind the first colon."""
        title = re.sub(r'\b(and|&)\b', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s+', ' ', title).strip()
        title = title.split(':')[0]
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
