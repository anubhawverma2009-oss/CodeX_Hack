"""
Answer Extractor for P5 - Report Navigator.
Extracts exact numerical answers and page numbers based on query semantics,
table coordinates, and text search.
"""
import re
from typing import Dict, Any, Tuple, Optional
from rapidfuzz import fuzz

from retriever import QueryAnalysis, Retriever
from confidence import ConfidenceEstimator

CITIES_LIST = [
    "Agra", "Ahmedabad", "Allahabad", "Prayagraj", "Amritsar", "Asansol Durgapur", "Aurangabad",
    "Bengaluru", "Bhopal", "Chandigarh", "Chennai", "Coimbatore", "Delhi", "Dhanbad",
    "Faridabad", "Ghaziabad", "Gwalior", "Hyderabad", "Indore", "Jabalpur", "Jaipur",
    "Jamshedpur", "Jodhpur", "Kannur", "Kanpur", "Khozikode", "Kochi", "Kolkata",
    "Kollam", "Kota", "Lucknow", "Ludhiana", "Madurai", "Mallapuram", "Meerut",
    "Mumbai", "Nagpur", "Nashik", "Patna", "Pune", "Raipur", "Rajkot", "Srinagar",
    "Surat", "Thiruvanthapuram", "Thrissur", "Tiruchirapalli", "Vadodra", "Varanasi",
    "Vijaywada", "Vizaq", "Visakhapatnam"
]

STATES_LIST = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttarakhand", "Uttar Pradesh", "West Bengal",
    "Andaman & Nicobar Islands", "Andaman and Nicobar", "Chandigarh",
    "Dadra & Nagar Haveli", "Daman & Diu", "Delhi", "Jammu & Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry"
]

class AnswerExtractor:
    def __init__(self, table_extractor, pages_text: Dict[int, str]):
        self.table_extractor = table_extractor
        self.pages_text = pages_text
        self.retriever = Retriever(table_extractor, pages_text)
        self.confidence_estimator = ConfidenceEstimator()

    def _find_matched_city(self, text_lower: str) -> Optional[str]:
        for c in sorted(CITIES_LIST, key=lambda x: -len(x)):
            if c.lower() in text_lower:
                return c
        return None

    def _find_matched_state(self, text_lower: str) -> Optional[str]:
        for s in sorted(STATES_LIST, key=lambda x: -len(x)):
            if s.lower() in text_lower:
                return s
        return None

    def extract_answer(self, query_obj: Dict[str, Any]) -> Dict[str, Any]:
        q_id = query_obj.get("id", "")
        q_text = query_obj.get("question", "")
        analysis = QueryAnalysis(q_text)
        q_lower = analysis.lower

        # 1. Unanswerable check (concept not in domain or explicitly out-of-scope)
        if analysis.is_unanswerable:
            return {
                "id": q_id,
                "answer": "NOT_FOUND",
                "page": None,
                "confidence": self.confidence_estimator.calculate("abstain")
            }

        matched_city = self._find_matched_city(q_lower)
        matched_state = self._find_matched_state(q_lower)

        # Detect unknown city asked in question
        if "city" in q_lower and not matched_city:
            m = re.search(r"in\s+([A-Za-z\s]+?)\s+(?:city|\()", q_text)
            if m:
                cand = m.group(1).strip()
                # If city candidate is not in report cities
                if not any(fuzz.ratio(cand.lower(), c.lower()) > 80 for c in CITIES_LIST):
                    return {
                        "id": q_id,
                        "answer": "NOT_FOUND",
                        "page": None,
                        "confidence": self.confidence_estimator.calculate("fallback_abstain")
                    }

        # 2. City: Two-wheeler riders killed
        if matched_city and ("two-wheeler" in q_lower or "two wheeler" in q_lower) and ("killed" in q_lower or "death" in q_lower):
            tbl = self.table_extractor.tables.get("city_impacting_vehicles")
            if tbl:
                match = self.retriever.find_entity_in_dict(matched_city.lower(), tbl["records"])
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
        if matched_city and "pedestrian" in q_lower and ("killed" in q_lower or "death" in q_lower):
            tbl = self.table_extractor.tables.get("city_impacting_vehicles")
            if tbl:
                match = self.retriever.find_entity_in_dict(matched_city.lower(), tbl["records"])
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
        if matched_city and "over-speeding" in q_lower and ("killed" in q_lower or "death" in q_lower):
            tbl = self.table_extractor.tables.get("city_traffic_violations")
            if tbl:
                match = self.retriever.find_entity_in_dict(matched_city.lower(), tbl["records"])
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
        if matched_city:
            tbl = self.table_extractor.tables.get("city_summary")
            if tbl:
                match = self.retriever.find_entity_in_dict(matched_city.lower(), tbl["records"])
                if match:
                    key, data, score = match
                    ans = None
                    if "injured" in q_lower or "injuries" in q_lower:
                        ans = data.get("injured_2023")
                    elif "killed" in q_lower or "death" in q_lower or "fatalities" in q_lower:
                        ans = data.get("killed_2023")
                    elif "accident" in q_lower or "crashes" in q_lower:
                        ans = data.get("accidents_2023")
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 6. State: Killed (Annexure 3)
        if matched_state and ("killed" in q_lower or "death" in q_lower or "fatalities" in q_lower):
            tbl = self.table_extractor.tables.get("state_killed")
            if tbl:
                st_search = matched_state.split('&')[0].strip() if '&' in matched_state else matched_state
                match = self.retriever.find_entity_in_dict(st_search.lower(), tbl["records"])
                if match:
                    key, data, score = match
                    ans = data.get("killed_2023")
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 7. State: Accidents (Annexure 2)
        if matched_state and "accident" in q_lower:
            tbl = self.table_extractor.tables.get("state_accidents")
            if tbl:
                st_search = matched_state.split('&')[0].strip() if '&' in matched_state else matched_state
                match = self.retriever.find_entity_in_dict(st_search.lower(), tbl["records"])
                if match:
                    key, data, score = match
                    ans = data.get("accidents_2023")
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 8. Collision Type (Table 1.5)
        if "collision" in q_lower or "run off road" in q_lower or ("type" in q_lower and "others" in q_lower):
            tbl = self.table_extractor.tables.get("collision_types")
            if tbl:
                match = self.retriever.find_entity_in_dict(q_lower, tbl["records"])
                if match:
                    key, data, score = match
                    if "killed" in q_lower or "death" in q_lower:
                        ans = data.get("killed_2023")
                    else:
                        ans = data.get("accidents_2023")
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", score)
                        }

        # 9. Road User Categories (Table 4.4)
        if "road user" in q_lower or ("in india" in q_lower and any(v in q_lower for v in ["two-wheeler", "cars", "pedestrian", "buses", "trucks"])):
            tbl = self.table_extractor.tables.get("road_users")
            if tbl:
                ru_target = "two-wheelers" if "two-wheeler" in q_lower else ("cars" if "car" in q_lower else None)
                if ru_target and ru_target in tbl["records"]:
                    ans = tbl["records"][ru_target].get("killed_2023")
                    if ans:
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": tbl["page"],
                            "confidence": self.confidence_estimator.calculate("exact_table_cell", 100.0)
                        }

        # 10. National Violations / All India (Table 3.1)
        tbl = self.table_extractor.tables.get("national_violations")
        if tbl:
            if "mobile phone" in q_lower and "use of mobile phone" in tbl["records"]:
                ans = tbl["records"]["use of mobile phone"].get("killed_2023")
                if ans:
                    return {
                        "id": q_id,
                        "answer": ans,
                        "page": tbl["page"],
                        "confidence": self.confidence_estimator.calculate("exact_table_cell", 100.0)
                    }
            if "all india" in q_lower and ("killed" in q_lower or "death" in q_lower) and "all india" in tbl["records"]:
                ans = tbl["records"]["all india"].get("killed_2023")
                if ans:
                    return {
                        "id": q_id,
                        "answer": ans,
                        "page": tbl["page"],
                        "confidence": self.confidence_estimator.calculate("exact_table_cell", 100.0)
                    }

        # Default Abstain when not supported
        return {
            "id": q_id,
            "answer": "NOT_FOUND",
            "page": None,
            "confidence": self.confidence_estimator.calculate("fallback_abstain")
        }
