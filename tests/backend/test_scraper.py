import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys

# Add project root directory to path so we can import backend package
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.scraper import MubiScraper

class TestMubiScraper(unittest.TestCase):

    def setUp(self):
        self.scraper = MubiScraper()
        # Replace the real session with a mock
        self.scraper.session = MagicMock()

    def test_fetch_films_for_country_success(self):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'films': [
                {'id': 1, 'title': 'Test Film 1', 'original_title': 'TF1', 'year': 2023},
                {'id': 2, 'title': 'Test Film 2'}
            ],
            'meta': {'next_page': None}
        }
        
        # Setup session mock
        self.scraper.session.get.return_value = mock_response

        films = self.scraper.fetch_films_for_country('US')
        
        self.assertEqual(len(films), 2)
        self.assertEqual(films[0]['id'], 1)
        self.assertEqual(films[0]['title'], 'Test Film 1')

    def test_run(self):
        # Mock responses
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'films': [
                {'id': 1, 'title': 'Global Film', 'year': 2020},
                {'id': 2, 'title': 'Local Film', 'year': 2021}
            ],
            'meta': {'next_page': None}
        }
        
        self.scraper.session.get.return_value = mock_resp
        
        # Override countries to just 2 for speed
        self.scraper.COUNTRIES = ['US', 'GB']
        
        output_file = 'test_films.json'
        try:
            self.scraper.run(output_path=output_file)
            
            self.assertTrue(os.path.exists(output_file))
            
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            self.assertEqual(len(data['items']), 2)
            
            # Check Film 1
            film1 = next(f for f in data['items'] if f['mubi_id'] == 1)
            self.assertEqual(sorted(film1['countries']), ['GB', 'US'])
            
            # Verify removed fields are not present
            self.assertNotIn('tmdb_id', film1)
            self.assertNotIn('imdb_id', film1)
            self.assertNotIn('image', film1)

        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

if __name__ == '__main__':
    unittest.main()
