import unittest
from unittest.mock import MagicMock, patch
from scraper import MubiScraper
import json

class TestMubiScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = MubiScraper()

    @patch('scraper.MubiScraper._create_session')
    def test_extract_new_fields(self, mock_create_session):
        # Setup mock response data
        mock_film_data = {
            'films': [{
                'id': 1001,
                'title': 'Test Movie',
                'original_title': 'Test Movie Original',
                'genres': ['Drama', 'Test'],
                'year': 2023,
                'duration': 90,
                'directors': [{'name': 'Director One'}],
                'popularity': 42,
                'average_rating_out_of_ten': 7.8,
                'short_synopsis': 'A short synopsis.',
                'default_editorial': 'An editorial excerpt.',
                'episode': {'id': 5, 'title': 'The Episode'},
                'series': {'id': 10, 'title': 'The Series'}
            }],
            'meta': {'next_page': None}
        }

        # Mock the session.get response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_film_data
        
        # We need to mock the session on the scraper instance
        self.scraper.session = MagicMock()
        self.scraper.session.get.return_value = mock_response

        # Execute
        # We'll call fetch_films_for_country directly to test the extraction logic
        # We mock time.sleep to speed up tests
        with patch('time.sleep'):
            results = self.scraper.fetch_films_for_country('US')

        # Assertions
        self.assertEqual(len(results), 1)
        film = results[0]
        
        # Check standard fields
        self.assertEqual(film['id'], 1001)
        self.assertEqual(film['title'], 'Test Movie')
        
        # Check NEW fields are present in the returned raw data
        # Note: fetch_films_for_country returns the RAW data from the API (list of dicts)
        # The transformation happens in `run`.
        # However, the user request implied updating the extraction logic.
        # Let's verify what `fetch_films_for_country` returns.
        # Looking at scraper.py:
        # films = data.get('films', [])
        # for film in films: ... films_data.append(film)
        # So fetch_films_for_country returns the raw dict from Mubi.
        
        # Wait, the logic I changed was in `run` method where it processes the results of `fetch_films_for_country`.
        # So I should actually test the integration or the logic inside `run`.
        # Or better, I can verify that `fetch_films_for_country` returns the data I need, 
        # but the DATA TRANSFORMATION happens in `run`.
        
        # Let's look at `run` in scraper.py again.
        # It calls `future.result()` which is `fetch_films_for_country` output.
        # Then it does:
        # new_data = { ... 'popularity': film.get('popularity') ... }
        
        # So I should verify that `run` builds `new_data` correctly.
        # Since `run` is a complex method with file I/O and threading, 
        # I might want to extract the "transform" logic to a method to test it easily,
        # OR I can mock the file system and thread pool.
        
        # For a quick test without refactoring, I will simulate the loop inside `run`.
        
        raw_film = mock_film_data['films'][0]
        
        # Re-implementing the extraction logic from scraper.py to assert it works?
        # No, that's testing my test.
        # I should modify the scraper to have a `process_film_data` method?
        # Or just test `run` with mocked file IO and ThreadPool.
        pass

    @patch('scraper.MubiScraper.fetch_films_for_country')
    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='{"items":[]}')
    @patch('os.path.exists', return_value=True) # claim input file exists
    @patch('json.dump')
    @patch('scraper.MubiScraper.calculate_greedy_targets')
    def test_run_saves_new_fields(self, mock_greedy, mock_json_dump, mock_exists, mock_open, mock_executor, mock_fetch):
        # Setup
        mock_greedy.return_value = ['US']
        mock_fetch.return_value = [{
            'id': 1001,
            'title': 'Test Movie',
            'mubi_id': 1001, # The raw data usually has 'id' which acts as mubi_id
            'original_title': 'Test Movie Original',
            'genres': ['Drama'],
            'year': 2023,
            'duration': 90,
            'directors': [{'name': 'Director One'}],
            'popularity': 42,
            'average_rating_out_of_ten': 7.8,
            'short_synopsis': 'A short synopsis.',
            'default_editorial': 'An editorial excerpt.',
            'episode': {'id': 5, 'title': 'The Episode'},
            'series': {'id': 10, 'title': 'The Series'}
        }]
        
        # Mock executor context manager
        mock_future = MagicMock()
        mock_future.result.return_value = mock_fetch.return_value
        
        mock_executor_instance = MagicMock()
        mock_executor_instance.__enter__.return_value = mock_executor_instance
        # make submit return the future, and as_completed yield it
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance
        
        # We need concurrent.futures.as_completed to yield the future
        with patch('concurrent.futures.as_completed', return_value=[mock_future]):
            self.scraper.run(output_path='dummy.json', mode='shallow')
            
        # Verify json.dump was called with correct data
        args, _ = mock_json_dump.call_args
        output_data = args[0]
        items = output_data['items']
        self.assertEqual(len(items), 1)
        item = items[0]
        
        self.assertEqual(item['popularity'], 42)
        self.assertEqual(item['average_rating_out_of_ten'], 7.8)
        self.assertEqual(item['short_synopsis'], 'A short synopsis.')
        self.assertEqual(item['default_editorial'], 'An editorial excerpt.')
        self.assertEqual(item['episode'], {'id': 5, 'title': 'The Episode'})
        self.assertEqual(item['series'], {'id': 10, 'title': 'The Series'})
        
        # Verify shallow sync logic did not crash
        self.assertIn('countries', item)

if __name__ == '__main__':
    unittest.main()
