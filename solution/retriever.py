"""
Retriever for P5 - Report Navigator.
Performs query analysis, entity recognition, intent classification,
and routes to the best matching document section or table.
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from rapidfuzz import fuzz

class QueryAnalysis:
    def __init__(self, question: str, default_year: int = 2023):
        self.raw_question = question
        self.clean_question = question.strip()
        self.lower = question.lower()
        self.year = self._extract_year(default_year)
        self.metric = self._extract_metric()
        self.entity_type = None
        self.extracted_entity = self._extract_candidate_entity()
        self._analyze()

    def _extract_year(self, default_year: int) -> int:
        match = re.search(r"\b(20[12]\d)\b", self.lower)
        if match:
            return int(match.group(1))
        return default_year

    def _extract_metric(self) -> str:
        if any(w in self.lower for w in ["killed", "death", "deaths", "fatalities", "fatality", "lives"]):
            return "killed"
        if any(w in self.lower for w in ["injured", "injuries", "injury", "hurt"]):
            return "injured"
        if any(w in self.lower for w in ["accident", "accidents", "crashes", "incidents"]):
            return "accidents"
        return "count"

    def _extract_candidate_entity(self) -> Optional[str]:
        # Extract candidate proper noun / entity following "in", "attributed to", or before "city"
        m1 = re.search(r"in\s+([A-Za-z\s&]+?)(?:\s+city|\s+in\s+20|\s+during\s+20|\?|$)", self.clean_question)
        if m1:
            cand = m1.group(1).strip()
            if cand.lower() not in ["road", "total", "india", "fatal", "accidents", "the"]:
                return cand

        m2 = re.search(r"attributed to ['\"]([^'\"]+)['\"]", self.clean_question, re.IGNORECASE)
        if m2:
            return m2.group(1).strip()

        return None

    def _analyze(self):
        if ("two-wheeler" in self.lower or "two wheeler" in self.lower) and ("city" in self.lower or self.extracted_entity):
            self.entity_type = "city_twowheeler"
        elif "pedestrian" in self.lower and ("city" in self.lower or self.extracted_entity):
            self.entity_type = "city_pedestrian"
        elif "over-speeding" in self.lower and ("city" in self.lower or self.extracted_entity):
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
            self.entity_type = "general"

class Retriever:
    def __init__(self, table_extractor, pages_text: Dict[int, str]):
        self.table_extractor = table_extractor
        self.pages_text = pages_text

    def check_document_contains_evidence(self, query_text: str, full_document_text: str) -> bool:
        """
        Dynamically checks whether the key concept tokens exist in the report.
        Avoids hardcoding unanswerable topics.
        """
        q_lower = query_text.lower()
        # Extract meaningful content words (length >= 4)
        stop_words = {
            "what", "where", "when", "many", "much", "were", "reported", "occurred",
            "during", "road", "accident", "accidents", "city", "state", "total", "number",
            "killed", "death", "deaths", "injured", "injuries", "person", "persons",
            "from", "with", "have", "been", "that", "this", "about", "which", "type"
        }
        words = [w for w in re.findall(r"\b[a-z]{4,}\b", q_lower) if w not in stop_words and not w.isdigit()]
        if not words:
            return True

        # Check if at least one key noun/word appears in the document
        matched_words = [w for w in words if w in full_document_text]
        return len(matched_words) > 0

    def find_entity_in_dict(self, query_text: str, entity_dict: Dict[str, Any], threshold: float = 75.0) -> Optional[Tuple[str, Any, float]]:
        """
        Matches query text against entity dictionary keys using word boundary containment
        and rapidfuzz token similarity. Longer keys tested first.
        """
        best_match = None
        best_score = 0.0

        # Sort keys by length descending so "Allahabad (Prayagraj)" is tested before "Agra"
        sorted_items = sorted(entity_dict.items(), key=lambda x: -len(x[0]))

        GENERIC_STOPWORDS = {
            "city", "district", "town", "state", "states", "uts", "collision", 
            "accidents", "accident", "road", "type", "rule", "rules", "traffic", 
            "vehicle", "vehicles", "users", "user", "area", "plus"
        }

        for key, val in sorted_items:
            # Word-boundary containment check
            clean_key = re.sub(r"[()]", "", key).strip()
            if clean_key:
                # Check for either the full key or any of its non-generic constituent parts
                sub_parts = [p.strip().lower() for p in re.split(r"[\s/]+", clean_key) if len(p.strip()) >= 4]
                sub_parts = [p for p in sub_parts if p not in GENERIC_STOPWORDS]
                parts = [clean_key.lower()] + sub_parts
                
                matched_part = False
                for p in parts:
                    if re.search(rf"\b{re.escape(p)}\b", query_text, re.IGNORECASE):
                        matched_part = True
                        break
                if matched_part:
                    score = 100.0
                    return (key, val, score)

            # Token set ratio fuzzy match
            score = fuzz.token_set_ratio(key, query_text)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = (key, val, score)

        return best_match
