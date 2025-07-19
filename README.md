# MUBI Addon for Kodi 🎥🚀

![Tests](https://github.com/YOUR_USERNAME/plugin.video.mubi/workflows/Run%20Tests/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-70%25-yellow)
![GitHub branch protection](https://img.shields.io/badge/branch%20protection-enabled-green)

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
- 🔖 Retrieves and displays your MUBI watchlist within Kodi, allowing quick access to saved films directly from the main interface
- 🗂️ Mubi collections are automatically converted to Kodi tags, enabling easy navigation of Mubi-curated collections directly within Kodi
- 🎛️ Skip specific Mubi genres: Configure the addon to ignore movies from certain genres. Go to settings and enter the genres you'd like to skip, separated by semicolons (e.g., horror;comedy).

## Installation

### Option 1: Install from Repository (Recommended) 📦

1. **Download the repository**: Get the latest `repository.kubi2021-2.zip` from the [releases page](https://github.com/kubi2021/plugin.video.mubi/releases) or directly from [here](https://raw.githubusercontent.com/kubi2021/plugin.video.mubi/main/repository.kubi2021-2.zip)
2. **Install the repository**: In Kodi, go to **Add-ons > Install from zip file** and select the downloaded `repository.kubi2021-2.zip`
3. **Install the MUBI add-on**: Go to **Add-ons > Install from repository > MUBI Repository > Video add-ons > MUBI** and click Install
4. **Automatic updates**: Future updates will be automatically available through the repository

### Option 2: Manual Installation 🔧

1. **Download the add-on**: Get the latest `plugin.video.mubi-2.zip` from the [releases page](https://github.com/kubi2021/plugin.video.mubi/releases) or directly from [here](https://raw.githubusercontent.com/kubi2021/plugin.video.mubi/main/repo/zips/plugin.video.mubi/plugin.video.mubi-2.zip)
2. **Install from zip**: In Kodi, go to **Add-ons > Install from zip file** and select the downloaded `plugin.video.mubi-2.zip`
3. **Manual updates**: You'll need to manually download and install new versions

### Requirements ⚙️

- **Kodi 19+ (Matrix/Nexus)**: This add-on requires Python 3 support
- **Internet connection**: For streaming and metadata fetching

## First run & Populating the Library

1. 🔑 Get an **OMDb API key** from [here](http://www.omdbapi.com/apikey.aspx). It's free and will be needed to populate the library with rich metadata. Don't forget to activate your key using the link in the email.
2. ⚙️ In the **add-on settings**, enter your **OMDb API key**. It's important to do this before the first sync of Mubi to Kodi.
3. 🎬 Launch the **Mubi** add-on.
4. 📁 The **Mubi Movies** folder is automatically added to the Kodi video sources when the addon is first launched. But you need to restart Kodi to see it.
5. ⚙️ For the Mubi movies to be properly scraped and displayed in your library, configure the source in **Kodi settings > Media > Video**:
    - Select the source "Mubi movies" and edit it
    - 1️⃣ Set the content type to **'Video'**.
    - 2️⃣ In the **Set Content** window, check "**Movies are in separate folders**," and leave the other toggles as they are.
    - 3️⃣ Choose your preferred information provider (e.g., **Universal Movie Scraper**).
    - 4️⃣ In the scraper settings, **uncheck** fetching the trailer (since the current add-on provides trailers directly from Mubi). Optionally, check to fetch all **fanart**.
6. 🔙 Go back to the **Mubi** addon and log in.
7. 🔄 Select the option to **sync Mubi locally**.
8. 🎥 Go to the **Movies** tab in Kodi and **update the library** to see the newly added Mubi movies.

### Next Runs 🚀

Whenever you want to **update** the local database, run the **sync** process again. The Kodi library will be automatically updated and cleaned (movies that are no longer available in Mubi will be removed from Kodi)

## Changelog

### Jul 14th, 2025
- Enhanced Audio Support: Added support for 5.1 surround sound (Enhanced AC-3) by declaring support for additional audio codecs (eac3, ac3, dts) in API requests

### Nov 5th, 2024
- added the action to clean the local library after the sync. It was already implemented that movies no longer available in Mubi would be removed from the local repositry, but they would still show up in the library. Now it's fixed.
- fixed a bug that skipped movies with special character in the title.
- refactoring of library class, included automated testing
- added the possiblity to skip Mubi genres you don't want to see in your library. Go to settings and enter the genres you'd like to skip, separated by semicolons (e.g., horror;comedy).

### October 27th 2024
- added support to Mubi watchlist, thanks [GTBoon72](https://github.com/GTBoon72)

### October 13th 2024

- improved the first run of the Addon and made compatible with more platforms
- improved the connection with OMDb. Initially many requests were failing and therefore many movies synced locally would not receive metadata from the Kodi scraper. After this update, there is larger success of connection with OMDb. Also movies for which OMDb was not reachable due to rate limit are not stored locally, so that they can be retried later.

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

The addon makes use of two APIs during the sync process:

- **Mubi**: This API is used to fetch categories and films.
- **OMDb**: Queried for each film to retrieve the IMDb ID, which allows Kodi to pull richer metadata like ratings, cast details, and posters.

The connection to Mubi is generally fast and reliable. However, to prevent overwhelming their servers and to comply with their API usage policies, we limit the number of requests to 60 per minute. This rate limiting may occasionally cause brief pauses during the sync, particularly when processing a large number of categories or films. These pauses are expected and help ensure smooth communication with Mubi's servers.

The OMDb API plays a crucial role in the sync by providing the IMDb ID for each film. This ID enables Kodi to enhance its local library with additional metadata. Unlike Mubi, OMDb’s connection can be less predictable. While we aim to query OMDb as quickly as possible, its rate limits are not clearly defined.

If the addon encounters errors such as "401 Unauthorized" or "429 Too Many Requests," it automatically slows down the rate of requests and introduces pauses to avoid being blocked or restricted. This adjustment can significantly impact the speed of the sync, especially when processing a large number of films.

If the addon is unable to retrieve data from OMDb due to rate limits, those specific movies will not be added to Kodi’s local database during that sync. However, you can easily retry syncing these films later, once the API limits have reset.


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
