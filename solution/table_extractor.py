"""
Table Extractor for P5 - Report Navigator.
Extracts and structures tables from the PDF document:
- City tables (Table 6.2, Annexure 46, Annexure 47, Annexure 48, etc.)
- State tables (Annexures 2, 3, 4, etc.)
- Aggregate breakdown tables (Collision types, Road users, Violations)
"""
import re
from typing import Dict, List, Optional, Any

def clean_num(val: str) -> str:
    """Strip commas, spaces, currency symbols to pure digits."""
    cleaned = re.sub(r"[,\s]", "", str(val))
    match = re.search(r"^\d+", cleaned)
    return match.group(0) if match else cleaned

class TableExtractor:
    def __init__(self, pages_text: Dict[int, str]):
        self.pages_text = pages_text
        self.tables = {}
        self._index_all_tables()

    def _index_all_tables(self):
        for page_num, text in self.pages_text.items():
            text_lower = text.lower()
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            # Million Plus Cities main table (Table 6.2)
            if "table 6.2" in text_lower or ("million-plus cities" in text_lower and "number of road accidents, persons killed" in text_lower):
                self._parse_million_plus_summary(page_num, lines)

            # Annexure 46: Impacting Vehicles in Million Plus Cities (Primary page has Pedestrians & Two Wheelers)
            elif "annexure 46" in text_lower and ("two wheelers" in text_lower or "two-wheelers" in text_lower) and "pedestrian" in text_lower and "concld" not in text_lower:
                self._parse_city_impacting_vehicles(page_num, lines)

            # Annexure 47: Traffic Violations in Million Plus Cities (Primary page has Over-Speeding)
            elif "annexure 47" in text_lower and "over-speeding" in text_lower and "concld" not in text_lower:
                self._parse_city_traffic_violations(page_num, lines)

            # Annexure 2: State wise Total Road Accidents (Primary page, not Concld)
            elif "annexure 2" in text_lower and "concld" not in text_lower and "total number of road accidents in india" in text_lower:
                self._parse_state_accidents(page_num, lines)

            # Annexure 3: State wise Total Persons Killed (Primary page, not Concld)
            elif "annexure 3" in text_lower and "concld" not in text_lower and "total number of persons killed in road accidents in india" in text_lower:
                self._parse_state_killed(page_num, lines)

            # Table 1.5: Accidents by type of collision
            elif "table 1.5" in text_lower or ("type of collision" in text_lower and "run off road" in text_lower):
                self._parse_collision_types(page_num, lines)

            # Table 4.4: Persons killed in road accidents in terms of road user categories
            elif "table 4.4" in text_lower or ("road user categories in" in text_lower and "two-wheelers" in text_lower):
                self._parse_road_users(page_num, lines)

            # Table 3.1: Traffic Rules Violation national
            elif "table 3.1" in text_lower or ("traffic rules violation during" in text_lower and "over-speeding" in text_lower):
                self._parse_national_violations(page_num, lines)

    def _parse_million_plus_summary(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 11:
                # Find city name
                words = re.findall(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", line)
                city_candidates = [w for w in words if w.lower() not in ["in", "numbers", "ranking", "total", "accidents", "killed", "injured", "sl", "no"]]
                if city_candidates:
                    city_name = city_candidates[0].strip()
                    offset = 1 if int(nums[0]) <= 50 and len(nums) > 12 else 0
                    records[city_name.lower()] = {
                        "accidents_2022": nums[offset],
                        "accidents_2023": nums[offset + 1],
                        "killed_2022": nums[offset + 4],
                        "killed_2023": nums[offset + 5],
                        "injured_2022": nums[offset + 8],
                        "injured_2023": nums[offset + 9],
                        "page": page_num,
                        "raw_line": line
                    }
        if records:
            self.tables["city_summary"] = {"page": page_num, "records": records}

    def _parse_city_impacting_vehicles(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 11:
                words = re.findall(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", line)
                city_candidates = [w for w in words if w.lower() not in ["killed", "grievously", "minor", "injured", "total", "contd", "bicycles", "two", "wheelers", "pedestrian"]]
                if city_candidates:
                    city_name = city_candidates[0].strip()
                    # Pedestrian killed is index 2, Two-wheelers killed is index 10
                    records[city_name.lower()] = {
                        "pedestrians_killed": nums[2] if len(nums) > 2 else None,
                        "bicycles_killed": nums[6] if len(nums) > 6 else None,
                        "twowheelers_killed": nums[10] if len(nums) > 10 else None,
                        "page": page_num,
                        "raw_line": line
                    }
        if records:
            self.tables["city_impacting_vehicles"] = {"page": page_num, "records": records}

    def _parse_city_traffic_violations(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 4:
                words = re.findall(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", line)
                city_candidates = [w for w in words if w.lower() not in ["number", "rank", "grievously", "minor", "injury", "total", "injured", "contd"]]
                if city_candidates:
                    city_name = city_candidates[0].strip()
                    records[city_name.lower()] = {
                        "overspeeding_accidents": nums[1],
                        "overspeeding_killed": nums[3],
                        "page": page_num,
                        "raw_line": line
                    }
        if records:
            self.tables["city_traffic_violations"] = {"page": page_num, "records": records}

    def _parse_state_accidents(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 5:
                words = re.findall(r"[A-Za-z&]+(?:\s+[A-Za-z&]+)*", line)
                state_candidates = [w for w in words if w.lower() not in ["number", "rank", "total", "note", "contd", "road", "length"]]
                if state_candidates:
                    state_name = state_candidates[0].strip()
                    records[state_name.lower()] = {
                        "accidents_2020": nums[1],
                        "accidents_2021": nums[2],
                        "accidents_2022": nums[3],
                        "accidents_2023": nums[4],
                        "page": page_num,
                        "raw_line": line
                    }
        if records:
            self.tables["state_accidents"] = {"page": page_num, "records": records}

    def _parse_state_killed(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 5:
                words = re.findall(r"[A-Za-z&]+(?:\s+[A-Za-z&]+)*", line)
                state_candidates = [w for w in words if w.lower() not in ["number", "rank", "total", "note", "contd", "road", "length", "population"]]
                if state_candidates:
                    state_name = state_candidates[0].strip()
                    records[state_name.lower()] = {
                        "killed_2020": nums[1],
                        "killed_2021": nums[2],
                        "killed_2022": nums[3],
                        "killed_2023": nums[4],
                        "page": page_num,
                        "raw_line": line
                    }
        if records:
            self.tables["state_killed"] = {"page": page_num, "records": records}

    def _parse_collision_types(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            line_clean = line.replace("%", "").strip()
            nums = [clean_num(p) for p in line_clean.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 6:
                for ct in ["hit and run", "parked vehicle", "hit from back", "hit from side", "run off road", "fixed object", "vehicle overturn", "head on collision", "others"]:
                    if ct in line.lower():
                        records[ct] = {
                            "accidents_2022": nums[0],
                            "killed_2022": nums[1],
                            "injured_2022": nums[2],
                            "accidents_2023": nums[3],
                            "killed_2023": nums[4],
                            "injured_2023": nums[5],
                            "page": page_num,
                            "raw_line": line
                        }
        if records:
            self.tables["collision_types"] = {"page": page_num, "records": records}

    def _parse_road_users(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 2:
                for ru in ["pedestrian", "bicycles", "two-wheelers", "auto-rickshaws", "cars", "trucks", "buses", "other non- motor", "others"]:
                    if ru in line.lower():
                        records[ru] = {
                            "killed_2022": nums[0],
                            "killed_2023": nums[1],
                            "page": page_num,
                            "raw_line": line
                        }
        if records:
            self.tables["road_users"] = {"page": page_num, "records": records}

    def _parse_national_violations(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 5:
                for v in ["over-speeding", "drunken driving", "wrong side", "jumping red light", "use of mobile phone", "others", "all india"]:
                    if v in line.lower():
                        records[v] = {
                            "accidents_2022": nums[0],
                            "killed_2022": nums[1],
                            "injured_2022": nums[2],
                            "accidents_2023": nums[3],
                            "killed_2023": nums[4],
                            "page": page_num,
                            "raw_line": line
                        }
        if records:
            self.tables["national_violations"] = {"page": page_num, "records": records}
