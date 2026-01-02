
import pytest
from unittest.mock import MagicMock
from backend.rating_calculator import BayesianRatingCalculator

def test_bayesian_rating_idempotency():
    """
    Test that running the BayesianRatingCalculator multiple times on the same item
    does not recursively inflate the vote count by including previous 'bayesian' ratings.
    """
    # Setup mock item with standard ratings
    item = {
        "title": "Test Movie",
        "ratings": [
            {"source": "mubi", "score_over_10": 9.0, "voters": 100},
            {"source": "imdb", "score_over_10": 8.0, "voters": 1000},
            {"source": "tmdb", "score_over_10": 7.5, "voters": 500},
        ]
    }
    
    expected_voters = 100 + 1000 + 500 # 1600
    
    # Initialize Calculator
    calc = BayesianRatingCalculator("dummy_path")
    calc.items = [item]
    
    # Mock I/O and dependencies
    calc.load_data = MagicMock()
    calc.save_data = MagicMock()
    # Mock constants to ensure stability (C=7.0, m=100)
    calc.get_constants = MagicMock(return_value=(7.0, 100.0))
    calc.calculate_new_constants = MagicMock(return_value=(7.0, 100.0))
    
    # --- Run 1 ---
    calc.run()
    
    # Verify first run results
    ratings_1 = item['ratings']
    bayesian_1 = next((r for r in ratings_1 if r['source'] == 'bayesian'), None)
    
    assert bayesian_1 is not None, "Bayesian rating should be generated"
    assert bayesian_1['voters'] == expected_voters, f"Expected {expected_voters} voters, got {bayesian_1['voters']}"
    
    # --- Run 2 ---
    # Running again on the same 'item' object which now contains the 'bayesian' rating from Run 1.
    calc.run()
    
    # Verify second run results
    ratings_2 = item['ratings']
    bayesian_2 = next((r for r in ratings_2 if r['source'] == 'bayesian'), None)
    
    assert bayesian_2 is not None
    # This is the critical check: voters should NOT increase
    assert bayesian_2['voters'] == expected_voters, \
        f"Regression detected: Voters increased from {expected_voters} to {bayesian_2['voters']}"

    # Verify score consistency
    assert bayesian_2['score_over_10'] == bayesian_1['score_over_10'], \
        f"Regression detected: Score changed from {bayesian_1['score_over_10']} to {bayesian_2['score_over_10']}"

    # Verify we didn't end up with duplicate bayesian entries
    bayesian_entries = [r for r in ratings_2 if r['source'] == 'bayesian']
    assert len(bayesian_entries) == 1, "Should have exactly one bayesian rating entry"
