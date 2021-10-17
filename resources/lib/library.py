# -*- coding: utf-8 -*-
# In order to manipulate files and folders
import os
from pathlib import Path
import xbmc
import xml.etree.ElementTree as ET



def write_strm_files(plugin_userdata_path, films):

    # create plugin folder
    if not os.path.exists(plugin_userdata_path):
        os.makedirs(plugin_userdata_path)

    # 1. work on the file list to merge duplicate
    # 2. rewrite the file name to os friendly


    for film in films:

        ## Create the strm files in special://userdata/addon_data/plugin.video.mubi
        clean_title = (film['film'].title).replace("/"," ")
        film_folder_name = Path(clean_title + ' (' + str(film['film'].metadata.year) + ')')
        film_path = plugin_userdata_path / film_folder_name
        film_file_name = clean_title + ' (' + str(film['film'].metadata.year) + ').strm'
        film_file = film_path / film_file_name

        nfo_file_name = clean_title + ' (' + str(film['film'].metadata.year) + ').nfo'
        nfo_file = film_path / nfo_file_name

        try:
            os.mkdir(film_path)
        except OSError as error:
            xbmc.log("Error while creating the library: %s" % error, 2)

        ## Check with Mubi release -> THE/one the film throws an error because of the slash.
        try:
            f = open(film_file, "w")
            f.write(film['url'])
            f.close()
        except OSError as error:
            xbmc.log("Error while creating the file: %s" % error, 2)

        nfo_tree = get_nfo_tree(film['film'].metadata)

        try:
            f = open(nfo_file, "wb")
            f.write(nfo_tree)
            f.close()
        except OSError as error:
            xbmc.log("Error while creating the file: %s" % error, 2)

def get_nfo_tree(metadata):

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

    director = ET.SubElement(movie, 'director')
    director.text = str(metadata.director[0]['name'])

    year = ET.SubElement(movie, 'year')
    year.text = str(metadata.year)

    trailer = ET.SubElement(movie, 'trailer')
    trailer.text = str(metadata.trailer)

    thumb = ET.SubElement(movie, 'thumb')
    thumb.set('aspect', 'poster')
    thumb.text = metadata.image

    return ET.tostring(movie)
