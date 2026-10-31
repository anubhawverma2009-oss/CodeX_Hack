"""
Table Extractor for P5 - Report Navigator.
Extracts and structures tables dynamically from any PDF report in the family:
- City tables (Table 6.2, Annexure 46, Annexure 47)
- State tables (Annexure 2, Annexure 3)
- Aggregate breakdown tables (Collision types, Road users, Violations)
Detects column years dynamically from table headers instead of hardcoding.
"""
import re
from typing import Dict, List, Optional, Any

def clean_num(val: str) -> str:
    """Strip commas, spaces, currency symbols to pure digits."""
    cleaned = re.sub(r"[,\s]", "", str(val))
    match = re.search(r"^\d+", cleaned)
    return match.group(0) if match else cleaned

class TableExtractor:
    def __init__(self, pages_text: Dict[int, str], default_year: int = 2023):
        self.pages_text = pages_text
        self.default_year = default_year
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
        # Detect the two comparison years from the header
        header_years = []
        for l in lines[:10]:
            found = re.findall(r"\b(20[12]\d)\b", l)
            if len(found) >= 2:
                header_years = [int(found[0]), int(found[1])]
                break
        if not header_years:
            header_years = [self.default_year - 1, self.default_year]

        y_prev, y_curr = header_years[0], header_years[1]
        records = {}

        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 11:
                words = re.findall(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", line)
                city_candidates = [
                    w for w in words 
                    if w.lower() not in ["in", "numbers", "ranking", "total", "accidents", "killed", "injured", "sl", "no", "plus", "cities"]
                ]
                if city_candidates:
                    city_name = city_candidates[0].strip()
                    offset = 1 if int(nums[0]) <= 50 and len(nums) > 12 else 0
                    records[city_name.lower()] = {
                        "name": city_name,
                        "accidents": {y_prev: nums[offset], y_curr: nums[offset + 1]},
                        "killed": {y_prev: nums[offset + 4], y_curr: nums[offset + 5]},
                        "injured": {y_prev: nums[offset + 8], y_curr: nums[offset + 9]},
                        "page": page_num,
                        "raw_line": line
                    }

        if records:
            self.tables["city_summary"] = {
                "page": page_num,
                "years": [y_prev, y_curr],
                "curr_year": y_curr,
                "records": records
            }

    def _parse_city_impacting_vehicles(self, page_num: int, lines: List[str]):
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 11:
                words = re.findall(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", line)
                city_candidates = [
                    w for w in words 
                    if w.lower() not in ["killed", "grievously", "minor", "injured", "total", "contd", "bicycles", "two", "wheelers", "pedestrian", "number", "rank"]
                ]
                if city_candidates:
                    city_name = city_candidates[0].strip()
                    records[city_name.lower()] = {
                        "name": city_name,
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
                city_candidates = [
                    w for w in words 
                    if w.lower() not in ["number", "rank", "grievously", "minor", "injury", "total", "injured", "contd", "speeding", "violations"]
                ]
                if city_candidates:
                    city_name = city_candidates[0].strip()
                    records[city_name.lower()] = {
                        "name": city_name,
                        "overspeeding_accidents": nums[1],
                        "overspeeding_killed": nums[3],
                        "page": page_num,
                        "raw_line": line
                    }
        if records:
            self.tables["city_traffic_violations"] = {"page": page_num, "records": records}

    def _parse_state_accidents(self, page_num: int, lines: List[str]):
        # The 4 comparison years in standard TRW Annexure 2 are [curr_year - 3, curr_year - 2, curr_year - 1, curr_year]
        # e.g. [2020, 2021, 2022, 2023]
        years = [self.default_year - 3, self.default_year - 2, self.default_year - 1, self.default_year]
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 5:
                words = re.findall(r"[A-Za-z&]+(?:\s+[A-Za-z&]+)*", line)
                state_candidates = [
                    w for w in words 
                    if w.lower() not in ["number", "rank", "total", "note", "contd", "road", "length", "states", "uts"]
                ]
                if state_candidates:
                    state_name = state_candidates[0].strip()
                    year_dict = {}
                    for i, yr in enumerate(years):
                        if i + 1 < len(nums):
                            year_dict[yr] = nums[i + 1]
                    records[state_name.lower()] = {
                        "name": state_name,
                        "accidents_by_year": year_dict,
                        "latest": nums[4] if len(nums) > 4 else nums[1],
                        "page": page_num,
                        "raw_line": line
                    }
        if records:
            self.tables["state_accidents"] = {
                "page": page_num,
                "years": years,
                "curr_year": self.default_year,
                "records": records
            }

    def _parse_state_killed(self, page_num: int, lines: List[str]):
        years = [self.default_year - 3, self.default_year - 2, self.default_year - 1, self.default_year]
        records = {}
        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 5:
                words = re.findall(r"[A-Za-z&]+(?:\s+[A-Za-z&]+)*", line)
                state_candidates = [
                    w for w in words 
                    if w.lower() not in ["number", "rank", "total", "note", "contd", "road", "length", "population", "states", "uts"]
                ]
                if state_candidates:
                    state_name = state_candidates[0].strip()
                    year_dict = {}
                    for i, yr in enumerate(years):
                        if i + 1 < len(nums):
                            year_dict[yr] = nums[i + 1]
                    records[state_name.lower()] = {
                        "name": state_name,
                        "killed_by_year": year_dict,
                        "latest": nums[4] if len(nums) > 4 else nums[1],
                        "page": page_num,
                        "raw_line": line
                    }
        if records:
            self.tables["state_killed"] = {
                "page": page_num,
                "years": years,
                "curr_year": self.default_year,
                "records": records
            }

    def _parse_collision_types(self, page_num: int, lines: List[str]):
        header_years = []
        for l in lines[:8]:
            found = re.findall(r"\b(20[12]\d)\b", l)
            if len(found) >= 2:
                header_years = [int(found[0]), int(found[1])]
                break
        if not header_years:
            header_years = [self.default_year - 1, self.default_year]

        y_prev, y_curr = header_years[0], header_years[1]
        records = {}

        for line in lines:
            line_clean = line.replace("%", "").strip()
            nums = [clean_num(p) for p in line_clean.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 6:
                for ct in ["hit and run", "parked vehicle", "hit from back", "hit from side", "run off road", "fixed object", "vehicle overturn", "head on collision", "others"]:
                    if ct in line.lower():
                        records[ct] = {
                            "accidents": {y_prev: nums[0], y_curr: nums[3]},
                            "killed": {y_prev: nums[1], y_curr: nums[4]},
                            "injured": {y_prev: nums[2], y_curr: nums[5]},
                            "page": page_num,
                            "raw_line": line
                        }
        if records:
            self.tables["collision_types"] = {
                "page": page_num,
                "years": [y_prev, y_curr],
                "curr_year": y_curr,
                "records": records
            }

    def _parse_road_users(self, page_num: int, lines: List[str]):
        header_years = []
        for l in lines[:6]:
            found = re.findall(r"\b(20[12]\d)\b", l)
            if len(found) >= 2:
                header_years = [int(found[0]), int(found[1])]
                break
        if not header_years:
            header_years = [self.default_year - 1, self.default_year]

        y_prev, y_curr = header_years[0], header_years[1]
        records = {}

        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 2:
                for ru in ["pedestrian", "bicycles", "two-wheelers", "auto-rickshaws", "cars", "trucks", "buses", "other non- motor", "others"]:
                    if ru in line.lower():
                        records[ru] = {
                            "killed": {y_prev: nums[0], y_curr: nums[1]},
                            "page": page_num,
                            "raw_line": line
                        }
        if records:
            self.tables["road_users"] = {
                "page": page_num,
                "years": [y_prev, y_curr],
                "curr_year": y_curr,
                "records": records
            }

    def _parse_national_violations(self, page_num: int, lines: List[str]):
        header_years = []
        for l in lines[:6]:
            found = re.findall(r"\b(20[12]\d)\b", l)
            if len(found) >= 2:
                header_years = [int(found[0]), int(found[1])]
                break
        if not header_years:
            header_years = [self.default_year - 1, self.default_year]

        y_prev, y_curr = header_years[0], header_years[1]
        records = {}

        for line in lines:
            nums = [clean_num(p) for p in line.split() if re.search(r"\d", p)]
            nums = [p for p in nums if p.isdigit()]
            if len(nums) >= 5:
                for v in ["over-speeding", "drunken driving", "wrong side", "jumping red light", "use of mobile phone", "others", "all india"]:
                    if v in line.lower():
                        records[v] = {
                            "accidents": {y_prev: nums[0], y_curr: nums[3]},
                            "killed": {y_prev: nums[1], y_curr: nums[4]},
                            "page": page_num,
                            "raw_line": line
                        }
        if records:
            self.tables["national_violations"] = {
                "page": page_num,
                "years": [y_prev, y_curr],
                "curr_year": y_curr,
                "records": records
            }
