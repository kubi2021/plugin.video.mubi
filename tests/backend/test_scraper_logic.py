import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys
import tempfile
import shutil

# Ensure backend can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.scraper import MubiScraper

class TestScraperLogic(unittest.TestCase):
    
    def setUp(self):
        self.scraper = MubiScraper()
        self.scraper.MIN_TOTAL_FILMS = 0 # Disable threshold for tests
        self.scraper.CRITICAL_COUNTRIES = [] # Disable critical country checks
        # Mock session to prevent real network calls
        self.scraper.session = MagicMock()
        # Create a temp directory for file operations
        self.test_dir = tempfile.mkdtemp()
        self.films_json_path = os.path.join(self.test_dir, 'films.json')
        self.series_json_path = os.path.join(self.test_dir, 'series.json')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_incremental_update_preserves_custom_fields(self):
        """
        Verify that scraping updates existing films (e.g. title) 
        but preserves fields not present in the scraper response (e.g. imdb_id).
        """
        # 1. Setup existing data with a custom field
        existing_data = {
            'items': [
                {
                    'mubi_id': 100, 
                    'title': 'Old Title', 
                    'year': 1990, 
                    'imdb_id': 'tt0099685', # Custom field
                    'available_countries': {'US': {'status': 'live'}}
                }
            ]
        }
        with open(self.films_json_path, 'w') as f:
            json.dump(existing_data, f)
            
        # 2. Mock scraper retrieval of the SAME film with NEW data
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'films': [
                {
                    'id': 100, 
                    'title': 'New Updated Title', # Changed
                    'year': 1990,
                    'directors': [{'name': 'Director A'}],
                    'consumable': {'status': 'live'}
                }
            ],
            'meta': {'next_page': None}
        }
        self.scraper.session.get.return_value = mock_resp
        
        # 3. Run shallow sync (updates existing)
        # We enforce US so it hits the mock for the right country
        with patch('backend.scraper.MubiScraper.COUNTRIES', ['US']):
            self.scraper.run(output_path=self.films_json_path, series_path=self.series_json_path, mode='shallow', input_path=self.films_json_path)
            
        # 4. Assertions
        with open(self.films_json_path, 'r') as f:
            data = json.load(f)
            
        film = data['items'][0]
        self.assertEqual(film['mubi_id'], 100)
        self.assertEqual(film['title'], 'New Updated Title', "Title should be updated from scrape")
        self.assertEqual(film['imdb_id'], 'tt0099685', "Custom field (imdb_id) should be preserved")

    def test_deep_sync_prunes_missing_films(self):
        """
        Verify that DEEP sync removes films that are not found in the scrape.
        """
        # 1. Setup existing data with 2 films
        existing_data = {
            'items': [
                {'mubi_id': 1, 'title': 'Film 1', 'available_countries': {'US': {'status': 'live'}}},
                {'mubi_id': 2, 'title': 'Film 2', 'available_countries': {'US': {'status': 'live'}}}
            ]
        }
        with open(self.films_json_path, 'w') as f:
            json.dump(existing_data, f)
            
        # 2. Mock scraper to return ONLY Film 1 (Film 2 has disappeared)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'films': [
                {'id': 1, 'title': 'Film 1', 'year': 2020, 'consumable': {'status': 'live'}}
            ],
            'meta': {'next_page': None}
        }
        self.scraper.session.get.return_value = mock_resp
        
        # 3. Run DEEP sync
        with patch('backend.scraper.MubiScraper.COUNTRIES', ['US']):
            self.scraper.run(output_path=self.films_json_path, series_path=self.series_json_path, mode='deep')
            
        # 4. Assertions
        with open(self.films_json_path, 'r') as f:
            data = json.load(f)
            
        ids = [item['mubi_id'] for item in data['items']]
        self.assertIn(1, ids, "Film 1 should be kept")
        self.assertNotIn(2, ids, "Film 2 should be pruned because it wasn't found in deep sync")

    def test_shallow_sync_keeps_missing_films(self):
        """
        Verify that SHALLOW sync does NOT remove films just because they weren't scraped this run.
        (e.g. if we only scrape US, we shouldn't delete FR films).
        """
        # 1. Setup existing data with Film A (US) and Film B (FR)
        existing_data = {
            'items': [
                {'mubi_id': 1, 'title': 'US Film', 'available_countries': {'US': {'status': 'live'}}},
                {'mubi_id': 2, 'title': 'FR Film', 'available_countries': {'FR': {'status': 'live'}}}
            ]
        }
        with open(self.films_json_path, 'w') as f:
            json.dump(existing_data, f)
            
        # 2. Mock scraper to return ONLY Film 1 (simulating a US-only scrape)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'films': [
                {'id': 1, 'title': 'US Film', 'year': 2020, 'consumable': {'status': 'live'}}
            ],
            'meta': {'next_page': None}
        }
        self.scraper.session.get.return_value = mock_resp
        
        # 3. Run SHALLOW sync
        # We force targets to only be US (which contains Film 1), leaving Film 2 untouched
        with patch('backend.scraper.MubiScraper.COUNTRIES', ['US']):
            # We must make sure calculate_greedy_targets only picks US, or we interpret it as such
            with patch.object(self.scraper, 'calculate_greedy_targets', return_value=['US']):
                 self.scraper.run(output_path=self.films_json_path, series_path=self.series_json_path, mode='shallow', input_path=self.films_json_path)
            
        # 4. Assertions
        with open(self.films_json_path, 'r') as f:
            data = json.load(f)
            
        ids = [item['mubi_id'] for item in data['items']]
        self.assertIn(1, ids, "Film 1 should be updated/kept")
        self.assertIn(2, ids, "Film 2 should be preserved in shallow sync even if not scraped")

    def test_deep_sync_resets_countries(self):
        """
        Verify that DEEP sync resets the available countries for a film.
        If Film 1 was in [US, GB] but now only found in [US], it should update.
        """
        # 1. Setup: Film 1 thinks it is in US and GB
        existing_data = {
            'items': [
                {'mubi_id': 1, 'title': 'Film 1', 'available_countries': {'US': {'status': 'live'}, 'GB': {'status': 'live'}}}
            ]
        }
        with open(self.films_json_path, 'w') as f:
            json.dump(existing_data, f)
            
        # 2. Mock: Scraper for US returns Film 1. Scraper for GB returns Nothing.
        with patch.object(self.scraper, 'fetch_films_for_country') as mock_fetch:
            def fetch_side_effect(country_code):
                if country_code == 'US':
                    return [{'id': 1, 'title': 'Film 1', 'year': 2020, 'consumable': {'status': 'live'}}]
                return [] # GB returns nothing
            
            mock_fetch.side_effect = fetch_side_effect
            
            # 3. Run DEEP sync on US and GB
            with patch('backend.scraper.MubiScraper.COUNTRIES', ['US', 'GB']):
                self.scraper.run(output_path=self.films_json_path, series_path=self.series_json_path, mode='deep')

        # 4. Assertions
        with open(self.films_json_path, 'r') as f:
            data = json.load(f)
            
        film = data['items'][0]
        self.assertEqual(film['mubi_id'], 1)
        self.assertEqual(list(film['available_countries'].keys()), ['US'], "Countries should be reset to only where it was found (US), removing GB")

    def test_shallow_sync_appends_countries(self):
        """
        Verify that SHALLOW sync APPENDS countries.
        If Film 1 was in [US], and we scrape GB and find it, it becomes [GB, US].
        """
        # 1. Setup: Film 1 in US
        existing_data = {
            'items': [
                {'mubi_id': 1, 'title': 'Film 1', 'available_countries': {'US': {'status': 'live'}}}
            ]
        }
        with open(self.films_json_path, 'w') as f:
            json.dump(existing_data, f)

        # 2. Mock: Scrape GB and find Film 1
        with patch.object(self.scraper, 'fetch_films_for_country') as mock_fetch:
            mock_fetch.return_value = [{'id': 1, 'title': 'Film 1', 'year': 2020, 'consumable': {'status': 'live'}}]
            
            # 3. Run SHALLOW sync on GB
            # Force target to GB
            with patch.object(self.scraper, 'calculate_greedy_targets', return_value=['GB']):
                self.scraper.run(output_path=self.films_json_path, series_path=self.series_json_path, mode='shallow', input_path=self.films_json_path)

        # 4. Assertions
        with open(self.films_json_path, 'r') as f:
            data = json.load(f)
            
        film = data['items'][0]
        self.assertEqual(film['mubi_id'], 1)
        self.assertEqual(sorted(film['available_countries'].keys()), ['GB', 'US'], "New country GB should be appended to existing US")

if __name__ == '__main__':
    unittest.main()
