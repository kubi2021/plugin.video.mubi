import os
from pathlib import Path
import xbmc
import xml.etree.ElementTree as ET
import requests
from requests.exceptions import RequestException


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
        film_file_name = f"{self.title} ({self.metadata.year}).strm"
        film_strm_file = film_path / film_file_name
        kodi_movie_url = f"{base_url}?action=play_ext&web_url={self.web_url}"

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
            nfo_tree = self._get_nfo_tree(self.metadata, self.categories, kodi_trailer_url)
            with open(nfo_file, "wb") as f:
                f.write(nfo_tree)
                if omdb_api_key:
                    imdb_url = self._get_imdb_url(self.metadata.originaltitle, self.title, self.metadata.year, omdb_api_key)
                    f.write(imdb_url.encode("utf-8"))
        except (OSError, ValueError) as error:
            xbmc.log(f"Error while creating NFO file for {self.title}: {error}", xbmc.LOGERROR)

    def _get_nfo_tree(self, metadata, categories: list, kodi_trailer_url: str) -> bytes:
        """Generate the NFO XML tree structure."""
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

        return ET.tostring(movie)

    def _get_imdb_url(self, original_title: str, english_title: str, year: str, omdb_api_key: str) -> str:
        """Fetch the IMDb URL using the OMDb API."""
        data_url = "http://www.omdbapi.com/"
        params = {"apikey": omdb_api_key, "t": original_title, "type": "movie", "y": year}

        try:
            response = requests.get(data_url, params=params, timeout=10)
            response.raise_for_status()  # Raise error if the request failed
            data = response.json()

            if "imdbID" in data:
                return f"https://www.imdb.com/title/{data['imdbID']}/"

            # Try English title if original title fails
            params["t"] = english_title
            response = requests.get(data_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "imdbID" in data:
                return f"https://www.imdb.com/title/{data['imdbID']}/"

        except (RequestException, KeyError) as error:
            xbmc.log(f"Error fetching IMDb URL for {self.title}: {error}", xbmc.LOGERROR)

        return ""
