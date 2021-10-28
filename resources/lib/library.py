# -*- coding: utf-8 -*-
# In order to manipulate files and folders
import os
from pathlib import Path
import xbmc
import xml.etree.ElementTree as ET
import requests


def write_strm_file(film_strm_file, film, kodi_url):
    try:
        f = open(film_strm_file, "w")
        f.write(kodi_url)
        f.close()
    except OSError as error:
        xbmc.log("Error while creating the file: %s" % error, 2)

def get_imdb_url(title,year, omdbapiKey):

    #Fetch Movie Data
    data_URL = 'http://www.omdbapi.com/?apikey='+omdbapiKey
    params = {
        't':title,
        'type':'movie',
        'y':year
    }
    response = requests.get(data_URL,params=params).json()
    if 'imdbID' in response:
        imdb_url = "https://www.imdb.com/title/" + response['imdbID']
        return imdb_url
    else:
        return ''

def write_nfo_file(nfo_file, film, kodi_trailer_url, omdbapiKey):

    nfo_tree = get_nfo_tree(film['metadata'], film['categories'], kodi_trailer_url)
    try:
        f = open(nfo_file, "wb")
        f.write(nfo_tree)
        if omdbapiKey:
            imdb_url = get_imdb_url(film['metadata'].originaltitle,film['metadata'].year, omdbapiKey ).encode('utf-8')
            f.write(imdb_url)
        f.close()
    except OSError as error:
        xbmc.log("Error while creating the file: %s" % error, 2)

def merge_duplicates(films):

    # the output will be a list of movies where each movie appears only once and categories are merged
    movies_and_categories = []

    for film in films:

        # For each film, search a list if the Mubi id exist
        idx = next((i for i, item in enumerate(movies_and_categories) if item["mubi_id"] == film.mubi_id), None)

        if idx:
            # if it exists add the new category to the movie
            movies_and_categories[idx]["categories"].append(film.category)
        else:
            # If it doesn't exist, add an item to the list with mubi id and category as list
            movie_and_categorie = {
                'mubi_id' : film.mubi_id,
                'title' : film.title,
                'artwork': film.artwork,
                'web_url': film.web_url,
                'metadata': film.metadata,
                'categories' : [film.category]
            }
            movies_and_categories.append(movie_and_categorie)

    return movies_and_categories


def get_nfo_tree(metadata, categories, kodi_trailer_url):

    # create the file structure
    movie = ET.Element('movie')

    title = ET.SubElement(movie, 'title')
    title.text = metadata.title

    originaltitle = ET.SubElement(movie, 'originaltitle')
    originaltitle.text = metadata.originaltitle

    ratings = ET.SubElement(movie, 'ratings')
    rating = ET.SubElement(ratings, 'rating')
    rating.set('name', 'MUBI')
    rating.set('name', 'MUBI')
    # rating.set('default', 'True')
    value = ET.SubElement(rating, 'value')
    value.text = str(metadata.rating)
    votes = ET.SubElement(rating, 'votes')
    votes.text = str(metadata.votes)

    plot = ET.SubElement(movie, 'plot')
    plot.text = metadata.plot

    outline = ET.SubElement(movie, 'outline')
    outline.text = metadata.plotoutline

    runtime = ET.SubElement(movie, 'runtime')
    runtime.text = str(metadata.duration)

    country = ET.SubElement(movie, 'country')
    country.text = metadata.country[0]

    # genre = ET.SubElement(movie, 'genre')
    # genre.text = metadata.genre

    for regisseur in metadata.director:
        director = ET.SubElement(movie, 'director')
        director.text = str(regisseur['name'])

    year = ET.SubElement(movie, 'year')
    year.text = str(metadata.year)

    trailer = ET.SubElement(movie, 'trailer')
    trailer.text = str(kodi_trailer_url)

    thumb = ET.SubElement(movie, 'thumb')
    thumb.set('aspect', 'landscape')
    thumb.text = metadata.image

    for category in categories:
        tag = ET.SubElement(movie, 'tag')
        tag.text = category

    dateadded = ET.SubElement(movie, 'dateadded')
    dateadded.text = str(metadata.dateadded)

    return ET.tostring(movie)
