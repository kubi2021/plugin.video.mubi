# MUBI Addon for Kodi 🎥🚀

## Why I'm doing this

I really enjoy MUBI and their curated selection of films. However, I find their interface somewhat cluttered, often requiring too many clicks to make a decision. When selecting a film, I prefer to have the key information readily available: duration, genre, and rating. I also value the ability to sort films by rating or recent additions. Thankfully, Kodi offers all of these features.

This project is a personal endeavour I work on in my free time. As I am not a professional developer, updates or changes might take a little longer to implement.

## Features
The goal of this addon is to harness Kodi's excellent browsing and metadata scraping capabilities while using films from MUBI. 🎥 Therefore, the addon creates a small file for each MUBI movie. These files are then treated as standard library items within Kodi, allowing them to be browsed directly from the main interface. 🔍 The metadata can also be enriched using Kodi's library update feature, giving you a seamless experience. 📚

- 🎬 Fetches all movies available on Mubi, including **full metadata**
- 👍 Compatible with the **Kodi movie library**
- 🛡️ Finds the corresponding movie on **IMDb** so Kodi scraper can fetch additional metadata
- 🍿 Play Mubi trailers directly within Kodi
- 🎥 (Tested on macOS only) Opens the movie in your **external browser** to play

### What Doesn't Work (Yet)
- 🧐 Playing the movie within Kodi (due to **DRM issues** that need to be resolved)

## Installation 📜

1. **Download** this repository.
2. From the **Kodi interface**, install the addon from the Zip file.
3. In the add-on settings, enter your **OMDb API key** (you can get it [here](http://www.omdbapi.com/apikey.aspx)). This key helps the addon identify the movie on **IMDb**, allowing the Kodi scraper to find additional metadata like artwork, etc.

## First run & Populating the Library 📏

1. Launch the Mubi add-on.
2. Select the option to **sync Mubi locally**.
3. Navigate to **Settings > Media > Library** and add a video source with the path:
    ```
    special://userdata/addon_data/plugin.video.mubi
    ```
4. In the next window (**Set Content**), after adding the path, specify that the directory contains **Movies**.
5. Choose your preferred information provider (e.g., **Universal Movie Scraper**).
6. In the scraper settings, **uncheck** fetching the trailer (since the current add-on provides trailers directly from Mubi). Optionally, check to fetch all **fanart**.
7. In the **Set Content** window, check "**Movies are in separate folders**," and leave the other toggles as they are.

### Next Runs 🚀

Whenever you want to **update** the local database:
1. Run the **sync** process again (as described above).
2. Then update the **Kodi library** to fetch the latest metadata.

## Changelog

### October 2024

MUBI recently updated their API a few months ago, which caused the current addon to stop working. Thanks to this [repository](https://github.com/mtr81/kodi_addons), I found great inspiration for adapting the addon to MUBI's new V3 API. 🎉

In addition to the API update, I made the following changes:
- 🔄 **Major refactoring** of the backend, making the addon more robust and easier to maintain.
- 🔑 Added the ability to **manage sessions** (login and logout), laying the groundwork for future functionality to play films directly within Kodi (not implemented yet).


### Sometimes in 2021

The code was originally forked from user [Jamieu](https://github.com/jamieu/plugin.video.mubi). It wasn't working with **Kodi 19**, so I made the following changes:

- 🗓 Adapted to Python 3
- 🔄 Using Mubi API V2
- ❌ Removed dependency on XMBCSwift
- 🛠️ Rewrote the browsing interface using native Kodi libraries

---



## Development Setup 🛠️

Follow these steps to set up your Kodi development environment, so that changes to the plugin code are automatically reflected without needing to reinstall or copy files:

### 1. Install the Plugin from Zip

1. First, **package your plugin** into a `.zip` file.
2. Open Kodi and navigate to **Add-ons** > **Install from zip file**.
3. Select your `.zip` file and install the plugin. This registers the plugin in Kodi.

### 2. Shutdown Kodi ⏹️

Once the plugin is installed, completely **close Kodi**.

### 3. Remove the Installed Plugin Folder

After closing Kodi, navigate to Kodi's **addons** directory, and **remove** the installed plugin folder. This is typically located at:

```bash
~/Library/Application Support/Kodi/addons/plugin.video.mubi
```

Use the following command to remove the folder:

```bash
rm -rf ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

### 4. Create a Symlink to Your Development Folder 🔗

Now, create a **symbolic link (symlink)** from your development folder to the Kodi addons directory. Replace `<path_to_your_dev_folder>` with the actual path to your local development folder:

```bash
ln -s <path_to_your_dev_folder> ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

For example:

```bash
ln -s /Users/youruser/Documents/GitHub/plugin.video.mubi ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

### 5. Restart Kodi 🔄

Once the symlink is created, **restart Kodi**. The plugin will now load directly from your development folder, and any changes made will be automatically reflected in Kodi without needing to reinstall the plugin.

---

Enjoy Mubi on Kodi! 🎥🍿