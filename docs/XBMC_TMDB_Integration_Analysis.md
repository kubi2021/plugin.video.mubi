# XBMC/Kodi TMDB Integration Analysis

This document analyzes how the official XBMC/Kodi codebase integrates with The Movie Database (TMDB) API, focusing on patterns and approaches that could be reused in Kodi plugin development.

## Overview

XBMC/Kodi uses TMDB through dedicated metadata scraper addons:
- `metadata.themoviedb.org.python` for movies
- `metadata.tvshows.themoviedb.org.python` for TV shows

Both addons are Python-based and follow similar architectural patterns.

## TMDB API Key Management

### Movie Scraper (`metadata.themoviedb.org.python`)
- **Location**: `addons/metadata.themoviedb.org.python/python/lib/tmdbscraper/tmdbapi.py:29`
- **Implementation**: Hardcoded constant
- **API Key**: `f090bb54758cabf231fb605d3e3e0468`

```python
TMDB_PARAMS = {'api_key': 'f090bb54758cabf231fb605d3e3e0468'}
```

### TV Show Scraper (`metadata.tvshows.themoviedb.org.python`)
- **Location**: `addons/metadata.tvshows.themoviedb.org.python/libs/settings.py:25`
- **Implementation**: Hardcoded constant with descriptive name
- **API Key**: `af3a53eb387d57fc935e9128468b1899`

```python
TMDB_CLOWNCAR = 'af3a53eb387d57fc935e9128468b1899'
TMDB_PARAMS = {'api_key': settings.TMDB_CLOWNCAR}
```

**Key Observations:**
- Both scrapers use separate API keys (likely for rate limiting/quota management)
- Movie scraper hardcodes directly in params dict
- TV scraper uses a settings-based approach with a constant
- No user-configurable API keys in either addon

## API Calling Patterns

### Base Configuration
```python
BASE_URL = 'https://api.themoviedb.org/3/{}'
HEADERS = (
    ('User-Agent', 'Kodi Movie scraper by Team Kodi'),
    ('Accept', 'application/json'),
)
```

### Request Implementation
- **Library**: Uses Python's built-in `urllib` (both Python 2/3 compatible)
- **Method**: `urllib.request.Request` with headers and URL-encoded parameters
- **Response Handling**: JSON parsing with `json.loads()`

**Core Request Function** (`api_utils.py`):
```python
def load_info(url, params=None, default=None, resp_type='json'):
    theerror = ''
    if params:
        url = url + '?' + urlencode(params)
    req = Request(url, headers=HEADERS)
    try:
        response = urlopen(req)
    except URLError as e:
        # Error handling...
    if resp_type.lower() == 'json':
        resp = json.loads(response.read().decode('utf-8'))
    return resp
```

### API Endpoints Used
- **Search**: `/search/movie` and `/search/tv`
- **Details**: `/movie/{id}` and `/tv/{id}`
- **Find by External ID**: `/find/{external_id}`
- **Configuration**: `/configuration`
- **Collections**: `/collection/{id}`
- **Seasons/Episodes**: `/tv/{id}/season/{season}/episode/{episode}`

### Parameter Patterns
```python
def _set_params(append_to_response, language):
    params = TMDB_PARAMS.copy()
    if language is not None:
        params['language'] = language
    if append_to_response is not None:
        params['append_to_response'] = append_to_response
    return params
```

Common parameters:
- `api_key`: Always included
- `language`: For localized content
- `append_to_response`: For additional data in single request
- `page`: For pagination
- `external_source`: For finding by IMDB/TVDB IDs

## Reusable Patterns for Plugin Development

### 1. API Key Management
- Use constants for API keys rather than user settings
- Consider separate keys for different content types if rate limits are a concern
- Follow Kodi's pattern of descriptive constant names

### 2. Request Wrapper
The `api_utils.load_info()` pattern provides good error handling:
- URL construction with parameter encoding
- Header management
- Exception handling for network errors
- JSON response parsing
- Optional default return values

### 3. Language Handling
- Use `language` parameter for localized content
- Fallback to English (`en-US`) when localized data is missing
- Store language preferences in addon settings

### 4. Data Fetching Strategy
- Use `append_to_response` to minimize API calls
- Implement caching for expensive operations
- Handle pagination for search results
- Parse external IDs (IMDB, TVDB) for cross-referencing

### 5. Error Handling
- Check for 'error' key in responses
- Provide meaningful error messages to users
- Use Kodi's logging system for debugging

## Code Examples

### Basic Movie Search
```python
def search_movie(query, year=None, language=None):
    params = {'api_key': TMDB_API_KEY, 'query': query}
    if year:
        params['year'] = str(year)
    if language:
        params['language'] = language

    url = 'https://api.themoviedb.org/3/search/movie'
    return make_request(url, params)
```

### Movie Details with Extras
```python
def get_movie_details(movie_id, language=None):
    params = {'api_key': TMDB_API_KEY}
    if language:
        params['language'] = language
    params['append_to_response'] = 'credits,images,videos'

    url = f'https://api.themoviedb.org/3/movie/{movie_id}'
    return make_request(url, params)
```

## Recommendations for plugin.video.mubi

1. **API Key**: Use a dedicated TMDB API key for the plugin
2. **Request Pattern**: Adopt the `api_utils.load_info()` approach for consistency
3. **Language Support**: Implement language settings similar to Kodi scrapers
4. **Caching**: Consider implementing response caching to reduce API calls
5. **Error Handling**: Use Kodi's notification system for API errors
6. **External IDs**: Support IMDB ID lookups for better integration

## File References

- `addons/metadata.themoviedb.org.python/python/lib/tmdbscraper/tmdbapi.py`
- `addons/metadata.themoviedb.org.python/python/lib/tmdbscraper/api_utils.py`
- `addons/metadata.tvshows.themoviedb.org.python/libs/tmdb.py`
- `addons/metadata.tvshows.themoviedb.org.python/libs/settings.py`
- `addons/metadata.tvshows.themoviedb.org.python/libs/api_utils.py`

## Dynamic API Key Reuse

### Feasibility
It is technically possible to dynamically reference the TMDB API key from Kodi's official scrapers by importing their Python modules at runtime. Kodi addons can access other installed addons' paths using the `xbmcaddon` module and import their code.

However, this approach is not recommended as it relies on undocumented internal structures that may change between Kodi versions.

### Technical Approach
To import from another addon:
```python
import xbmcaddon
import sys

addon = xbmcaddon.Addon('metadata.themoviedb.org.python')
path = addon.getAddonInfo('path')
sys.path.insert(0, path + '/python/lib')
from tmdbscraper import tmdbapi
api_key = tmdbapi.TMDB_PARAMS['api_key']
```

### Pros
- Automatic key updates if Kodi updates the scrapers
- No need to manage API key separately

### Cons
- Fragile: Depends on addon installation paths and internal code structure
- Not supported: No public API for cross-addon imports
- Potential breakage in future Kodi updates
- Requires the scraper addon to be installed (which it is by default)
- Different keys for movies vs TV shows (rate limiting)

### Recommended Approach
Continue hardcoding a dedicated TMDB API key for the plugin, following Kodi's own pattern. This is the most reliable and maintainable solution.

### Alternatives
- **Addon Settings**: Store the API key in addon settings (user-configurable)
- **Shared Library**: Create a shared Kodi addon for TMDB access (overkill for this use case)
- **Addon Dependencies**: Depend on the scraper addon (not applicable as scrapers don't export APIs)

## Conclusion

XBMC/Kodi's TMDB integration provides a solid foundation for plugin development. The patterns emphasize reliability, error handling, and efficient API usage. While the API keys are hardcoded, the request patterns and data handling approaches are highly reusable for custom Kodi plugins.