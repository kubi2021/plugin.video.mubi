import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
import os
import sys
import tempfile
import shutil

# Ensure backend can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.enrich_metadata import enrich_metadata
from backend.tmdb_provider import TMDBProvider, ExternalMetadataResult

class TestEnrichMetadata(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.films_path = os.path.join(self.test_dir, 'films.json')
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch.dict(os.environ, {'TMDB_API_KEY': 'fake_key'})
    @patch('backend.tmdb_provider.requests.get')
    def test_enrich_metadata_successful(self, mock_get):
        """Test that films without IDs are updated when matches are found."""
        # Setup initial JSON
        initial_data = {
            'items': [
                {'mubi_id': 1, 'title': 'Test Movie', 'year': 2020, 'directors': ['Test Director']}, # Missing IDs
                {'mubi_id': 2, 'title': 'Known Movie', 'imdb_id': 'tt123', 'tmdb_id': '456', 'ratings': [{'source': 'imdb', 'score_over_10': 7.5}]} # Has IDs and Rating
            ]
        }
        with open(self.films_path, 'w') as f:
            json.dump(initial_data, f)

        # Mock TMDB responses
        # 1. Config check
        mock_resp_config = MagicMock()
        mock_resp_config = MagicMock()
        mock_resp_config.status_code = 200
        
        mock_resp_genres = MagicMock()
        mock_resp_genres.status_code = 200
        mock_resp_genres.json.return_value = {"genres": []}
        
        # 2. Search response (success)
        mock_resp_search = MagicMock()
        mock_resp_search.status_code = 200
        mock_resp_search.json.return_value = {
            'results': [{'id': 999, 'release_date': '2020-01-01', 'title': 'Test Movie', 'original_title': 'Test Movie'}]
        }
        
        # 3. Details response (with IMDB)
        mock_resp_details = MagicMock()
        mock_resp_details.status_code = 200
        mock_resp_details.json.return_value = {
            'external_ids': {'imdb_id': 'tt999'},
            'id': 999,
            'runtime': 120,
            'vote_average': 8.0,
            'vote_count': 500,
            'title': 'Test Movie',
            'original_title': 'Test Movie',
            'credits': {
                'crew': [{'job': 'Director', 'name': 'Test Director'}]
            }
        }
        
        # 0. Genre fetch responses (movie, tv) for __init__
        mock_resp_genres = MagicMock()
        mock_resp_genres.status_code = 200
        mock_resp_genres.json.return_value = {"genres": [{"id": 28, "name": "Action"}]}

        # 0. Genre fetch responses (movie, tv) for __init__
        mock_resp_genres = MagicMock()
        mock_resp_genres.status_code = 200
        mock_resp_genres.json.return_value = {"genres": [{"id": 28, "name": "Action"}]}

        # Side effect sequence
        mock_get.side_effect = [
            mock_resp_genres, # init movie genres
            mock_resp_genres, # init tv genres
            mock_resp_config, # test_connection
            mock_resp_search, # search for "Test Movie"
            mock_resp_details, # details for ID 999
            mock_resp_details # Safety buffer
        ]
        
        # We need to mock get_imdb_id on the provider instance, NOT requests.get for search
        # because enrich_metadata calls provider.get_imdb_id directly.
        # But wait, the test is mocking requests.get, meaning it tests the integration of enrich->provider->requests.
        # The error "'int' object has no attribute 'success'" implies something in enrich_metadata 
        # is receiving an int where it expects an object with .success.
        # enrich_metadata calls provider.get_imdb_id(). 
        # In the test setup, we are patching requests.get, so the real Provider code runs.
        # The real provider code now returns ExternalMetadataResult.
        # However, we mocked `tmdb_provider.TMDBProvider` class in `test_enrich_metadata_successful`? NO.
        # We are testing `enrich_metadata` which uses `TMDBProvider`.
        # Ah, looking at `enrich_metadata.py`: `result = provider.get_imdb_id(...)`.
        # If the real provider is used, it returns ExternalMetadataResult.
        # BUT, if the test is mocking `TMDBProvider`, we need to update the mock return value.
        
        # Let's check the test file content again.
        # The test uses `patch('backend.enrich_metadata.TMDBProvider')`.
        # So `provider` is a Mock object.
        # `provider.get_imdb_id` must return an object with `.success`.

        
        enrich_metadata(self.films_path)
        
        # Verify
        with open(self.films_path, 'r') as f:
            data = json.load(f)
            
        # Movie 1 should be updated
        self.assertEqual(data['items'][0]['imdb_id'], 'tt999')
        self.assertEqual(data['items'][0]['tmdb_id'], '999')
        
        # Movie 2 should be unchanged
        self.assertEqual(data['items'][1]['imdb_id'], 'tt123')

    @patch.dict(os.environ, {'TMDB_API_KEY': 'fake_key'})
    @patch('backend.tmdb_provider.requests.get')
    def test_enrich_metadata_no_match(self, mock_get):
        """Test behavior when no match is found."""
        initial_data = {
            'items': [{'mubi_id': 1, 'title': 'Unknown Movie', 'directors': ['Unknown Director']}]
        }
        with open(self.films_path, 'w') as f:
            json.dump(initial_data, f)
            
        mock_resp_config = MagicMock()
        mock_resp_config.status_code = 200
        
        # Search returns empty results
        mock_resp_search = MagicMock()
        mock_resp_search.status_code = 200
        mock_resp_search.json.return_value = {'results': []}
        
        mock_resp_genres = MagicMock()
        mock_resp_genres.status_code = 200
        mock_resp_genres.json.return_value = {"genres": []}
        
        mock_get.side_effect = [
            mock_resp_genres, # init
            mock_resp_genres, # init
            mock_resp_config, 
            mock_resp_search
        ]
        
        enrich_metadata(self.films_path)
        
        with open(self.films_path, 'r') as f:
            data = json.load(f)
            
        self.assertNotIn('imdb_id', data['items'][0])
        self.assertNotIn('tmdb_id', data['items'][0])

    @patch.dict(os.environ, {})
    def test_exit_if_no_api_key(self):
        """Should exit if TMDB_API_KEY is not set."""
        with self.assertRaises(SystemExit) as cm:
            enrich_metadata(self.films_path)
        self.assertEqual(cm.exception.code, 1)

    @patch.dict(os.environ, {'TMDB_API_KEY': 'fake_key'})
    @patch('backend.tmdb_provider.requests.get')
    def test_enrich_metadata_creates_ratings_array(self, mock_get):
        """Test that ratings array is created with Mubi and TMDB ratings."""
        # Setup initial JSON with Mubi rating data
        initial_data = {
            'items': [{
                'mubi_id': 1,
                'title': 'Test Movie',
                'year': 2020,
                'directors': ['Test Director'],
                'average_rating_out_of_ten': 7.5,
                'number_of_ratings': 1000
            }]
        }
        with open(self.films_path, 'w') as f:
            json.dump(initial_data, f)

        # Mock TMDB responses
        mock_resp_config = MagicMock()
        mock_resp_config.status_code = 200
        
        mock_resp_search = MagicMock()
        mock_resp_search.status_code = 200
        mock_resp_search.json.return_value = {
            'results': [{'id': 999, 'release_date': '2020-01-01', 'title': 'Test Movie', 'original_title': 'Test Movie'}]
        }
        
        # Details response with rating data
        mock_resp_details = MagicMock()
        mock_resp_details.status_code = 200
        mock_resp_details.json.return_value = {
            'external_ids': {'imdb_id': 'tt999'},
            'id': 999,
            'runtime': 120,
            'vote_average': 8.0,
            'vote_count': 500,
            'title': 'Test Movie',
            'original_title': 'Test Movie',
            'credits': {
                'crew': [{'job': 'Director', 'name': 'Test Director'}]
            }
        }
        
        mock_resp_genres = MagicMock()
        mock_resp_genres.status_code = 200
        mock_resp_genres.json.return_value = {"genres": []}
        
        mock_get.side_effect = [
            mock_resp_genres, # init
            mock_resp_genres, # init
            mock_resp_config,
            mock_resp_search,
            mock_resp_details,
            mock_resp_details # Safety buffer
        ]
        
        enrich_metadata(self.films_path)
        
        # Verify ratings array
        with open(self.films_path, 'r') as f:
            data = json.load(f)
        
        item = data['items'][0]
        self.assertIn('ratings', item)
        ratings = item['ratings']
        self.assertEqual(len(ratings), 2)
        
        # Check Mubi entry
        mubi_rating = next((r for r in ratings if r['source'] == 'mubi'), None)
        self.assertIsNotNone(mubi_rating)
        self.assertEqual(mubi_rating['score_over_10'], 7.5)
        self.assertEqual(mubi_rating['voters'], 1000)
        
        # Check TMDB entry
        tmdb_rating = next((r for r in ratings if r['source'] == 'tmdb'), None)
        self.assertIsNotNone(tmdb_rating)
        self.assertEqual(tmdb_rating['score_over_10'], 8.0)
        self.assertEqual(tmdb_rating['voters'], 500)

    @patch.dict(os.environ, {'TMDB_API_KEY': 'fake_key', 'OMDB_API_KEY': 'fake_omdb'})
    @patch('backend.enrich_metadata.OMDBProvider')
    @patch('backend.tmdb_provider.requests.get')
    def test_enrich_metadata_incorporates_omdb_ratings(self, mock_tmdb_get, MockOMDBProvider):
        """Test that OMDB ratings are fetched and added."""
        # Setup initial JSON
        initial_data = {
            'items': [{
                'mubi_id': 1,
                'title': 'Test Movie',
                'year': 2020,
                'directors': ['Test Director']
            }]
        }
        with open(self.films_path, 'w') as f:
            json.dump(initial_data, f)

        # Mock TMDB responses (standard success flow)
        mock_resp_config = MagicMock()
        mock_resp_config.status_code = 200
        mock_resp_search = MagicMock()
        mock_resp_search.status_code = 200
        mock_resp_search.json.return_value = {'results': [{'id': 999, 'release_date': '2020-01-01', 'title': 'Test Movie', 'original_title': 'Test Movie'}]}
        mock_resp_details = MagicMock()
        mock_resp_details.status_code = 200
        mock_resp_details.json.return_value = {
            'external_ids': {'imdb_id': 'tt999'},
            'id': 999,
            'runtime': 120,
            'vote_average': 8.0, 
            'vote_count': 500,
            'title': 'Test Movie',
            'original_title': 'Test Movie',
            'credits': {
                'crew': [{'job': 'Director', 'name': 'Test Director'}]
            }
        }
        mock_resp_genres = MagicMock()
        mock_resp_genres.status_code = 200
        mock_resp_genres.json.return_value = {"genres": []}

        mock_tmdb_get.side_effect = [
             mock_resp_genres, 
             mock_resp_genres, 
             mock_resp_config, 
             mock_resp_search, 
             mock_resp_details,
             mock_resp_details # Safety buffer
        ]

        # Mock OMDB Provider instance and response
        mock_omdb_instance = MockOMDBProvider.return_value
        mock_omdb_result = MagicMock()
        mock_omdb_result.success = True
        mock_omdb_result.extra_ratings = [
            {"source": "imdb", "score_over_10": 7.5, "voters": 1000},
            {"source": "rotten_tomatoes", "score_over_10": 9.0, "voters": 0}
        ]
        mock_omdb_instance.get_details.return_value = mock_omdb_result

        enrich_metadata(self.films_path)

        # Verify calls
        mock_omdb_instance.get_details.assert_called_with('tt999')

        # Verify Output
        with open(self.films_path, 'r') as f:
            data = json.load(f)
        
        ratings = data['items'][0]['ratings']
        self.assertEqual(len(ratings), 3) # TMDB + IMDB + RT
        
        sources = sorted([r['source'] for r in ratings])
        self.assertEqual(sources, ['imdb', 'rotten_tomatoes', 'tmdb'])
        
        rt = next(r for r in ratings if r['source'] == 'rotten_tomatoes')
        self.assertEqual(rt['score_over_10'], 9.0)

if __name__ == '__main__':
    unittest.main()
