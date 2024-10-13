import os
from pathlib import Path
import xbmc
import xml.etree.ElementTree as ET
import requests
from requests.exceptions import RequestException
import json
import time
import re


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

    def add_category(self, category: str):
        """Add a category to the film, ensuring no duplicates."""
        if category and category not in self.categories:
            self.categories.append(category)

    def create_strm_file(self, film_path: Path, base_url: str):
        """Create the .strm file for the film."""
        from urllib.parse import urlencode

        film_file_name = f"{self.title} ({self.metadata.year}).strm"
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
        nfo_file_name = f"{self.title} ({self.metadata.year}).nfo"
        nfo_file = film_path / nfo_file_name
        kodi_trailer_url = f"{base_url}?action=play_trailer&url={self.metadata.trailer}"

        try:
            # Fetch IMDb URL if the API key is provided
            imdb_url = ""
            if omdb_api_key:
                imdb_url = self._get_imdb_url(self.metadata.originaltitle, self.title, self.metadata.year, omdb_api_key)

            # Generate the NFO XML with the IMDb URL included
            nfo_tree = self._get_nfo_tree(self.metadata, self.categories, kodi_trailer_url, imdb_url)
            
            # Write the XML to file
            with open(nfo_file, "wb") as f:
                f.write(nfo_tree)
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



    def _get_imdb_url(self, original_title: str, english_title: str, year: str, omdb_api_key: str) -> str:
        """Fetch the IMDb URL using the OMDb API with retry logic for 401 errors and title normalization."""
        data_url = "http://www.omdbapi.com/"
        max_retries = 5  # Maximum number of retries
        backoff_factor = 1  # Start with a 1-second delay and double with each retry

        # Normalize the titles (remove or replace 'and'/'&')
        original_title_cleaned = self._normalize_title(original_title)
        english_title_cleaned = self._normalize_title(english_title)

        # First, we attempt with the original title
        params = {"apikey": omdb_api_key, "t": original_title, "type": "movie", "y": year}
        use_original_title = True  # Start by trying the original title
        cleaned_title_attempted = False  # Track if the cleaned title has been attempted

        for attempt in range(1, max_retries + 1):
            try:
                # Log the retry attempt
                title_in_use = original_title if use_original_title else english_title
                if cleaned_title_attempted:
                    title_in_use = original_title_cleaned if use_original_title else english_title_cleaned

                xbmc.log(f"Attempt {attempt} to fetch IMDb URL for '{title_in_use}' ({year})", xbmc.LOGDEBUG)
                
                # Make the request to OMDb API
                response = requests.get(data_url, params=params, timeout=10)
                
                # Check if the status code is 401 (Unauthorized)
                if response.status_code == 401:
                    xbmc.log(f"Received 401 Unauthorized. Retrying after {backoff_factor} seconds...", xbmc.LOGWARNING)
                    # Wait before retrying
                    time.sleep(backoff_factor)
                    # Increase the backoff delay
                    backoff_factor *= 2
                    continue  # Retry the loop

                # Raise an exception for any other HTTP errors
                response.raise_for_status()

                data = response.json()
                xbmc.log(f"OMDb API response for title '{title_in_use}': {json.dumps(data, indent=4)}", xbmc.LOGDEBUG)

                # Check if IMDb ID is found
                if "imdbID" in data:
                    return f"https://www.imdb.com/title/{data['imdbID']}/"

                # Try the English title if we started with the original title
                if use_original_title:
                    xbmc.log(f"IMDb ID not found for '{original_title}'. Trying '{english_title}'", xbmc.LOGDEBUG)
                    params["t"] = english_title
                    use_original_title = False  # Switch to English title
                # If we've already tried both titles, try the cleaned titles
                elif not cleaned_title_attempted:
                    xbmc.log(f"Attempting to clean titles. Trying '{original_title_cleaned}' and '{english_title_cleaned}'", xbmc.LOGDEBUG)
                    params["t"] = original_title_cleaned
                    use_original_title = True  # Retry with the cleaned original title
                    cleaned_title_attempted = True  # Track that we've tried the cleaned title
                else:
                    # If we've tried all variations, log a warning and return an empty string
                    xbmc.log(f"IMDb ID not found for both '{original_title}' and '{english_title}' and cleaned titles", xbmc.LOGWARNING)
                    return ""

            except requests.exceptions.HTTPError as http_err:
                # Log and retry if the error is a 401 (Unauthorized)
                if response.status_code == 401:
                    xbmc.log(f"Received 401 Unauthorized. Retrying after {backoff_factor} seconds...", xbmc.LOGWARNING)
                    time.sleep(backoff_factor)  # Sleep before retrying
                    backoff_factor *= 2  # Increase the backoff delay
                    continue  # Retry the loop
                # For other HTTP errors, log and return
                xbmc.log(f"HTTP error occurred while fetching IMDb URL: {http_err}", xbmc.LOGERROR)
                return ""

            except requests.exceptions.RequestException as req_err:
                # Handle general request exceptions
                xbmc.log(f"Request error occurred while fetching IMDb URL: {req_err}", xbmc.LOGERROR)
                return ""

            except ValueError as val_err:
                # Handle JSON decoding errors or unexpected response formats
                xbmc.log(f"Error decoding OMDb API response: {val_err}", xbmc.LOGERROR)
                return ""

            except KeyError as key_err:
                # Handle missing fields in the response
                xbmc.log(f"Missing expected data in OMDb API response: {key_err}", xbmc.LOGERROR)
                return ""

        # If all retries fail, log a final warning and return an empty string
        xbmc.log(f"Max retries reached. IMDb URL not fetched for '{original_title}' ({year})", xbmc.LOGWARNING)
        return ""


    def _normalize_title(self, title: str) -> str:
        """Normalize the title by replacing/removing common words and symbols."""
        # Replace "and" with "&" and vice versa, then remove them entirely
        title = re.sub(r'\b(and|&)\b', '', title, flags=re.IGNORECASE)
        
        # Remove any extra spaces left behind after replacing
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title