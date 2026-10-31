"""
Answer Extractor for P5 - Report Navigator.
Extracts exact numerical answers and page numbers based on query semantics,
dynamic table coordinates, and text search.
"""
import re
from typing import Dict, Any, Tuple, Optional
from rapidfuzz import fuzz

from retriever import QueryAnalysis, Retriever
from confidence import ConfidenceEstimator

class AnswerExtractor:
    def __init__(self, table_extractor, pages_text: Dict[int, str], default_year: int = 2023):
        self.table_extractor = table_extractor
        self.pages_text = pages_text
        self.default_year = default_year
        self.retriever = Retriever(table_extractor, pages_text)
        self.confidence_estimator = ConfidenceEstimator()
        self._full_doc_text = " ".join(pages_text.values()).lower()

    def extract_answer(self, query_obj: Dict[str, Any]) -> Dict[str, Any]:
        q_id = query_obj.get("id", "")
        q_text = query_obj.get("question", "")
        analysis = QueryAnalysis(q_text, default_year=self.default_year)
        q_lower = analysis.lower
        target_year = analysis.year

        # 1. Document Evidence Check (Dynamic unanswerable detection)
        if not self.retriever.check_document_contains_evidence(q_text, self._full_doc_text):
            return {
                "id": q_id,
                "answer": "NOT_FOUND",
                "page": None,
                "confidence": self.confidence_estimator.calculate("abstain")
            }

        # 2. City: Two-wheeler riders killed
        if ("two-wheeler" in q_lower or "two wheeler" in q_lower) and ("killed" in q_lower or "death" in q_lower):
            tbl = self.table_extractor.tables.get("city_impacting_vehicles")
            if tbl:
                match = self.retriever.find_entity_in_dict(q_lower, tbl["records"])
                if match:
                    key, data, score = match
                    ans = data.get("twowheelers_killed")
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 3. City: Pedestrian killed
        if "pedestrian" in q_lower and ("killed" in q_lower or "death" in q_lower):
            tbl = self.table_extractor.tables.get("city_impacting_vehicles")
            if tbl:
                match = self.retriever.find_entity_in_dict(q_lower, tbl["records"])
                if match:
                    key, data, score = match
                    ans = data.get("pedestrians_killed")
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 4. City: Over-speeding deaths
        if "over-speeding" in q_lower and ("killed" in q_lower or "death" in q_lower):
            tbl = self.table_extractor.tables.get("city_traffic_violations")
            if tbl:
                match = self.retriever.find_entity_in_dict(q_lower, tbl["records"])
                if match:
                    key, data, score = match
                    ans = data.get("overspeeding_killed")
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 5. City: Summary accidents, killed, injured (Table 6.2)
        # Check if the query asks about a city
        tbl_city = self.table_extractor.tables.get("city_summary")
        if tbl_city:
            match = self.retriever.find_entity_in_dict(q_lower, tbl_city["records"])
            if match:
                key, data, score = match
                year_to_use = target_year if target_year in tbl_city.get("years", []) else tbl_city.get("curr_year", self.default_year)
                ans = None
                if "injured" in q_lower or "injuries" in q_lower:
                    ans = data["injured"].get(year_to_use)
                elif "killed" in q_lower or "death" in q_lower or "fatalities" in q_lower:
                    ans = data["killed"].get(year_to_use)
                elif "accident" in q_lower or "crashes" in q_lower:
                    ans = data["accidents"].get(year_to_use)
                if ans:
                    return {
                        "id": q_id,
                        "answer": ans,
                        "page": tbl_city["page"],
                        "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                    }

        # If question asked specifically for a city but not matched in the city table
        if "city" in q_lower:
            return {
                "id": q_id,
                "answer": "NOT_FOUND",
                "page": None,
                "confidence": self.confidence_estimator.calculate("fallback_abstain")
            }

        # 6. State: Killed (Annexure 3)
        if "killed" in q_lower or "death" in q_lower or "fatalities" in q_lower:
            tbl_state_k = self.table_extractor.tables.get("state_killed")
            if tbl_state_k:
                match = self.retriever.find_entity_in_dict(q_lower, tbl_state_k["records"])
                if match:
                    key, data, score = match
                    year_to_use = target_year if target_year in tbl_state_k.get("years", []) else tbl_state_k.get("curr_year", self.default_year)
                    ans = data["killed_by_year"].get(year_to_use, data.get("latest"))
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl_state_k["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 7. State: Accidents (Annexure 2)
        if "accident" in q_lower:
            tbl_state_a = self.table_extractor.tables.get("state_accidents")
            if tbl_state_a:
                match = self.retriever.find_entity_in_dict(q_lower, tbl_state_a["records"])
                if match:
                    key, data, score = match
                    year_to_use = target_year if target_year in tbl_state_a.get("years", []) else tbl_state_a.get("curr_year", self.default_year)
                    ans = data["accidents_by_year"].get(year_to_use, data.get("latest"))
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl_state_a["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 8. Collision Type (Table 1.5)
        if "collision" in q_lower or "run off road" in q_lower or ("type" in q_lower and "others" in q_lower):
            tbl_col = self.table_extractor.tables.get("collision_types")
            if tbl_col:
                match = self.retriever.find_entity_in_dict(q_lower, tbl_col["records"])
                if match:
                    key, data, score = match
                    year_to_use = target_year if target_year in tbl_col.get("years", []) else tbl_col.get("curr_year", self.default_year)
                    if "killed" in q_lower or "death" in q_lower:
                        ans = data["killed"].get(year_to_use)
                    else:
                        ans = data["accidents"].get(year_to_use)
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl_col["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 9. Road User Categories (Table 4.4)
        if "road user" in q_lower or ("in india" in q_lower and any(v in q_lower for v in ["two-wheeler", "cars", "pedestrian", "buses", "trucks"])):
            tbl_ru = self.table_extractor.tables.get("road_users")
            if tbl_ru:
                ru_target = "two-wheelers" if "two-wheeler" in q_lower else ("cars" if "car" in q_lower else None)
                if ru_target and ru_target in tbl_ru["records"]:
                    year_to_use = target_year if target_year in tbl_ru.get("years", []) else tbl_ru.get("curr_year", self.default_year)
                    ans = tbl_ru["records"][ru_target]["killed"].get(year_to_use)
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl_ru["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", 100.0)
                        }

        # 10. National Violations / All India (Table 3.1)
        tbl_viol = self.table_extractor.tables.get("national_violations")
        if tbl_viol:
            year_to_use = target_year if target_year in tbl_viol.get("years", []) else tbl_viol.get("curr_year", self.default_year)
            if "mobile phone" in q_lower and "use of mobile phone" in tbl_viol["records"]:
                ans = tbl_viol["records"]["use of mobile phone"]["killed"].get(year_to_use)
                if ans:
                    return {
                        "id": q_id,
                        "answer": ans,
                        "page": tbl_viol["page"],
                        "confidence": self.confidence_estimator.calculate("exact_table_cell", 100.0)
                    }
            if "all india" in q_lower and ("killed" in q_lower or "death" in q_lower) and "all india" in tbl_viol["records"]:
                ans = tbl_viol["records"]["all india"]["killed"].get(year_to_use)
                if ans:
                    return {
                        "id": q_id,
                        "answer": ans,
                        "page": tbl_viol["page"],
                        "confidence": self.confidence_estimator.calculate("exact_table_cell", 100.0)
                    }

        # Default Abstain when not supported
        return {
            "id": q_id,
            "answer": "NOT_FOUND",
            "page": None,
            "confidence": self.confidence_estimator.calculate("fallback_abstain")
        }
