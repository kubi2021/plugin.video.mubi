
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

from backend.enrich_metadata import enrich_metadata

class TestEnrichMetadataOMDBLogic(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.films_path = os.path.join(self.test_dir, 'films.json')
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch.dict(os.environ, {'TMDB_API_KEY': 'fake_tmdb', 'OMDB_API_KEYS': 'fake_omdb'})
    @patch('backend.enrich_metadata.OMDBProvider')
    @patch('backend.enrich_metadata.TMDBProvider')  # Mock the class itself
    def test_omdb_call_conditions(self, MockTMDBProvider, MockOMDBProvider):
        """
        Verify OMDB call logic:
        1. NO call if IMDB ID is missing (even if TMDB ID exists).
        2. NO call if IMDB ID exists AND IMDB rating exists.
        3. CALL if IMDB ID exists AND IMDB rating is missing.
        """
        
        # Setup Input Data
        items = [
            # Case 1: TMDB ID exists, IMDB ID missing. Should SKIP OMDB.
            {
                'mubi_id': 1, 
                'title': 'No IMDB ID', 
                'year': 2020, 
                'tmdb_id': '1001',
                # imdb_id missing
                'ratings': []
            },
            # Case 2: TMDB ID exists, IMDB ID exists, IMDB Rating exists. Should SKIP OMDB.
            {
                'mubi_id': 2, 
                'title': 'Has Rating', 
                'year': 2020, 
                'tmdb_id': '1002', 
                'imdb_id': 'tt1002',
                'ratings': [{'source': 'imdb', 'score_over_10': 7.0}]
            },
            # Case 3: TMDB ID exists, IMDB ID exists, IMDB Rating MISSING. Should CALL OMDB.
            {
                'mubi_id': 3, 
                'title': 'Need Rating', 
                'year': 2020, 
                'tmdb_id': '1003', 
                'imdb_id': 'tt1003',
                'ratings': [{'source': 'tmdb', 'score_over_10': 8.0}] # TMDB rating only
            }
        ]
        
        with open(self.films_path, 'w') as f:
            json.dump({'items': items}, f)

        # Setup Mocks
        mock_tmdb_instance = MockTMDBProvider.return_value
        mock_tmdb_instance.test_connection.return_value = True
        
        # We need mock_tmdb_instance.get_imdb_id to return valid results 
        # so process_film continues to OMDB logic.
        # process_film calls provider.get_imdb_id(...).
        
        def get_imdb_id_side_effect(*args, **kwargs):
            # Parse arguments or rely on kwargs if called with kwargs. 
            # In enrich_metadata: provider.get_imdb_id(title, original_title=..., mubi_id=...)
            # mubi_id is a keyword arg.
            mubi_id = kwargs.get('mubi_id')
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.vote_average = None # Don't add new TMDB ratings logic for simplicity
            
            if mubi_id == 3:
                # For the one we want to process
                mock_res.imdb_id = 'tt1003'
                mock_res.tmdb_id = '1003'
            
            return mock_res

        mock_tmdb_instance.get_imdb_id.side_effect = get_imdb_id_side_effect

        mock_omdb_instance = MockOMDBProvider.return_value
        mock_omdb_instance.api_keys = ['fake_omdb'] # Needed for check
        mock_omdb_instance.get_details.return_value.success = True
        mock_omdb_instance.get_details.return_value.extra_ratings = [{'source': 'imdb', 'score': 9.0}]

        # Execute
        enrich_metadata(self.films_path)
        
        # Verify Interactions
        
        # Case 1 & 2 should NOT have triggered process_film logic that calls OMDB
        # However, checking `get_details` calls is the ultimate proof.
        
        # We expect exactly ONE call to OMDB, for tt1003
        self.assertEqual(mock_omdb_instance.get_details.call_count, 1)
        mock_omdb_instance.get_details.assert_called_with('tt1003')
        
        # Explicit verification it was NOT called for others
        call_args_list = mock_omdb_instance.get_details.call_args_list
        called_ids = [c[0][0] for c in call_args_list]
        
        self.assertNotIn('tt1002', called_ids, "Should not call OMDB if rating exists")
        # 'tt1001' doesn't exist so obviously not called, but logic holds.

if __name__ == '__main__':
    unittest.main()
