# MUBI Addon for Kodi 🎥🚀

## Why I'm doing this

I really enjoy MUBI and their curated selection of films. However, I find their interface somewhat cluttered, often requiring too many clicks to make a decision. When selecting a film, I prefer to have the key information readily available: duration, genre, and rating. I also value the ability to sort films by rating or recent additions. Thankfully, Kodi offers all of these features.

This project is a personal endeavour I work on in my free time. As I am not a professional developer, updates or changes might take a little longer to implement.

## Features

The goal of this addon is to harness Kodi's excellent browsing and metadata scraping capabilities while using films from MUBI. 🎥 Therefore, the addon creates a small file for each MUBI movie. These files are then treated as standard library items within Kodi, allowing them to be browsed directly from the main interface. 🔍 The metadata can also be enriched using Kodi's library update feature, giving you a seamless experience. 📚

- 🎬 Fetches all movies available on Mubi, including full Mubi ratings and descriptions
- 👍 Compatible with the Kodi movie library
- 🛡️ Finds the corresponding movie on IMDb so Kodi scraper can fetch additional metadata
- 🍿 Play Mubi trailers directly within Kodi
- 📺 Movies are playable directly within Kodi, supporting subtitles and multiple audio streams out of the box using Kodi's features
- 🌐 If the movie can't be played within Kodi, the user is prompted to open it in their browser (tested on macOS only)
- 🈯 Supports display of titles and descriptions in the languages supported by Mubi

## Installation

1. **Download** this repository.
2. From the **Kodi interface**, install the addon from the Zip file.

## First run & Populating the Library

1. 🔑 Get an **OMDb API key** from [here](http://www.omdbapi.com/apikey.aspx). It's free and will be needed to populate the library with rich metadata.
2. ⚙️ In the **add-on settings**, enter your **OMDb API key**. It's important to do this before the first sync of Mubi to Kodi.
3. 🎬 Launch the **Mubi** add-on.
4. 📁 The **Mubi Movies** folder is automatically added to the Kodi video sources by the addon.
5. ⚙️ For the Mubi movies to be properly scraped and displayed in your library, configure the source in **Kodi settings > Media > Video**:
    - 1️⃣ Set the content type to **'Video'**.
    - 2️⃣ In the **Set Content** window, check "**Movies are in separate folders**," and leave the other toggles as they are.
    - 3️⃣ Choose your preferred information provider (e.g., **Universal Movie Scraper**).
    - 4️⃣ In the scraper settings, **uncheck** fetching the trailer (since the current add-on provides trailers directly from Mubi). Optionally, check to fetch all **fanart**.
6. 🔙 Go back to the **Mubi** addon and log in.
7. 🔄 Select the option to **sync Mubi locally**.
8. 🎥 Go to the **Movies** tab in Kodi and **update the library** to see the newly added Mubi movies.

### Next Runs 🚀

Whenever you want to **update** the local database:
1. Run the **sync** process again (as described above).
2. Then update the **Kodi library** to fetch the latest metadata.
3. 🎥 Go to the **Movies** tab in Kodi and **update the library** to see the newly added Mubi movies.

## Changelog

### October 12th 2024

- improved installation by automatically adding the Mubi Video source to Kodi
- better user experience with OMDb API, plugins detects if the API Key is missig and notifies the user before the sync
- improved library management:
    - obsolete movies are removed from the local folder
    - after syncing with Mubi, Kodi library upgrade is automatically triggered

### October 11th 2024

- Added support for playing MUBI movies directly within Kodi 🎥
- Implemented subtitles and multiple audio streams support using Kodi's native features 📺
- Added support for displaying titles and descriptions in the languages supported by MUBI 🈯

### October 10th 2024

MUBI recently updated their API a few months ago, which caused the current addon to stop working. Thanks to [@mtr81](https://github.com/mtr81), I found great inspiration for adapting the addon to MUBI's new V3 API. 🎉

In addition to the API update, I made the following changes:
- 🔄 **Major refactoring** of the backend, making the addon more robust and easier to maintain.
- 🔑 Added the ability to **manage sessions** (login and logout), laying the groundwork for future functionality to play films directly within Kodi (not implemented yet).
- The user can change the country in the settings, allowing them to see movie titles in their favorite language.


### Sometimes in 2021

The code was originally forked from user [Jamieu](https://github.com/jamieu/plugin.video.mubi). It wasn't working with **Kodi 19**, so I made the following changes:

- 🗓 Adapted to Python 3
- 🔄 Using Mubi API V2
- ❌ Removed dependency on XMBCSwift
- 🛠️ Rewrote the browsing interface using native Kodi libraries

## Troubleshooting

### 1. Sync Process is Slow ⏳

If you notice that the sync process is taking longer than expected, this is due to a rate limiting feature we introduced to the Mubi API calls. This rate limiting prevents overloading Mubi's servers and ensures that we comply with their usage policies.

It's normal for the sync process to have occasional pauses, especially noticeable when syncing categories. Please be patient as the process completes.

### 2. Manually Creating the Mubi Source in Kodi 🛠️

If for some reason the Mubi Movies folder isn't automatically added as a video source during the installation process, you can manually create the source in Kodi by following these steps:

1. Navigate to **Settings > Media > Library**.
2. Select **Add Video Source**.
3. Enter the following path for the source:
   ```
   special://userdata/addon_data/plugin.video.mubi
   ```
4. Complete the process, and the Mubi Movies folder will be available in your Kodi library.

After adding the source manually, follow the normal steps to configure it for movies and set up the scraper.

### 3. Cleaning up the Addon 🧹

Before upgrading the addon, it's best to do a full cleanup to avoid potential issues. To clean up the addon:

1. Navigate to **userdata/addon_data/plugin.video.mubi** and remove all the files and folders.
2. It's also suggested to **clean your media library**.
3. Install the new version of the addon.
4. You'll need to **log in again** and perform the **first sync**.

---

Enjoy Mubi on Kodi! 🎥🍿
