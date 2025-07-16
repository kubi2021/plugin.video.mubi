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
    def __init__(self, mubi_id: str, title: str, artwork: str, web_url: str, category: str, metadata):
        if not mubi_id or not title or not metadata:
            raise ValueError("Film must have a mubi_id, title, and metadata")
        
        self.mubi_id = mubi_id
        self.title = title
        self.artwork = artwork
        self.web_url = web_url
        self.categories = [category]  # Store categories as a list to handle multiple categories
        self.metadata = metadata

    def __eq__(self, other):
        if not isinstance(other, Film):
            return False
        return self.mubi_id == other.mubi_id

    def __hash__(self):
        return hash(self.mubi_id)


    def add_category(self, category: str):
        """Add a category to the film, ensuring no duplicates."""
        if category and category not in self.categories:
            self.categories.append(category)

    def _sanitize_filename(self, filename: str, replacement: str = " ") -> str:
        """
        Sanitize a filename by removing or replacing characters that are unsafe for file names
        and ensuring compatibility across multiple operating systems.
        
        :param filename: The original file name.
        :param replacement: Character to replace invalid characters with.
        :return: A sanitized file name.
        """
        # Replace reserved characters and command injection characters
        # Note: Parentheses () and apostrophes ' are safe in filenames and commonly used
        sanitized = re.sub(r'[<>:"/\\|?*^%$&{}@!;`~#]', replacement, filename)

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
        Generate a consistent, sanitized folder name for the film, using the title and year.

        :return: A sanitized folder name in the format "Title (Year)".
        """
        # First sanitize the title to remove problematic characters including trailing periods
        sanitized_title = self._sanitize_filename(self.title)
        year = self.metadata.year if self.metadata.year else "Unknown"
        return f"{sanitized_title} ({year})"


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

    def create_nfo_file(self, film_path: Path, base_url: str, omdb_api_key: str):
        """Create the .nfo file for the film."""
        # Use sanitized folder name for consistent file naming
        film_folder_name = self.get_sanitized_folder_name()
        nfo_file_name = f"{film_folder_name}.nfo"
        nfo_file = film_path / nfo_file_name
        kodi_trailer_url = f"{base_url}?action=play_trailer&url={self.metadata.trailer}"

        try:
            imdb_url = ""
            if omdb_api_key:
                time.sleep(2)
                imdb_url = self._get_imdb_url(self.metadata.originaltitle, self.title, self.metadata.year, omdb_api_key)

                if imdb_url is None:
                    xbmc.log(f"Creating NFO file for '{self.title}' without IMDb URL due to API errors.", xbmc.LOGWARNING)
                    # Still create NFO file without IMDb URL rather than failing completely
                    imdb_url = ""

            nfo_tree = self._get_nfo_tree(self.metadata, self.categories, kodi_trailer_url, imdb_url)
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



    def _get_nfo_tree(self, metadata, categories: list, kodi_trailer_url: str, imdb_url: str) -> bytes:
        """Generate the NFO XML tree structure, including IMDb URL if available."""
        if not metadata.title:
            raise ValueError("Metadata must contain a title")

        movie = ET.Element("movie")

        ET.SubElement(movie, "title").text = metadata.title
        ET.SubElement(movie, "originaltitle").text = metadata.originaltitle

        ratings = ET.SubElement(movie, "ratings")
        rating = ET.SubElement(ratings, "rating")
        rating.set("name", "MUBI")
        ET.SubElement(rating, "value").text = str(metadata.rating)
        ET.SubElement(rating, "votes").text = str(metadata.votes)

        ET.SubElement(movie, "plot").text = metadata.plot
        ET.SubElement(movie, "outline").text = metadata.plotoutline
        ET.SubElement(movie, "runtime").text = str(metadata.duration)

        if metadata.country:
            ET.SubElement(movie, "country").text = metadata.country[0]

        for genre in metadata.genre:
            ET.SubElement(movie, "genre").text = genre

        for director in metadata.director:
            ET.SubElement(movie, "director").text = director

        ET.SubElement(movie, "year").text = str(metadata.year)
        ET.SubElement(movie, "trailer").text = kodi_trailer_url
        thumb = ET.SubElement(movie, "thumb")
        thumb.set("aspect", "landscape")
        thumb.text = metadata.image

        for category in categories:
            ET.SubElement(movie, "tag").text = category

        ET.SubElement(movie, "dateadded").text = str(metadata.dateadded)

        # Add IMDb URL if available
        if imdb_url:
            ET.SubElement(movie, "imdbid").text = imdb_url

        return ET.tostring(movie)





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