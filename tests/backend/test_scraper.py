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

            # Verify removed fields are not present
            self.assertNotIn('tmdb_id', film1)
            self.assertNotIn('imdb_id', film1)
            self.assertNotIn('image', film1)

        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    @patch('sys.exit')
    def test_run_panic_if_no_films(self, mock_exit):
        # Mock empty response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'films': [], 'meta': {'next_page': None}}
        self.scraper.session.get.return_value = mock_resp
        
        self.scraper.COUNTRIES = ['US']
        self.scraper.run(output_path='test_panic.json')
        
        # Verify sys.exit(1) was called
        mock_exit.assert_called_with(1)

    @patch('sys.exit')
    def test_run_partial_error(self, mock_exit):
        # Mock one success, one failure
        def side_effect(*args, **kwargs):
            # args[0] is url
            # check headers or url for country... 
            # simplified: inspect call args or just use side_effect generator
            return MagicMock() # catch-all
            
        # Better approach: check 'Client-Country' header in call args
        mock_resp_success = MagicMock()
        mock_resp_success.status_code = 200
        mock_resp_success.json.return_value = {
            'films': [{'id': 1, 'title': 'OK'}], 'meta': {'next_page': None}
        }
        
        # Requests raises exception
        self.scraper.session.get.side_effect = [
            mock_resp_success, # US
            Exception("Request failed") # GB
        ]
        
        self.scraper.COUNTRIES = ['US', 'GB']
        
        try:
            self.scraper.run(output_path='test_partial.json')
            # Verify sys.exit(1) was called because of the error
            mock_exit.assert_called_with(1)
            # Verify file WAS created despite error (partial success)
            self.assertTrue(os.path.exists('test_partial.json'))
        finally:
            if os.path.exists('test_partial.json'):
                os.remove('test_partial.json')

if __name__ == '__main__':
    unittest.main()
