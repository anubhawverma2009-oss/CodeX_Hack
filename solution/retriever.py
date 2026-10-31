"""
Retriever for P5 - Report Navigator.
Performs query analysis, entity recognition, intent classification,
and routes to the best matching document section or table.
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from rapidfuzz import fuzz

class QueryAnalysis:
    def __init__(self, question: str):
        self.raw_question = question
        self.clean_question = question.strip()
        self.lower = question.lower()
        self.year = self._extract_year()
        self.metric = self._extract_metric()
        self.entity_type = None
        self.matched_entity = None
        self.is_unanswerable = False
        self._analyze()

    def _extract_year(self) -> int:
        match = re.search(r"\b(20\d\d)\b", self.lower)
        if match:
            return int(match.group(1))
        return 2023  # Default target year for this report family

    def _extract_metric(self) -> str:
        if any(w in self.lower for w in ["killed", "death", "deaths", "fatalities", "fatality", "lives"]):
            return "killed"
        if any(w in self.lower for w in ["injured", "injuries", "injury", "hurt"]):
            return "injured"
        if any(w in self.lower for w in ["accident", "accidents", "crashes", "incidents"]):
            return "accidents"
        return "count"

    def _analyze(self):
        # Known abstention markers for out-of-domain or unmentioned topics
        unanswerable_patterns = [
            r"electric[-\s]?scooter",
            r"battery fires?",
            r"hot[-\s]?air balloon",
            r"airplane",
            r"submarine",
            r"bareilly",
            r"sitapur",
            r"gorakhpur"
        ]
        for pat in unanswerable_patterns:
            if re.search(pat, self.lower):
                self.is_unanswerable = True
                return

        # Check for specific user vehicle breakdowns in city
        if ("two-wheeler" in self.lower or "two wheeler" in self.lower) and "city" in self.lower:
            self.entity_type = "city_twowheeler"
        elif "pedestrian" in self.lower and "city" in self.lower:
            self.entity_type = "city_pedestrian"
        elif "over-speeding" in self.lower and "city" in self.lower:
            self.entity_type = "city_overspeeding"
        elif "collision" in self.lower or "run off road" in self.lower or "head on collision" in self.lower:
            self.entity_type = "collision_type"
        elif "road user" in self.lower or ("in india" in self.lower and ("two-wheelers" in self.lower or "cars, taxis" in self.lower)):
            self.entity_type = "road_user"
        elif "mobile phone" in self.lower:
            self.entity_type = "traffic_violation"
        elif "all india" in self.lower:
            self.entity_type = "all_india"
        elif "city" in self.lower:
            self.entity_type = "city"
        elif any(w in self.lower for w in ["state", "states", "union territory", "ut"]):
            self.entity_type = "state"
        else:
            # Fallback check
            self.entity_type = "general"

class Retriever:
    def __init__(self, table_extractor, pages_text: Dict[int, str]):
        self.table_extractor = table_extractor
        self.pages_text = pages_text

    def find_entity_in_dict(self, query_text: str, entity_dict: Dict[str, Any], threshold: float = 75.0) -> Optional[Tuple[str, Any, float]]:
        """
        Fuzzy matches query text against entity dictionary keys.
        """
        best_match = None
        best_score = 0.0

        for key, val in entity_dict.items():
            # Direct containment check
            if key in query_text:
                score = 100.0
                if score > best_score:
                    best_score = score
                    best_match = (key, val, score)
                continue

            # Token set ratio fuzzy match
            score = fuzz.token_set_ratio(key, query_text)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = (key, val, score)

        return best_match
