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

    @patch('sys.exit')
    def test_run(self, mock_exit):
        # Disable threshold for this test
        self.scraper.MIN_TOTAL_FILMS = 0

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

            # Should NOT exit
            mock_exit.assert_not_called()

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

    @patch('sys.exit')
    def test_run_min_threshold_failure(self, mock_exit):
        # Mock scraper to return few films
        self.scraper.MIN_TOTAL_FILMS = 5
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Returns 1 film per country
        mock_resp.json.return_value = {
            'films': [{'id': 1, 'title': 'A', 'year': 2020}], 'meta': {'next_page': None}
        }
        self.scraper.session.get.return_value = mock_resp
        self.scraper.COUNTRIES = ['US']
        
        self.scraper.run(output_path='test_threshold.json')
        # Should exit(1) because 1 < 5
        mock_exit.assert_called_with(1)
        if os.path.exists('test_threshold.json'):
            os.remove('test_threshold.json')

    @patch('sys.exit')
    def test_run_critical_country_failure(self, mock_exit):
        # Mock US returns 0 films
        self.scraper.CRITICAL_COUNTRIES = ['US']
        self.scraper.COUNTRIES = ['US', 'GB']
        
        def side_effect(*args, **kwargs):
            # args[0] is url. mock response based on country?
            # Simplified: check if 'Client-Country': 'US' in headers
            headers = kwargs.get('headers', {})
            if headers.get('Client-Country') == 'US':
                return MagicMock(status_code=200, json=lambda: {'films': [], 'meta': {}}) # 0 films
            else:
                return MagicMock(status_code=200, json=lambda: {'films': [{'id': 2, 'title': 'B', 'year': 2020}], 'meta': {}})
        
        self.scraper.session.get.side_effect = side_effect
        
        self.scraper.run(output_path='test_critical.json')
        # Should exit(1) because US is critical and had 0 films
        mock_exit.assert_called_with(1)
        if os.path.exists('test_critical.json'):
            os.remove('test_critical.json')

    @patch('sys.exit')
    def test_validate_data_integrity(self, mock_exit):
        # 10 films, 1 missing year (10% > 5%) -> Failure
        self.scraper.MIN_TOTAL_FILMS = 0 # Disable count check
        self.scraper.MAX_MISSING_PERCENT = 5.0
        
        items = [{'mubi_id': i, 'title': f'T{i}', 'year': 2020} for i in range(9)]
        items.append({'mubi_id': 10, 'title': 'Bad', 'year': None}) # 1 bad out of 10
        
        errors = self.scraper.validate_data(items)
        self.assertTrue(len(errors) > 0)
        self.assertIn("Field Integrity", errors[0])

    def test_validate_integrity_failure(self):
        # 3. Simulate critical failure (>5% missing year)
        items = []
        for i in range(100):
            item = {'mubi_id': i, 'title': 'T'}
            if i < 10: # 10% missing year
                 pass 
            else:
                 item['year'] = 2020
            items.append(item)
        
        errors = self.scraper.validate_data(items)
        self.assertTrue(any("Field Integrity" in e for e in errors))

    def test_detect_clusters(self):
        """Test that identical catalogues are grouped correctly."""
        # Setup: DE, AT, CH have films [1, 2]. US has [3].
        final_items = [
            {'mubi_id': 1, 'countries': ['DE', 'AT', 'CH']},
            {'mubi_id': 2, 'countries': ['DE', 'AT', 'CH']},
            {'mubi_id': 3, 'countries': ['US']}
        ]
        
        clusters = self.scraper.detect_clusters(final_items)
        
        # Expect 2 clusters
        self.assertEqual(len(clusters), 2)
        
        # Verify DACH cluster
        dach_cluster = next((c for c in clusters if 'DE' in c['members']), None)
        self.assertIsNotNone(dach_cluster)
        self.assertEqual(dach_cluster['leader'], 'DE') # DE is critical, should be leader
        self.assertEqual(set(dach_cluster['members']), {'DE', 'AT', 'CH'})
        self.assertEqual(dach_cluster['count'], 2)

        # Verify US cluster
        us_cluster = next((c for c in clusters if 'US' in c['members']), None)
        self.assertIsNotNone(us_cluster)
        self.assertEqual(us_cluster['leader'], 'US')
        self.assertEqual(us_cluster['members'], ['US'])

    @patch('backend.scraper.MubiScraper.fetch_films_for_country')
    @patch('json.load')
    @patch('os.path.exists')
    def test_run_shallow_mode(self, mock_exists, mock_json_load, mock_fetch):
        """Test that shallow mode only scrapes leaders and attributes films to members."""
        # Setup mocks
        mock_exists.return_value = True
        mock_json_load.return_value = [
            {"leader": "A", "members": ["A", "B", "C"]}
        ]
        
        # Setup fetch return
        mock_fetch.return_value = [
            {'id': 101, 'title': 'Film 101'}
        ]
        
        # Run in shallow mode
        with patch('builtins.open', MagicMock(), create=True) as mock_file:
             # We need to mock validate_data to start fresh or ensure it passes
             with patch.object(self.scraper, 'validate_data', return_value=[]):
                self.scraper.run(mode='shallow', clusters_path='dummy.json', output_path='out.json')
        
        # Verify:
        # 1. fetch_films_for_country called ONLY for 'A'
        mock_fetch.assert_called_once_with('A')
        
        # 2. We can't easily inspect the 'out.json' write content with simple mock_open
        # But we can verify no errors were logged/raised.
        # Ideally we'd inspect what was passed to json.dump.

if __name__ == '__main__':
    unittest.main()
