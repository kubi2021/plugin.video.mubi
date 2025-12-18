import unittest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import shutil
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
        
        test_dir = tempfile.mkdtemp()
        try:
            output_file = os.path.join(test_dir, 'test_films.json')
            series_file = os.path.join(test_dir, 'test_series.json')
            self.scraper.run(output_path=output_file, series_path=series_file)
            
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
            shutil.rmtree(test_dir)

    @patch('sys.exit')
    def test_run_panic_if_no_films(self, mock_exit):
        # Mock empty response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'films': [], 'meta': {'next_page': None}}
        self.scraper.session.get.return_value = mock_resp
        
        test_dir = tempfile.mkdtemp()
        try:
            output_file = os.path.join(test_dir, 'test_panic.json')
            series_file = os.path.join(test_dir, 'test_series.json')
            self.scraper.COUNTRIES = ['US']
            self.scraper.run(output_path=output_file, series_path=series_file)
            
            # Verify sys.exit(1) was called
            mock_exit.assert_called_with(1)
        finally:
            shutil.rmtree(test_dir)

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
        
        test_dir = tempfile.mkdtemp()
        try:
            output_file = os.path.join(test_dir, 'test_partial.json')
            series_file = os.path.join(test_dir, 'test_series.json')
            self.scraper.run(output_path=output_file, series_path=series_file)
            # Verify sys.exit(1) was called because of the error
            mock_exit.assert_called_with(1)
            # Verify file WAS created despite error (partial success)
            self.assertTrue(os.path.exists(output_file))
        finally:
            shutil.rmtree(test_dir)

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
        
        test_dir = tempfile.mkdtemp()
        try:
            output_file = os.path.join(test_dir, 'test_threshold.json')
            series_file = os.path.join(test_dir, 'test_series.json')
            self.scraper.run(output_path=output_file, series_path=series_file)
            # Should exit(1) because 1 < 5
            mock_exit.assert_called_with(1)
        finally:
            shutil.rmtree(test_dir)

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
        
        test_dir = tempfile.mkdtemp()
        try:
            output_file = os.path.join(test_dir, 'test_critical.json')
            series_file = os.path.join(test_dir, 'test_series.json')
            self.scraper.run(output_path=output_file, series_path=series_file)
            # Should exit(1) because US is critical and had 0 films
            mock_exit.assert_called_with(1)
        finally:
            shutil.rmtree(test_dir)

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

    def test_run_deep_mode_validation(self):
        """Test deep mode still runs validation."""
        # Setup mocks to return valid data but fail validation
        self.scraper.session.get.return_value.status_code = 200
        self.scraper.session.get.return_value.json.return_value = {
             'films': [{'id': 1, 'title': ''}], # Missing title triggers validation error
             'meta': {}
        }
        
        with patch('backend.scraper.MubiScraper.COUNTRIES', ['US']):
           with patch('builtins.open', mock_open()) as mocked_file:
                # Mock sys.exit to catch failure
                with self.assertRaises(SystemExit):
                     self.scraper.run(mode='deep')

    def test_run_shallow_mode_merge(self):
        """Test that shallow mode merges new countries into existing films without duplicating."""
        # Create temp dir
        test_dir = tempfile.mkdtemp()
        try:
            # 1. Setup Input: Film 1 known in US
            previous_data = {
                'items': [
                    {'mubi_id': 1, 'countries': ['US'], 'title': 'Film 1'}
                ]
            }
            input_file = os.path.join(test_dir, "previous.json")
            with open(input_file, 'w') as f:
                json.dump(previous_data, f)
                
            # 2. Setup Scrape Result: Film 1 found in GB (New country)
            self.scraper.session.get.return_value.status_code = 200
            self.scraper.session.get.return_value.json.return_value = {
                 'films': [{'id': 1, 'title': 'Film 1', 'directors': []}], 
                 'meta': {'next_page': None}
            }
            
            with patch('backend.scraper.MubiScraper.COUNTRIES', ['US', 'GB']):
                 # Force target to GB to simulate finding the film there
                 with patch.object(self.scraper, 'calculate_greedy_targets', return_value=['GB']):
                     output_file = os.path.join(test_dir, "output.json")
                     series_file = os.path.join(test_dir, "series.json")
                     self.scraper.run(output_path=output_file, series_path=series_file, mode='shallow', input_path=input_file)
                     
                     # 3. Verify Output
                     with open(output_file, 'r') as f:
                         output = json.load(f)
                         items = output['items']
                         
                         # Should have 1 item (no duplicate)
                         self.assertEqual(len(items), 1)
                         film = items[0]
                         self.assertEqual(film['mubi_id'], 1)
                         # Should have BOTH countries merged
                         self.assertIn('US', film['countries'])
                         self.assertIn('GB', film['countries'])
        finally:
            shutil.rmtree(test_dir)

    def test_run_shallow_mode(self):
        """Test shallow mode uses input file and greedy strategy."""
        test_dir = tempfile.mkdtemp()
        try:
            # Create dummy input file
            previous_data = {
                'items': [
                    {'mubi_id': 1, 'countries': ['US'], 'title': 'Test 1', 'year': 2020},
                    {'mubi_id': 2, 'countries': ['GB'], 'title': 'Test 2', 'year': 2020}
                ]
            }
            input_file = os.path.join(test_dir, "previous.json")
            with open(input_file, 'w') as f:
                json.dump(previous_data, f)
                
            # Mock scraper session to return NO new films (so we just keep existing ones)
            self.scraper.session.get.return_value.status_code = 200
            self.scraper.session.get.return_value.json.return_value = {
                 'films': [], 'meta': {'next_page': None}
            }
            
            with patch('backend.scraper.MubiScraper.COUNTRIES', ['US', 'GB']):
                 output_file = os.path.join(test_dir, "output.json")
                 series_file = os.path.join(test_dir, "series.json")
                 self.scraper.run(output_path=output_file, series_path=series_file, mode='shallow', input_path=input_file)
                 
                 # Check output
                 with open(output_file, 'r') as f:
                     output = json.load(f)
                     self.assertEqual(len(output['items']), 2)
                     # Should still have the original films even if scrape returned nothing (Append-Only)
                     self.assertEqual(output['items'][0]['mubi_id'], 1)
        finally:
            shutil.rmtree(test_dir)

    def test_calculate_greedy_targets(self):
        """Test that greedy set cover finds the optimal countries."""
        # Scenario:
        # Film 1: [US, GB]
        # Film 2: [US]
        # Film 3: [DE]
        # Film 4: [FR, DE]
        # Optimal Set: US (covers 1, 2) + DE (covers 3, 4) -> 2 countries
        
        sample_data = [
            {'mubi_id': 1, 'countries': ['US', 'GB']},
            {'mubi_id': 2, 'countries': ['US']},
            {'mubi_id': 3, 'countries': ['DE']},
            {'mubi_id': 4, 'countries': ['FR', 'DE']}
        ]
        
        with patch('backend.scraper.MubiScraper.COUNTRIES', ['US', 'GB', 'DE', 'FR']):
             targets = self.scraper.calculate_greedy_targets(sample_data)
             
             self.assertEqual(len(targets), 2)
             self.assertIn('US', targets)
             self.assertIn('DE', targets)

    def test_run_shallow_mode(self):
        """Test shallow mode uses input file and greedy strategy."""
        test_dir = tempfile.mkdtemp()
        try:
            # Create dummy input file
            previous_data = {
                'items': [
                    {'mubi_id': 1, 'countries': ['US'], 'title': 'Test 1', 'year': 2020},
                    {'mubi_id': 2, 'countries': ['GB'], 'title': 'Test 2', 'year': 2020}
                ]
            }
            input_file = os.path.join(test_dir, "previous.json")
            with open(input_file, 'w') as f:
                json.dump(previous_data, f)
                
            # Mock scraper session to return NO new films (so we just keep existing ones)
            self.scraper.session.get.return_value.status_code = 200
            self.scraper.session.get.return_value.json.return_value = {
                 'films': [], 'meta': {'next_page': None}
            }
            
            with patch('backend.scraper.MubiScraper.COUNTRIES', ['US', 'GB']):
                 output_file = os.path.join(test_dir, "output.json")
                 series_file = os.path.join(test_dir, "series.json")
                 self.scraper.run(output_path=output_file, series_path=series_file, mode='shallow', input_path=input_file)
                 
                 # Check output
                 with open(output_file, 'r') as f:
                     output = json.load(f)
                     self.assertEqual(len(output['items']), 2)
                     # Should still have the original films even if scrape returned nothing (Append-Only)
                     self.assertEqual(output['items'][0]['mubi_id'], 1)
        finally:
            shutil.rmtree(test_dir)


if __name__ == '__main__':
    unittest.main()
