# MUBI Addon for Kodi

## What it is
Plugin to load MUBI Films Of The Day within Kodi.

The code was taken from user [Jamieu](https://github.com/jamieu/plugin.video.mubi). It was not working with Kodi 19, so I had to make the following changes:

- Adapted to Python 3
- Using Mubi API V2
- Removed dependency on XMBCSwift
- Rewrote the browsing interface using native Kodi libraries

What works:

- Fetching the 30 MUBI Films Of The Day, including the metadata
- (Tested on MacOS only) open the movie in your external browser to player

What doesn't work (yet):

- Fetching all playable Mubi movies in Kodi
- Playing the movie within Kodi (DRM issues to solve)


## Notes

## Installation

1. Download this repo
2. Install from Zip
