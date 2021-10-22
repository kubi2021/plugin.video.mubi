# -*- coding: utf-8 -*-
# In order to manipulate files and folders
import os
from pathlib import Path
import xbmc
import xml.etree.ElementTree as ET
import requests


def write_files(plugin_userdata_path, film):

    # create plugin folder
    if not os.path.exists(plugin_userdata_path):
        os.makedirs(plugin_userdata_path)

    ## Create the strm files in special://userdata/addon_data/plugin.video.mubi
    clean_title = (film['title']).replace("/"," ")


    ## Create the folder
    film_folder_name = Path(clean_title + ' (' + str(film['metadata'].year) + ')')
    film_path = plugin_userdata_path / film_folder_name
    try:
        os.mkdir(film_path)
    except OSError as error:
        xbmc.log("Error while creating the library: %s" % error, 2)

    ## Create the STRM file
    film_file_name = clean_title + ' (' + str(film['metadata'].year) + ').strm'
    film_file = film_path / film_file_name
    try:
        f = open(film_file, "w")
        f.write(film['url'])
        f.close()
    except OSError as error:
        xbmc.log("Error while creating the file: %s" % error, 2)

    ## Download the trailer_url
    trailer_file_name = clean_title + ' (' + str(film['metadata'].year) + ').avi'
    trailer_file = film_path / trailer_file_name
    try:
        url = film['metadata'].trailer
        r = requests.get(url, allow_redirects=True)
        open(trailer_file, 'wb').write(r.content)
    except OSError as error:
        xbmc.log("Error while creating the file: %s" % error, 2)

    ## Create the NFO file
    nfo_file_name = clean_title + ' (' + str(film['metadata'].year) + ').nfo'
    nfo_file = film_path / nfo_file_name
    nfo_tree = get_nfo_tree(film['metadata'], film['categories'], trailer_file)
    try:
        f = open(nfo_file, "wb")
        f.write(nfo_tree)
        f.close()
    except OSError as error:
        xbmc.log("Error while creating the file: %s" % error, 2)

def merge_duplicates(films):

    # the output will be a list of movies where each movie appears only once and categories are merged
    movies_and_categories = []

    for film in films:

        # For each film, search a list if the Mubi id exist
        idx = next((i for i, item in enumerate(movies_and_categories) if item["mubi_id"] == film['film'].mubi_id), None)

        if idx:
            # if it exists add the new category to the movie
            movies_and_categories[idx]["categories"].append(film['film'].category)
        else:
            # If it doesn't exist, add an item to the list with mubi id and category as list
            movie_and_categorie = {
                'mubi_id' : film['film'].mubi_id,
                'title' : film['film'].title,
                'artwork': film['film'].artwork,
                'web_url': film['film'].web_url,
                'metadata': film['film'].metadata,
                'url': film['url'],
                'categories' : [film['film'].category]
            }
            movies_and_categories.append(movie_and_categorie)

    return movies_and_categories


def get_nfo_tree(metadata, categories, trailer_path):

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
    rating.set('default', 'True')
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

    for regisseur in metadata.director:
        director = ET.SubElement(movie, 'director')
        director.text = str(regisseur['name'])

    year = ET.SubElement(movie, 'year')
    year.text = str(metadata.year)

    trailer = ET.SubElement(movie, 'trailer')
    trailer.text = str(trailer_path)

    thumb = ET.SubElement(movie, 'thumb')
    thumb.set('aspect', 'poster')
    thumb.text = metadata.image

    for category in categories:
        tag = ET.SubElement(movie, 'tag')
        tag.text = category

    dateadded = ET.SubElement(movie, 'dateadded')
    dateadded.text = str(metadata.dateadded)

    return ET.tostring(movie)
