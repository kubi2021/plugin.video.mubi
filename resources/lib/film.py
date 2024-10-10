# film.py

import os
from pathlib import Path
import xbmc
import xml.etree.ElementTree as ET
import requests


class Film:
    def __init__(self, mubi_id, title, artwork, web_url, category, metadata):
        self.mubi_id = mubi_id
        self.title = title
        self.artwork = artwork
        self.web_url = web_url
        self.categories = [category]  # Store categories as a list to handle multiple categories
        self.metadata = metadata

    def add_category(self, category):
        """Add a category to the film, ensuring no duplicates."""
        if category not in self.categories:
            self.categories.append(category)

    def create_strm_file(self, film_path, base_url):
        """Create the .strm file for the film."""
        film_file_name = f"{self.title} ({self.metadata.year}).strm"
        film_strm_file = film_path / film_file_name
        kodi_movie_url = f"{base_url}?action=play_ext&web_url={self.web_url}"

        try:
            with open(film_strm_file, "w") as f:
                f.write(kodi_movie_url)
        except OSError as error:
            xbmc.log(f"Error while creating STRM file: {error}", 2)

    def create_nfo_file(self, film_path, base_url, omdb_api_key):
        """Create the .nfo file for the film."""
        nfo_file_name = f"{self.title} ({self.metadata.year}).nfo"
        nfo_file = film_path / nfo_file_name
        kodi_trailer_url = f"{base_url}?action=play_trailer&url={self.metadata.trailer}"

        nfo_tree = self._get_nfo_tree(self.metadata, self.categories, kodi_trailer_url)

        try:
            with open(nfo_file, "wb") as f:
                f.write(nfo_tree)
                if omdb_api_key:
                    imdb_url = self._get_imdb_url(self.metadata.originaltitle, self.title, self.metadata.year, omdb_api_key)
                    f.write(imdb_url.encode("utf-8"))
        except OSError as error:
            xbmc.log(f"Error while creating NFO file: {error}", 2)

    def _get_nfo_tree(self, metadata, categories, kodi_trailer_url):
        """Generate the NFO XML tree structure."""
        movie = ET.Element("movie")

        title = ET.SubElement(movie, "title")
        title.text = metadata.title

        originaltitle = ET.SubElement(movie, "originaltitle")
        originaltitle.text = metadata.originaltitle

        ratings = ET.SubElement(movie, "ratings")
        rating = ET.SubElement(ratings, "rating")
        rating.set("name", "MUBI")

        value = ET.SubElement(rating, "value")
        value.text = str(metadata.rating)
        votes = ET.SubElement(rating, "votes")
        votes.text = str(metadata.votes)

        plot = ET.SubElement(movie, "plot")
        plot.text = metadata.plot

        outline = ET.SubElement(movie, "outline")
        outline.text = metadata.plotoutline

        runtime = ET.SubElement(movie, "runtime")
        runtime.text = str(metadata.duration)

        country = ET.SubElement(movie, "country")
        if metadata.country:
            country.text = metadata.country[0]

        for genre in metadata.genre:
            genre_element = ET.SubElement(movie, "genre")
            genre_element.text = genre

        for director in metadata.director:
            director_element = ET.SubElement(movie, "director")
            director_element.text = director

        year = ET.SubElement(movie, "year")
        year.text = str(metadata.year)

        trailer = ET.SubElement(movie, "trailer")
        trailer.text = kodi_trailer_url

        thumb = ET.SubElement(movie, "thumb")
        thumb.set("aspect", "landscape")
        thumb.text = metadata.image

        for category in categories:
            tag = ET.SubElement(movie, "tag")
            tag.text = category

        dateadded = ET.SubElement(movie, "dateadded")
        dateadded.text = str(metadata.dateadded)

        return ET.tostring(movie)

    def _get_imdb_url(self, original_title, english_title, year, omdb_api_key):
        """Fetch the IMDb URL using the OMDb API."""
        data_URL = "http://www.omdbapi.com/"
        params = {"apikey": omdb_api_key, "t": original_title, "type": "movie", "y": year}
        response = requests.get(data_URL, params=params).json()

        if "imdbID" in response:
            imdb_url = f"https://www.imdb.com/title/{response['imdbID']}/"
            return imdb_url

        # Try English title if original title fails
        params["t"] = english_title
        response = requests.get(data_URL, params=params).json()

        if "imdbID" in response:
            return f"https://www.imdb.com/title/{response['imdbID']}/"

        return ""


