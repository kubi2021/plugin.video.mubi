# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
from typing import List, Dict, Any

class FilmFilter:
    """
    Handles filtering of film data based on user settings (e.g., Genres).
    Operates on raw film data dictionaries.
    """

    def __init__(self):
        self.skip_genres = self._load_genre_settings()

    def _load_genre_settings(self) -> List[str]:
        """
        Build list of genres to skip based on toggle settings
        """
        addon = xbmcaddon.Addon()
        
        # Map setting IDs to genre names (lowercase for comparison)
        genre_settings = {
            'skip_genre_action': 'action',
            'skip_genre_adventure': 'adventure',
            'skip_genre_animation': 'animation',
            'skip_genre_avant_garde': 'avant-garde',
            'skip_genre_comedy': 'comedy',
            'skip_genre_commercial': 'commercial',
            'skip_genre_crime': 'crime',
            'skip_genre_cult': 'cult',
            'skip_genre_documentary': 'documentary',
            'skip_genre_drama': 'drama',
            'skip_genre_erotica': 'erotica',
            'skip_genre_fantasy': 'fantasy',
            'skip_genre_horror': 'horror',
            'skip_genre_lgbtq': 'lgbtq+',
            'skip_genre_mystery': 'mystery',
            'skip_genre_romance': 'romance',
            'skip_genre_sci_fi': 'sci-fi',
            'skip_genre_short': 'short',
            'skip_genre_thriller': 'thriller',
            'skip_genre_tv_movie': 'tv movie',
        }

        skip_genres = []
        for setting_id, genre_name in genre_settings.items():
            if addon.getSettingBool(setting_id):
                skip_genres.append(genre_name)

        xbmc.log(f"FilmFilter: Genres to skip: {skip_genres}", xbmc.LOGDEBUG)
        return skip_genres

    def filter_films(self, films_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out films that match the skip genres.
        
        :param films_data: List of raw film data dictionaries.
        :return: Filtered list of film data.
        """
        if not self.skip_genres:
            return films_data

        initial_count = len(films_data)
        
        filtered_films = []
        for film in films_data:
            # Check if any of the film's genres matches the skip list
            # The structure of 'genres' in raw API response is usually a list of strings
            # In some Mubi API responses it might be objects, but from scraper.py/mubi.py it seems to be list
            
            # Safe extraction
            film_genres = film.get('genres') or []
            
            # Normalize to lower case for comparison
            film_genres_lower = [g.lower() for g in film_genres]
            
            should_skip = any(skip_g in film_genres_lower for skip_g in self.skip_genres)
            
            if not should_skip:
                filtered_films.append(film)

        removed_count = initial_count - len(filtered_films)
        if removed_count > 0:
            xbmc.log(f"FilmFilter: Removed {removed_count} films based on genre filtering.", xbmc.LOGINFO)
            
        return filtered_films
