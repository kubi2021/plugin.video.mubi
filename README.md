# MUBI Addon for Kodi

## What it is
Plugin to load MUBI Films within Kodi.

The code was taken from user [Jamieu](https://github.com/jamieu/plugin.video.mubi). It was not working with Kodi 19, so I had to make the following changes:

- Adapted to Python 3
- Using Mubi API V2
- Removed dependency on XMBCSwift
- Rewrote the browsing interface using native Kodi libraries

Features:

- Fetches the all available movies
- Creates local NFO files so that the movies can be added to the Kodi library, additional data can be fetched using Kodi scrappers. After having run the "Sync all Mubi films locally", add the following path to your Kodi movies library "special://userdata/addon_data/plugin.video.mubi" and update the library.
- Play Mubi trailer from within Kodi
- (Tested on MacOS only) open the movie in your external browser to player



What doesn't work (yet):

- Playing the movie within Kodi (DRM issues to solve)


## Notes

## Installation

1. Download this repo
2. Install from Zip
