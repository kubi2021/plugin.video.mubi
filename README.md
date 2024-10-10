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

## Development Setup

Follow these steps to set up your Kodi development environment so that changes to the plugin code are automatically reflected without needing to reinstall or copy files:

### 1. Install the Plugin from Zip

1. First, package your plugin into a `.zip` file.
2. Open Kodi and go to **Add-ons** > **Install from zip file**.
3. Select your `.zip` file and install the plugin. This registers the plugin in Kodi.

### 2. Shutdown Kodi

Once the plugin is installed, completely close Kodi.

### 3. Remove the Installed Plugin Folder

After closing Kodi, navigate to Kodi's **addons** directory, and remove the installed plugin folder. This is typically located at:

```bash
~/Library/Application Support/Kodi/addons/plugin.video.mubi
```

Use the following command to remove the folder:

```bash
rm -rf ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

### 4. Create a Symlink to Your Development Folder

Now, create a symbolic link (symlink) from your development folder to the Kodi addons directory. Replace `<path_to_your_dev_folder>` with the actual path to your local development folder:

```bash
ln -s <path_to_your_dev_folder> ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

For example:

```bash
ln -s /Users/youruser/Documents/GitHub/plugin.video.mubi ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

### 5. Restart Kodi

Once the symlink is created, restart Kodi. The plugin will now load directly from your development folder, and any changes made will be automatically reflected in Kodi without needing to reinstall the plugin.