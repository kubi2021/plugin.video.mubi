import unittest
from unittest.mock import MagicMock, patch
import json
from backend.omdb_provider import OMDBProvider

class TestOMDBProvider(unittest.TestCase):

    def setUp(self):
        self.api_keys = ["key1", "key2", "key3"]
        self.provider = OMDBProvider(api_keys=self.api_keys)

    def test_init_single_key(self):
        p = OMDBProvider(api_keys="single_key")
        self.assertEqual(p.api_keys, ["single_key"])

    def test_init_list_keys(self):
        p = OMDBProvider(api_keys=["k1", "k2"])
        self.assertEqual(p.api_keys, ["k1", "k2"])
        
    def test_init_empty_keys_raises(self):
        with self.assertRaises(ValueError):
            OMDBProvider(api_keys=[])

    def test_key_rotation(self):
        # Check that keys cycle
        keys_used = []
        for _ in range(4):
            keys_used.append(self.provider._get_next_key())
        
        self.assertEqual(keys_used, ["key1", "key2", "key3", "key1"])

    @patch('requests.get')
    def test_get_details_success(self, mock_get):
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Response": "True",
            "imdbID": "tt1234567",
            "Title": "Test Movie",
            "imdbRating": "7.5",
            "imdbVotes": "1,000",
            "Ratings": [
                {"Source": "Internet Movie Database", "Value": "7.5/10"},
                {"Source": "Rotten Tomatoes", "Value": "80%"},
                {"Source": "Metacritic", "Value": "70/100"}
            ]
        }
        mock_get.return_value = mock_response

        result = self.provider.get_details("tt1234567")

        self.assertTrue(result.success)
        self.assertEqual(result.imdb_id, "tt1234567")
        
        # Verify ratings extraction and normalization
        ratings = getattr(result, 'extra_ratings', [])
        self.assertEqual(len(ratings), 3)
        
        # Check IMDB
        imdb = next(r for r in ratings if r["source"] == "imdb")
        self.assertEqual(imdb["score_over_10"], 7.5)
        self.assertEqual(imdb["voters"], 1000)
        
        # Check Rotten Tomatoes (80% -> 8.0)
        rt = next(r for r in ratings if r["source"] == "rotten_tomatoes")
        self.assertEqual(rt["score_over_10"], 8.0)
        
        # Check Metacritic (70/100 -> 7.0)
        mc = next(r for r in ratings if r["source"] == "metacritic")
        self.assertEqual(mc["score_over_10"], 7.0)
        
        # Verify correct key was passed (key is rotated)
        args, kwargs = mock_get.call_args
        self.assertIn("apikey", kwargs["params"])
        self.assertIn(kwargs["params"]["apikey"], self.api_keys)

    @patch('requests.get')
    def test_get_details_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Response": "False",
            "Error": "Movie not found!"
        }
        mock_get.return_value = mock_response
        
        result = self.provider.get_details("ttInvalid")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Movie not found!")

if __name__ == '__main__':
    unittest.main()
