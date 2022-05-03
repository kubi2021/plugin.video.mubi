# MUBI Addon for Kodi

## What it is
Plugin to load MUBI Films within Kodi.

The code was taken from user [Jamieu](https://github.com/jamieu/plugin.video.mubi). It was not working with Kodi 19, so I had to make the following changes:

- Adapted to Python 3
- Using Mubi API V2
- Removed dependency on XMBCSwift
- Rewrote the browsing interface using native Kodi libraries

Features:

- Fetches the all movies available on Kodi, including all meta data from Mubi
- Compatible with the Kodi movie library
- Finds the corresponding movie in IMDB so that Kodi scraper can fetch the meta data
- Play Mubi trailer from within Kodi
- (Tested on MacOS only) open the movie in your external browser to player

What doesn't work (yet):

- Playing the movie within Kodi (DRM issues to solve)


## Notes

## Installation

1. Download this repo
2. From the Kodi interface, install the add on from Zip
3. In the add-on config, enter your OMDb API key (you can get it [here](http://www.omdbapi.com/apikey.aspx)). It's thanks to this key that the add-on will identify the movie on IMDb, and that later on the kodi scraper can find the corresponding artowrks, etc.

## First run & populating the library
1. launch the Mubi add on
2. Select to sync Mubi locally
3. In settings > media > library, add a video source with the path: special://userdata/addon_data/plugin.video.mubi
4. In the next window (Set Content), after adding the path, set that the directory contains Movies
5. Choose your favorite information provider (I'm using the universal movie scraper)
6. In the settings of the scraper, uncheck feching the trailer as the current add-on is providing the trailer directly from Mubi. I also check to fetch all fanarts.
7. Back to the "Set content" window, check "movies are in separate folders", leave the other toggles as they are.

## Next runs

Whenever you want to update the local database, follow step 1 and 2 above. Then update the library to get the last meta data.
