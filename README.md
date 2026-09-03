# MUBI Addon for Kodi 🎥🚀

![Tests](https://github.com/kubi2021/plugin.video.mubi/workflows/Run%20Tests/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-70%25-yellow)
![GitHub branch protection](https://img.shields.io/badge/branch%20protection-enabled-green)

## Why I'm doing this

I really enjoy MUBI and their curated selection of films. However, I find their interface somewhat cluttered, often requiring too many clicks to make a decision. When selecting a film, I prefer to have the key information readily available: duration, genre, and rating. I also value the ability to sort films by rating or recent additions. Thankfully, Kodi offers all of these features.

This project is a personal endeavour I work on in my free time. As I am not a professional developer, updates or changes might take a little longer to implement.

If you are looking for a simple way of browsing the MUBI catalogue without integrating with the Kodi library, another extension does exactly this: [mtr81/kodi_addons](https://github.com/mtr81/kodi_addons).

> **Want to contribute?** Development, testing, release, and backend documentation lives in [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Features

- 🎬 **Full MUBI catalogue** — Fetches all movies with ratings and descriptions, seamlessly integrated into your Kodi library
- 🌍 **Worldwide catalogue** — Access MUBI's entire global catalogue (~2000 films). **Fast Sync** (beta) downloads a pre-computed catalogue in seconds; the classic sync fetches directly from MUBI across a small curated set of countries
- 🛡️ **Rich metadata** — Finds IMDb matches so Kodi scrapers can fetch cast, ratings, posters, and more
- 🍿 **Optimal quality** — Automatically selects best stream quality for movies and trailers
- 📺 **Native playback** — Movies play directly in Kodi with Mubi subtitles and multiple audio streams
- 🎨 **Artwork** — Posters, thumbnails, fanart, and clearlogos
- 🏆 **Ratings & advisories** — MPAA ratings and content warnings for informed viewing
- 🔖 **Watchlist sync** — Your MUBI watchlist accessible directly from Kodi
- 🈯 **Multi-language** — Titles and descriptions in languages supported by MUBI (configure in plugin settings)
- 🛡️ **VPN-friendly** — Detects your country via IP and suggests optimal VPN servers for geo-restricted films
- 🖥️ **Browser fallback** — Opens films in your browser when Kodi playback isn't available (tested on macOS only)

## Installation

### Option 1: File Manager Source (Easiest) 🌐

1. **Add file manager source**: In Kodi, go to **File Manager > Add source**
2. **Enter URL**: `https://kubi2021.github.io/plugin.video.mubi/`
3. **Install repository**: Go to **Add-ons > Install from zip file** and select the repository from your new source
4. **Install MUBI add-on**: Go to **Add-ons > Install from repository > MUBI Repository > Video add-ons > MUBI**
5. **Automatic updates**: Future updates will be automatically available

### Option 2: Download Repository Zip 📦

1. **Download the repository**: Get the latest `repository.kubi2021-*.zip` from [here](https://kubi2021.github.io/plugin.video.mubi/repository.kubi2021-2.zip)
2. **Install the repository**: In Kodi, go to **Add-ons > Install from zip file** and select the downloaded repository zip file
3. **Install the MUBI add-on**: Go to **Add-ons > Install from repository > MUBI Repository > Video add-ons > MUBI** and click Install
4. **Automatic updates**: Future updates will be automatically available through the repository

### Option 3: Direct Add-on Installation (No Repository) 🔧

1. **Download the add-on**: Get the latest `plugin.video.mubi-*.zip` from the [releases page](https://github.com/kubi2021/plugin.video.mubi/releases)
2. **Install from zip**: In Kodi, go to **Add-ons > Install from zip file** and select the downloaded add-on zip file
3. **Manual updates**: You'll need to manually download and install new versions

### Requirements ⚙️

- **Kodi 19+ (Matrix/Nexus)**: This add-on requires Python 3 support
- **Internet connection**: For streaming and metadata fetching

## First run & Populating the Library

1. 🔑 Get an **TMDB API key** from [here](https://www.themoviedb.org/). It's free and will be needed to populate the library with rich metadata. Once you sign-up, head to [the API page](https://www.themoviedb.org/settings/api), fill the form (the information is not so important, you can put kodi.tv as the URL, and in the description, just write that you will use it for fetching movies metadata for a Kodi plugin). Don't forget to activate your key using the link in the email.
2. ⚙️ In the **add-on settings**, enter your **TMDB API key**. It's important to do this before the first sync of Mubi to Kodi.
3. In the setting, enable the **auto_clean_library** option. Kodi will automatically clean the library after the sync. Leave it disabled if you have other plugins that manage your library, like Jellyfin.
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

### Sep 3rd, 2026 - Fast Sync by Default ⚡
- **Fast Sync is now the default**: On update, existing users are automatically switched to the pre-computed GitHub catalogue ("Fast Sync") once. New installs start with it enabled too. You can still turn it back off in the add-on settings if you need the legacy per-country sync.

### Sep 3rd, 2026 - Correct Availability Across Timezones 🕒
- **Timezone-Aware Availability**: Fixed a case where a film's availability could be judged wrong when Mubi expressed its start/end times with a numeric UTC offset (e.g. `+02:00`) instead of `Z`. Availability is now compared as real instants, and the library and browsing views use one shared check so they always agree.
- **Stricter Start-Date Check**: A film is now only treated as available on its dates when it has a start date that has already passed. A film with only a future end date and no start date no longer shows up unless Mubi still marks it as live.

### Dec 30th, 2025 - Bayesian Ratings & Smarter Availability 🧠🎯
- **Bayesian Ratings**: Introduced Bayesian composite ratings for the Fast Sync mode (currently in beta). This provides a more balanced and reliable scoring system by weighing ratings from multiple sources.
- **Refined Availability Logic**: Fixed an issue where "upcoming" movies could appear in your library before they were actually playable. Now, films will only show up when they are truly available to watch.

### Dec 22nd, 2025 - Bayesian Ratings & OMDB 🧠
- **Bayesian Composite Ratings**: Implemented a smart rating system that fuses scores from Mubi, TMDB, and IMDB into a single, reliable 0-10 score. This "Bayesian Average" prevents movies with few votes from skewing the rankings. This is currently not showing in the plugin, only in the backend.
- **OMDB Backend Integration**: The backend scraper now directly queries OMDB for additional ratings (IMDb, Rotten Tomatoes, Metacritic) during the enrichment phase.
- **Robustness**: Improved API key handling and error resilience in the backend pipeline.

### Dec 20th, 2025 - Improved Availability Handling 🎯
- **Smarter Country Selection**: Worldwide sync now prioritizes countries with better VPN infrastructure when selecting which regions to fetch from
- **More Accurate Syncs**: Fixed edge cases where films could show incorrect or incomplete availability data
- **Better User Experience**: Removed low-tier VPN countries from sync optimization, resulting in more reliable playback options

### Dec 18th, 2025 - Fast Sync (Beta) ⚡
- **GitHub-Hosted Backend Scraper**: Built a backend scraper that runs on GitHub Actions, pre-computing the MUBI catalogue so the plugin doesn't need to crawl the API directly.
- **Fast Sync Mode**: Enable in **Settings > Advanced > Fast Sync (Beta)** to use the new sync method.
- **Dramatically Faster**: Syncs the entire MUBI catalogue in seconds instead of ~15 minutes with the older method.

### Dec 12th, 2025 - TMDB & Speed Boost 🚀
- **TMDB Integration**: Added The Movie Database (TMDB) as the primary metadata provider for richer and more reliable movie details (ratings, cast, posters).
- **10x Faster Sync**: Dramatically improved synchronization speed by optimizing API calls and implementing parallel processing.
- **Strict Validation**: Added robust API key validation to prevent sync errors.
- **Plugin Compatibility**: Solved conflict with other plugins (e.g. Jellyfin). Thanks to [@axelsimon](https://github.com/axelsimon) for supporting the fix!

### Dec 7th, 2025 - VPN & Multi-Country Support 🌍

**VPN-Aware Country Detection:**
- 🔍 Added IP-based geolocation to detect your actual country from current IP (using ipapi.co/ipinfo.io)
- 🔄 VPN users can now switch countries without restarting Kodi
- 💬 User-friendly error dialogs when films are geo-restricted, showing VPN suggestions sorted by server performance

**Multi-Country Sync & Availability:**
- 🌐 Films now store availability in NFO files with all countries where they can be played
- 📍 Sync defaults to your configured client country (Settings > Country)
- ⚡ VPN tier classification for optimal server recommendations (based on 2024/2025 Global Internet Speed Indices)

**Sync Performance Improvements:**
- 🚀 Removed artificial delays - sync is now significantly faster
- ⏱️ Reactive rate limiting: only slows down when MUBI returns 429 (Too Many Requests)
- 🔁 Exponential backoff with Retry-After header support
- 📊 Fixed progress counter to monotonically increase across countries

### Dec 5th, 2025
- Enhanced NFO metadata with Kodi 20+ tags: `<premiered>`, `<tag>` (content warnings), `<tagline>` (press quotes)
- Added support for multiple `<country>` tags instead of just the first country
- Added `<channels>` audio channel information from MUBI's extended audio options
- Expanded artwork extraction: poster from `cover_artwork_vertical`, fanart from `centered_background`
- Kodi 20+ (Nexus) live browsing enhancements with full InfoTagVideo API support
- Added audio and subtitle stream details for live browsing (matching NFO metadata parity)
- Fixed sync loop bug: sync no longer repeats infinitely when there are no new movies

### Jul 21st, 2025
- Removed category-based browsing system for simplified user experience
- Direct film synchronization using MUBI API V4 /browse/films endpoint
- Faster sync process with fewer API calls and reduced complexity
- Rich metadata support with audio languages, subtitle languages, and media features
- Optimal trailer quality selection (1080p/720p) for better viewing experience
- Multiple artwork types support (posters, thumbnails, clearlogos)
- Content ratings and MPAA information display
- Audio format indicators (stereo, 5.1, Dolby Atmos) in film metadata
- Comprehensive subtitle language and accessibility information
- REMOVED: Mubi collection tagging (may be re-added in future versions)

### Jul 20th, 2025
- Migrated to API V4
- Added modern DRM configuration support for Kodi 22+ with backward compatibility for older versions

### Jul 19th, 2025
- Converted project to proper Kodi repository with automated zip generation

### Jul 14th, 2025
- Enhanced Audio Support: Added support for 5.1 surround sound (Enhanced AC-3) by declaring support for additional audio codecs (eac3, ac3, dts) in API requests

### Nov 5th, 2024
- added the action to clean the local library after the sync. It was already implemented that movies no longer available in Mubi would be removed from the local repositry, but they would still show up in the library. Now it's fixed.
- fixed a bug that skipped movies with special character in the title.
- refactoring of library class, included automated testing
- added the possibility to skip Mubi genres you don't want to see in your library. Go to settings and enter the genres you'd like to skip, separated by semicolons (e.g., horror;comedy).

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



### 1. Manually Creating the Mubi Source in Kodi 🛠️

If for some reason the Mubi Movies folder isn't automatically added as a video source during the installation process, you can manually create the source in Kodi by following these steps:

1. Navigate to **Settings > Media > Library**.
2. Select **Add Video Source**.
3. Enter the following path for the source:
   ```
   special://userdata/addon_data/plugin.video.mubi
   ```
4. Complete the process, and the Mubi Movies folder will be available in your Kodi library.

After adding the source manually, follow the normal steps to configure it for movies and set up the scraper.

---

Enjoy Mubi on Kodi! 🎥🍿

---

_Last updated: 2026-09-03_
