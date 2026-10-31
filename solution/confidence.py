"""
Confidence Estimation for P5 - Report Navigator.
Calibrates prediction confidence based on retrieval evidence and match score.
"""

class ConfidenceEstimator:
    @staticmethod
    def calculate(match_type: str, match_score: float = 100.0) -> float:
        """
        Calculates a calibrated confidence score between 0.0 and 1.0.
        """
        if match_type == "exact_table_cell":
            base = 0.98
            # Scale slightly with fuzzy match quality
            adjustment = min(1.0, match_score / 100.0)
            return round(base * adjustment, 2)
        elif match_type == "text_regex":
            return 0.88
        elif match_type == "abstain":
            return 0.95
        elif match_type == "fallback_abstain":
            return 0.90
        return 0.50
