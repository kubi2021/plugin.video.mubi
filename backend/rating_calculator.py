import json
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class BayesianRatingCalculator:
    """
    Calculates composite ratings using a Bayesian Average.
    
    Formula:
    W = (v / (v + m)) * R + (m / (v + m)) * C
    
    Where:
    W = Weighted Rating
    R = Average computed Rating for the item (Mean of scores from sources)
    v = Total number of votes for the item
    m = Minimum votes required (Confidence Threshold, derived from Mubi avg votes)
    C = Global Mean vote across the whole report
    """
    
    DEFAULT_C = 6.9
    
    def __init__(self, films_path: str, history_path: Optional[str] = None):
        self.films_path = films_path
        self.history_path = history_path
        self.data: Dict[str, Any] = {}
        self.items: List[Dict[str, Any]] = []
        self.bayes_stats: Dict[str, float] = {}
        
    def load_data(self):
        with open(self.films_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.items = self.data.get('items', [])
        
        # Load existing stats if available (Warm Start)
        # Priority 1: Current file (if it has stats)
        # Priority 2: History file (if provided)
        if self.data.get('bayes_stats'):
             self.bayes_stats = self.data.get('bayes_stats')
             logger.info(f"Warm Start: Found stats in current file: {self.bayes_stats}")
        elif self.history_path:
            import os
            logger.info(f"Attempting Warm Start from history file: {self.history_path}")
            if not os.path.exists(self.history_path):
                logger.error(f"DEBUG: History file path '{self.history_path}' does NOT exist.")
                self.bayes_stats = {}
            else:
                try:
                    logger.info(f"DEBUG: Opening history file at {os.path.abspath(self.history_path)}")
                    with open(self.history_path, 'r', encoding='utf-8') as f:
                        hist_data = json.load(f)
                        
                    keys = list(hist_data.keys())
                    logger.info(f"DEBUG: History file keys: {keys}")
                    
                    if 'bayes_stats' in hist_data:
                        self.bayes_stats = hist_data.get('bayes_stats', {})
                        logger.info(f"DEBUG: Successfully loaded history stats: {self.bayes_stats}")
                    else:
                        logger.warning("DEBUG: 'bayes_stats' key missing in history file!")
                        self.bayes_stats = {}
                        
                except Exception as e:
                    logger.warning(f"Failed to load history file: {e}. Proceeding with Cold Start.")
                    self.bayes_stats = {}
        else:
             logger.info("No history file provided. Cold Start.")
             self.bayes_stats = {}
        
    def save_data(self):
        self.data['items'] = self.items
        self.data['bayes_stats'] = self.bayes_stats
        with open(self.films_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
            
    def get_constants(self) -> Tuple[float, float]:
        """
        Determine C (Global Mean) and m (Confidence Threshold).
        Logic:
        - Cold Start: Use Default C, Calculate m from current Mubi votes.
        - Warm Start: Use stored C and m.
        """
        c_val = self.bayes_stats.get('global_mean_C')
        m_val = self.bayes_stats.get('mubi_confidence_m')
        
        if c_val is not None and m_val is not None:
            logger.info(f"Warm Start: Using stored constants C={c_val}, m={m_val}")
            return c_val, m_val
            
        logger.info("Cold Start: Calculating initial constants...")
        # Start with default C
        c_val = self.DEFAULT_C
        
        # Calculate m from Mubi votes
        total_mubi_votes = 0
        count = 0
        for item in self.items:
            mubi_rating = self._get_rating_by_source(item, 'mubi')
            if mubi_rating:
                votes = mubi_rating.get('voters', 0)
                total_mubi_votes += votes
                count += 1
                
        m_val = total_mubi_votes / count if count > 0 else 0
        
        logger.info(f"Cold Start: Calculated m={m_val} (from {count} films), using Default C={c_val}")
        return c_val, m_val

    def _get_rating_by_source(self, item: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        ratings = item.get('ratings', [])
        for r in ratings:
            if r.get('source') == source:
                return r
        return None

    def calculate_raw_metrics(self, item: Dict[str, Any]) -> Tuple[float, int]:
        """
        Calculate R (Raw Average) and v (Total Votes) from all sources.
        """
        ratings = item.get('ratings', [])
        if not ratings:
            return 0.0, 0
            
        total_weighted_score = 0.0
        total_votes = 0
        
        for r in ratings:
            try:
                score = float(r.get('score_over_10', 0))
                votes = int(r.get('voters', 0))
                
                # Exclude invalid data (0 votes usually means no data for aggregation purposes)
                if votes > 0:
                    total_weighted_score += (score * votes)
                    total_votes += votes
            except (ValueError, TypeError):
                continue
                
        if total_votes == 0:
            return 0.0, 0
            
        raw_average = total_weighted_score / total_votes
        return raw_average, total_votes

    def calculate_new_constants(self) -> Tuple[float, float]:
        """
        Recalculate C and m after processing for next run.
        C = Average of all R_raw
        m = Average of Mubi votes
        """
        total_r_raw = 0.0
        total_mubi_votes = 0
        count_r = 0
        count_mubi = 0
        
        for item in self.items:
            # Re-calculate these on the fly or could assume they are fresh
            r_raw, _ = self.calculate_raw_metrics(item)
            if r_raw > 0:
                total_r_raw += r_raw
                count_r += 1
                
            mubi_rating = self._get_rating_by_source(item, 'mubi')
            if mubi_rating:
                 votes = mubi_rating.get('voters', 0)
                 total_mubi_votes += votes
                 count_mubi += 1
        
        new_c = total_r_raw / count_r if count_r > 0 else self.DEFAULT_C
        new_m = total_mubi_votes / count_mubi if count_mubi > 0 else 0.0
        
        return new_c, new_m

    def run(self):
        self.load_data()
        
        C, m = self.get_constants()
        
        updated_count = 0
        for item in self.items:
            R_raw, v_total = self.calculate_raw_metrics(item)
            
            if v_total == 0:
                # Remove any stale bayesian rating
                item['ratings'] = [r for r in item.get('ratings', []) if r.get('source') != 'bayesian']
                # Optionally add a 0-value rating or just skip. 
                # User prompted "bayesian rating can just be one of the rating", usually 0 votes means no rating object.
                # Let's skip adding it if 0 votes, but ensure cleanup.
                item.pop('bayesian_rating', None)
                item.pop('total_votes', None)
                continue
            
            # Bayesian Formula
            # W = (v / (v + m)) * R + (m / (v + m)) * C
            weight_v = v_total / (v_total + m)
            weight_m = m / (v_total + m)
            
            W = (weight_v * R_raw) + (weight_m * C)
            
            # Remove existing bayesian rating if present
            item['ratings'] = [r for r in item.get('ratings', []) if r.get('source') != 'bayesian']
            
            # Add new bayesian rating
            item['ratings'].append({
                "source": "bayesian",
                "score_over_10": round(W, 1),
                "voters": v_total
            })
            
            # Legacy field cleanup (if we want to ensure they are gone, though schema validation might strip them)
            item.pop('bayesian_rating', None)
            item.pop('total_votes', None)
            
            updated_count += 1
            
        # Update calibration for next run
        new_c, new_m = self.calculate_new_constants()
        self.bayes_stats = {
            "global_mean_C": round(new_c, 2),
            "mubi_confidence_m": round(new_m, 2)
        }
        
        logger.info(f"Bayesian Rating Compete. Processed {len(self.items)} items. New Stats: {self.bayes_stats}")
        self.save_data()

if __name__ == "__main__":
    import sys
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Bayesian Rating Calculator")
    parser.add_argument('films_path', help="Path to films.json")
    parser.add_argument('--history-file', help="Path to previous films.json for warm start stats", default=None)
    
    args = parser.parse_args()
        
    calc = BayesianRatingCalculator(args.films_path, history_path=args.history_file)
    calc.run()
