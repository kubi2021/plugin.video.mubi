import unittest
import json
import tempfile
import shutil
import os
from backend.rating_calculator import BayesianRatingCalculator

class TestBayesianRatingCalculator(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.films_path = os.path.join(self.test_dir, 'films.json')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_dummy_data(self, items, stats=None):
        data = {'items': items}
        if stats:
            data['bayes_stats'] = stats
        with open(self.films_path, 'w') as f:
            json.dump(data, f)
            
    def test_cold_start_constants(self):
        """Test calculation of m and usage of default C on cold start."""
        items = [
            # 10 votes
            {'ratings': [{'source': 'mubi', 'voters': 10, 'score_over_10': 8.0}]},
            # 20 votes
            {'ratings': [{'source': 'mubi', 'voters': 20, 'score_over_10': 6.0}]},
        ]
        self.create_dummy_data(items)
        
        calc = BayesianRatingCalculator(self.films_path)
        calc.load_data()
        
        C, m = calc.get_constants()
        
        self.assertEqual(C, 6.9) # Default
        self.assertEqual(m, 15.0) # (10+20)/2

    def test_warm_start_constants(self):
        """Test usage of stored constants."""
        stats = {'global_mean_C': 7.5, 'mubi_confidence_m': 100.0}
        self.create_dummy_data([], stats=stats)
        
        calc = BayesianRatingCalculator(self.films_path)
        calc.load_data()
        
        C, m = calc.get_constants()
        self.assertEqual(C, 7.5)
        self.assertEqual(m, 100.0)

    def test_calculation_logic(self):
        """Test the full bayesian formula application."""
        # Stats: m=10, C=5.0
        # Item: 10 votes (mubi only), score 10.0
        # v=10, m=10 -> weights are 0.5 and 0.5
        # R=10.0
        # W = 0.5 * 10.0 + 0.5 * 5.0 = 5.0 + 2.5 = 7.5
        
        stats = {'global_mean_C': 5.0, 'mubi_confidence_m': 10.0}
        items = [
            {
                'title': 'Test Movie',
                'ratings': [{'source': 'mubi', 'voters': 10, 'score_over_10': 10.0}]
            }
        ]
        self.create_dummy_data(items, stats)
        
        calc = BayesianRatingCalculator(self.films_path)
        calc.run()
        
        with open(self.films_path, 'r') as f:
            data = json.load(f)
            
        item = data['items'][0]
        bayes_rating = next((r for r in item['ratings'] if r['source'] == 'bayesian'), None)
        self.assertIsNotNone(bayes_rating)
        self.assertEqual(bayes_rating['score_over_10'], 7.5)
        self.assertEqual(bayes_rating['voters'], 10)

    def test_multi_source_aggregation(self):
        """Test aggregation of votes from multiple sources."""
        stats = {'global_mean_C': 7.0, 'mubi_confidence_m': 20.0}
        items = [
            {
                'ratings': [
                    {'source': 'mubi', 'voters': 10, 'score_over_10': 8.0},
                    {'source': 'tmdb', 'voters': 10, 'score_over_10': 6.0}
                ]
            }
        ]
        self.create_dummy_data(items, stats)
        
        calc = BayesianRatingCalculator(self.films_path)
        calc.run()
        
        with open(self.films_path, 'r') as f:
            data = json.load(f)
            
        item = data['items'][0]
        bayes_rating = next((r for r in item['ratings'] if r['source'] == 'bayesian'), None)
        self.assertIsNotNone(bayes_rating)
        self.assertEqual(bayes_rating['score_over_10'], 7.0)
        self.assertEqual(bayes_rating['voters'], 20)

    def test_zero_votes(self):
        items = [{'ratings': []}]
        self.create_dummy_data(items)
        calc = BayesianRatingCalculator(self.films_path)
        calc.run()
        
        with open(self.films_path, 'r') as f:
            data = json.load(f)
            
        item = data['items'][0]
        # Should NOT have a bayesian rating if 0 votes
        bayes_rating = next((r for r in item.get('ratings', []) if r['source'] == 'bayesian'), None)
        self.assertIsNone(bayes_rating)

    def test_metadata_update(self):
        """Test that new constants are saved."""
        items = [
             {'ratings': [{'source': 'mubi', 'voters': 10, 'score_over_10': 8.0}]},
             {'ratings': [{'source': 'mubi', 'voters': 10, 'score_over_10': 6.0}]}
        ]
        self.create_dummy_data(items)
        
        calc = BayesianRatingCalculator(self.films_path)
        calc.run()
        
        with open(self.films_path, 'r') as f:
            data = json.load(f)
            
        stats = data['bayes_stats']
        self.assertEqual(stats['global_mean_C'], 7.0)
        self.assertEqual(stats['mubi_confidence_m'], 10.0)

    def test_formula_scenarios(self):
        """
        Verify Bayesian formula output against varied scenarios.
        Formula: W = (v / (v + m)) * R + (m / (v + m)) * C
        """
        scenarios = [
            # description, v, R, C, m, expected
            ("Equal Weight", 100, 8.0, 6.0, 100.0, 7.0),
            ("Low Confidence (Msg)", 10, 10.0, 5.0, 90.0, 5.5),
            ("High Confidence (Msg)", 90, 10.0, 5.0, 10.0, 9.5),
            ("Extreme Zero Score", 50, 0.0, 10.0, 50.0, 5.0),
        ]

        for desc, v, R, C, m, expected in scenarios:
            with self.subTest(msg=desc, v=v, R=R, C=C, m=m):
                # Setup data
                stats = {'global_mean_C': C, 'mubi_confidence_m': m}
                items = [{
                    'title': 'Test',
                    'ratings': [{'source': 'test', 'voters': v, 'score_over_10': R}]
                }]
                self.create_dummy_data(items, stats)
                
                # Run
                calc = BayesianRatingCalculator(self.films_path)
                calc.run()
                
                # Verify
                with open(self.films_path, 'r') as f:
                    data = json.load(f)
                
                item = data['items'][0]
                # Find bayesian rating
                bayes = next((r for r in item['ratings'] if r['source'] == 'bayesian'), None)
                
                self.assertIsNotNone(bayes, f"Bayesian rating missing for {desc}")
                self.assertAlmostEqual(bayes['score_over_10'], expected, places=1)
                self.assertEqual(bayes['voters'], v)

if __name__ == '__main__':
    unittest.main()
