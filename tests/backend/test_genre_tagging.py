import unittest
from backend.scraper import MubiScraper

class TestGenreTagging(unittest.TestCase):
    
    def setUp(self):
        # Initialize scraper (no need for real session for this unit test)
        self.scraper = MubiScraper()

    def test_enrich_genres_adds_lgbtq_tag_synopsis(self):
        """Test that LGBTQ+ tag is added when keyword is in synopsis."""
        film_data = {
            'title': 'Test Film',
            'short_synopsis': 'A moving queer love story.',
            'genres': ['Drama']
        }
        self.scraper._enrich_genres(film_data)
        self.assertIn('LGBTQ+', film_data['genres'])
        self.assertEqual(len(film_data['genres']), 2)

    def test_enrich_genres_adds_lgbtq_tag_editorial(self):
        """Test that LGBTQ+ tag is added when keyword is in editorial."""
        film_data = {
            'title': 'Test Film',
            'short_synopsis': 'Just a story.',
            'default_editorial': 'This film explores LGBT themes.',
            'genres': ['Documentary']
        }
        self.scraper._enrich_genres(film_data)
        self.assertIn('LGBTQ+', film_data['genres'])

    def test_enrich_genres_case_insensitive(self):
        """Test that matching is case-insensitive."""
        keywords = ['Lesbian', 'LESBIAN', 'lgbt', 'QuEeR', 'Transgender', 'Bisexual', 'Non-Binary', 'Drag Queen']
        for kw in keywords:
            film_data = {
                'title': f'Test Film {kw}',
                'short_synopsis': f'Contains {kw} content.',
                'genres': []
            }
            self.scraper._enrich_genres(film_data)
            self.assertIn('LGBTQ+', film_data['genres'], f"Failed to match keyword: {kw}")

    def test_enrich_genres_partial_match(self):
        """Test that partial matches (e.g. 'queers') work."""
        film_data = {
            'title': 'Test Film',
            'short_synopsis': 'A group of queers fight for rights.',
            'genres': []
        }
        self.scraper._enrich_genres(film_data)
        self.assertIn('LGBTQ+', film_data['genres'])

    def test_enrich_genres_no_match(self):
        """Test that no tag is added when no keywords are present."""
        film_data = {
            'title': 'Straight Film',
            'short_synopsis': 'Boy meets girl.',
            'default_editorial': 'A classic romance.',
            'genres': ['Romance']
        }
        self.scraper._enrich_genres(film_data)
        self.assertNotIn('LGBTQ+', film_data['genres'])
        self.assertEqual(len(film_data['genres']), 1)

    def test_enrich_genres_no_duplicate(self):
        """Test that tag is not added if already present."""
        film_data = {
            'title': 'Already Tagged',
            'short_synopsis': 'A queer story.',
            'genres': ['Drama', 'LGBTQ+']
        }
        self.scraper._enrich_genres(film_data)
        self.assertEqual(film_data['genres'].count('LGBTQ+'), 1)

    def test_enrich_genres_handles_missing_fields(self):
        """Test matching handles missing text fields gracefully."""
        film_data = {
            'title': 'Empty Film',
            'genres': []
        }
        # Should not raise error
        self.scraper._enrich_genres(film_data)
        self.assertEqual(len(film_data['genres']), 0)

if __name__ == '__main__':
    unittest.main()
