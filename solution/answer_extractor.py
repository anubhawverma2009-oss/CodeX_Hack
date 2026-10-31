"""
Answer Extractor for P5 - Report Navigator.
Extracts exact numerical answers and page numbers based on query semantics,
dynamic table coordinates, and text search.
Generates comprehensive execution trace metadata for pipeline transparency.
"""
import re
from typing import Dict, Any, Tuple, Optional
from rapidfuzz import fuzz

from retriever import QueryAnalysis, Retriever
from confidence import ConfidenceEstimator

class AnswerExtractor:
    def __init__(self, table_extractor, pages_text: Dict[int, str], default_year: int = 2023, pdf_processor: Optional[Any] = None):
        self.table_extractor = table_extractor
        self.pages_text = pages_text
        self.default_year = default_year
        self.pdf_processor = pdf_processor
        self.retriever = Retriever(table_extractor, pages_text)
        self.confidence_estimator = ConfidenceEstimator()
        self._full_doc_text = " ".join(pages_text.values()).lower()

    def _make_trace(self,
                    entity: Optional[str],
                    metric: Optional[str],
                    year: Optional[Any],
                    retrieved_page: Optional[int],
                    table_name: Optional[str],
                    method: Optional[str],
                    matched_row: Optional[str],
                    matched_column: Optional[str],
                    extracted_value: str,
                    raw_line: Optional[str],
                    confidence_score: float,
                    confidence_basis: Optional[str],
                    ocr_used: bool) -> Dict[str, Any]:
        return {
            # Flat top-level aliases for direct key access
            "entity_type": entity if entity else "Not available",
            "metric": metric if metric else "Not available",
            "year": str(year) if year is not None else "Not available",
            "retrieved_page": retrieved_page,
            "table_title": table_name if table_name else "Not available",
            "retrieval_method": method if method else "Not available",
            "matched_row": matched_row if matched_row else "Not available",
            "matched_col": matched_column if matched_column else "Not available",
            "evidence_text": raw_line if raw_line else "Not available",
            "confidence_score": confidence_score,
            "confidence_basis": confidence_basis if confidence_basis else "Not available",
            "ocr_used": ocr_used,

            # Categorized sub-dictionaries for pipeline transparency
            "question_understanding": {
                "entity": entity if entity else "Not available",
                "metric": metric if metric else "Not available",
                "year": str(year) if year is not None else "Not available"
            },
            "document_retrieval": {
                "retrieved_page": retrieved_page,
                "table_name": table_name if table_name else "Not available",
                "method": method if method else "Not available"
            },
            "answer_extraction": {
                "matched_row": matched_row if matched_row else "Not available",
                "matched_column": matched_column if matched_column else "Not available",
                "extracted_value": extracted_value,
                "raw_line": raw_line if raw_line else "Not available"
            },
            "verification": {
                "citation_page": retrieved_page,
                "confidence_score": confidence_score,
                "confidence_basis": confidence_basis if confidence_basis else "Not available",
                "ocr_used": ocr_used
            }
        }

    def extract_answer(self, query_obj: Dict[str, Any]) -> Dict[str, Any]:
        q_id = query_obj.get("id", "")
        q_text = query_obj.get("question", "")
        analysis = QueryAnalysis(q_text, default_year=self.default_year)
        q_lower = analysis.lower
        target_year = analysis.year

        # 1. Document Evidence Check (Dynamic unanswerable detection)
        if not self.retriever.check_document_contains_evidence(q_text, self._full_doc_text):
            conf = self.confidence_estimator.calculate("abstain")
            return {
                "id": q_id,
                "answer": "NOT_FOUND",
                "page": None,
                "confidence": conf,
                "trace": self._make_trace(
                    entity=analysis.extracted_entity,
                    metric=analysis.metric if analysis.metric != "count" else "Not available",
                    year=target_year,
                    retrieved_page=None,
                    table_name="Not available",
                    method="Document Evidence Verification (Abstention)",
                    matched_row="Not available",
                    matched_column="Not available",
                    extracted_value="NOT_FOUND",
                    raw_line="Query keywords or entity not found anywhere in report text.",
                    confidence_score=conf,
                    confidence_basis="High-confidence abstention based on missing document evidence",
                    ocr_used=False
                )
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
                        conf = self.confidence_estimator.calculate("exact_table_cell", score)
                        page_num = tbl["page"]
                        ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": page_num,
                            "confidence": conf,
                            "trace": self._make_trace(
                                entity=data.get("name", key.title()),
                                metric="Two-Wheelers Killed",
                                year=self.default_year,
                                retrieved_page=page_num,
                                table_name="Annexure 46: Accidents Classified by Type of Impacting Vehicles in Million Plus Cities",
                                method="Structured Table Coordinate Indexing",
                                matched_row=data.get("name", key.title()),
                                matched_column="Two-Wheelers Killed",
                                extracted_value=ans,
                                raw_line=data.get("raw_line", "Not available"),
                                confidence_score=conf,
                                confidence_basis=f"Exact table cell match with fuzzy entity score {score:.1f}%",
                                ocr_used=ocr_used
                            )
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
                        conf = self.confidence_estimator.calculate("exact_table_cell", score)
                        page_num = tbl["page"]
                        ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": page_num,
                            "confidence": conf,
                            "trace": self._make_trace(
                                entity=data.get("name", key.title()),
                                metric="Pedestrians Killed",
                                year=self.default_year,
                                retrieved_page=page_num,
                                table_name="Annexure 46: Accidents Classified by Type of Impacting Vehicles in Million Plus Cities",
                                method="Structured Table Coordinate Indexing",
                                matched_row=data.get("name", key.title()),
                                matched_column="Pedestrians Killed",
                                extracted_value=ans,
                                raw_line=data.get("raw_line", "Not available"),
                                confidence_score=conf,
                                confidence_basis=f"Exact table cell match with fuzzy entity score {score:.1f}%",
                                ocr_used=ocr_used
                            )
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
                        conf = self.confidence_estimator.calculate("exact_table_cell", score)
                        page_num = tbl["page"]
                        ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": page_num,
                            "confidence": conf,
                            "trace": self._make_trace(
                                entity=data.get("name", key.title()),
                                metric="Over-speeding Persons Killed",
                                year=self.default_year,
                                retrieved_page=page_num,
                                table_name="Annexure 47: Traffic Rule Violations in Million Plus Cities",
                                method="Structured Table Coordinate Indexing",
                                matched_row=data.get("name", key.title()),
                                matched_column="Over-speeding Persons Killed",
                                extracted_value=ans,
                                raw_line=data.get("raw_line", "Not available"),
                                confidence_score=conf,
                                confidence_basis=f"Exact table cell match with fuzzy entity score {score:.1f}%",
                                ocr_used=ocr_used
                            )
                        }

        # 5. City: Summary accidents, killed, injured (Table 6.2)
        tbl_city = self.table_extractor.tables.get("city_summary")
        if tbl_city:
            match = self.retriever.find_entity_in_dict(q_lower, tbl_city["records"])
            if match:
                key, data, score = match
                year_to_use = target_year if target_year in tbl_city.get("years", []) else tbl_city.get("curr_year", self.default_year)
                ans = None
                metric_label = None
                if "injured" in q_lower or "injuries" in q_lower:
                    ans = data["injured"].get(year_to_use)
                    metric_label = f"Persons Injured ({year_to_use})"
                elif "killed" in q_lower or "death" in q_lower or "fatalities" in q_lower:
                    ans = data["killed"].get(year_to_use)
                    metric_label = f"Persons Killed ({year_to_use})"
                elif "accident" in q_lower or "crashes" in q_lower:
                    ans = data["accidents"].get(year_to_use)
                    metric_label = f"Total Accidents ({year_to_use})"

                if ans:
                    conf = self.confidence_estimator.calculate("exact_table_cell", score)
                    page_num = tbl_city["page"]
                    ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                    return {
                        "id": q_id,
                        "answer": ans,
                        "page": page_num,
                        "confidence": conf,
                        "trace": self._make_trace(
                            entity=data.get("name", key.title()),
                            metric=metric_label,
                            year=year_to_use,
                            retrieved_page=page_num,
                            table_name="Table 6.2: Number of Road Accidents, Persons Killed & Injured in Million-Plus Cities",
                            method="Structured Table Coordinate Indexing",
                            matched_row=data.get("name", key.title()),
                            matched_column=metric_label,
                            extracted_value=ans,
                            raw_line=data.get("raw_line", "Not available"),
                            confidence_score=conf,
                            confidence_basis=f"Exact table cell match with fuzzy entity score {score:.1f}%",
                            ocr_used=ocr_used
                        )
                    }

        # If question asked specifically for a city but not matched in the city table
        if "city" in q_lower:
            conf = self.confidence_estimator.calculate("fallback_abstain")
            return {
                "id": q_id,
                "answer": "NOT_FOUND",
                "page": None,
                "confidence": conf,
                "trace": self._make_trace(
                    entity=analysis.extracted_entity if analysis.extracted_entity else "Requested City",
                    metric=analysis.metric if analysis.metric != "count" else "Not available",
                    year=target_year,
                    retrieved_page=None,
                    table_name="Not available",
                    method="Million-Plus City Index Lookup (Abstention)",
                    matched_row="Not available",
                    matched_column="Not available",
                    extracted_value="NOT_FOUND",
                    raw_line="Requested city is not listed in Table 6.2 or Million-Plus City annexures.",
                    confidence_score=conf,
                    confidence_basis="Fallback abstention filter for unlisted city",
                    ocr_used=False
                )
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
                        conf = self.confidence_estimator.calculate("exact_table_cell", score)
                        page_num = tbl_state_k["page"]
                        ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": page_num,
                            "confidence": conf,
                            "trace": self._make_trace(
                                entity=data.get("name", key.title()),
                                metric=f"Persons Killed ({year_to_use})",
                                year=year_to_use,
                                retrieved_page=page_num,
                                table_name="Annexure 3: State/UT-wise Total Number of Persons Killed",
                                method="Structured Table Coordinate Indexing",
                                matched_row=data.get("name", key.title()),
                                matched_column=f"Persons Killed ({year_to_use})",
                                extracted_value=ans,
                                raw_line=data.get("raw_line", "Not available"),
                                confidence_score=conf,
                                confidence_basis=f"Exact table cell match with fuzzy entity score {score:.1f}%",
                                ocr_used=ocr_used
                            )
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
                        conf = self.confidence_estimator.calculate("exact_table_cell", score)
                        page_num = tbl_state_a["page"]
                        ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": page_num,
                            "confidence": conf,
                            "trace": self._make_trace(
                                entity=data.get("name", key.title()),
                                metric=f"Total Road Accidents ({year_to_use})",
                                year=year_to_use,
                                retrieved_page=page_num,
                                table_name="Annexure 2: State/UT-wise Total Number of Road Accidents",
                                method="Structured Table Coordinate Indexing",
                                matched_row=data.get("name", key.title()),
                                matched_column=f"Total Road Accidents ({year_to_use})",
                                extracted_value=ans,
                                raw_line=data.get("raw_line", "Not available"),
                                confidence_score=conf,
                                confidence_basis=f"Exact table cell match with fuzzy entity score {score:.1f}%",
                                ocr_used=ocr_used
                            )
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
                        metric_label = f"Persons Killed ({year_to_use})"
                    else:
                        ans = data["accidents"].get(year_to_use)
                        metric_label = f"Total Accidents ({year_to_use})"
                    if ans:
                        conf = self.confidence_estimator.calculate("exact_table_cell", score)
                        page_num = tbl_col["page"]
                        ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": page_num,
                            "confidence": conf,
                            "trace": self._make_trace(
                                entity="Collision Type Breakdown",
                                metric=metric_label,
                                year=year_to_use,
                                retrieved_page=page_num,
                                table_name="Table 1.5: Accidents by Type of Collision",
                                method="Structured Table Coordinate Indexing",
                                matched_row=key.title(),
                                matched_column=metric_label,
                                extracted_value=ans,
                                raw_line=data.get("raw_line", "Not available"),
                                confidence_score=conf,
                                confidence_basis=f"Exact table cell match with fuzzy entity score {score:.1f}%",
                                ocr_used=ocr_used
                            )
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
                        conf = self.confidence_estimator.calculate("exact_table_cell", 100.0)
                        page_num = tbl_ru["page"]
                        ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                        return {
                            "id": q_id,
                            "answer": ans,
                            "page": page_num,
                            "confidence": conf,
                            "trace": self._make_trace(
                                entity="Road User Categories",
                                metric=f"Persons Killed ({year_to_use})",
                                year=year_to_use,
                                retrieved_page=page_num,
                                table_name="Table 4.4: Persons Killed in Road Accidents by Road User Category",
                                method="Structured Table Coordinate Indexing",
                                matched_row=ru_target.title(),
                                matched_column=f"Persons Killed ({year_to_use})",
                                extracted_value=ans,
                                raw_line=tbl_ru["records"][ru_target].get("raw_line", "Not available"),
                                confidence_score=conf,
                                confidence_basis="Exact table cell match with 100% entity score",
                                ocr_used=ocr_used
                            )
                        }

        # 10. National Violations / All India (Table 3.1)
        tbl_viol = self.table_extractor.tables.get("national_violations")
        if tbl_viol:
            year_to_use = target_year if target_year in tbl_viol.get("years", []) else tbl_viol.get("curr_year", self.default_year)
            if "mobile phone" in q_lower and "use of mobile phone" in tbl_viol["records"]:
                ans = tbl_viol["records"]["use of mobile phone"]["killed"].get(year_to_use)
                if ans:
                    conf = self.confidence_estimator.calculate("exact_table_cell", 100.0)
                    page_num = tbl_viol["page"]
                    ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                    return {
                        "id": q_id,
                        "answer": ans,
                        "page": page_num,
                        "confidence": conf,
                        "trace": self._make_trace(
                            entity="National Violations",
                            metric=f"Persons Killed ({year_to_use})",
                            year=year_to_use,
                            retrieved_page=page_num,
                            table_name="Table 3.1: Traffic Rules Violation During Calendar Year",
                            method="Structured Table Coordinate Indexing",
                            matched_row="Use of Mobile Phone",
                            matched_column=f"Persons Killed ({year_to_use})",
                            extracted_value=ans,
                            raw_line=tbl_viol["records"]["use of mobile phone"].get("raw_line", "Not available"),
                            confidence_score=conf,
                            confidence_basis="Exact table cell match with 100% entity score",
                            ocr_used=ocr_used
                        )
                    }
            if "all india" in q_lower and ("killed" in q_lower or "death" in q_lower) and "all india" in tbl_viol["records"]:
                ans = tbl_viol["records"]["all india"]["killed"].get(year_to_use)
                if ans:
                    conf = self.confidence_estimator.calculate("exact_table_cell", 100.0)
                    page_num = tbl_viol["page"]
                    ocr_used = self.pdf_processor.is_ocr_page(page_num) if self.pdf_processor else False
                    return {
                        "id": q_id,
                        "answer": ans,
                        "page": page_num,
                        "confidence": conf,
                        "trace": self._make_trace(
                            entity="All India Total",
                            metric=f"Persons Killed ({year_to_use})",
                            year=year_to_use,
                            retrieved_page=page_num,
                            table_name="Table 3.1: Traffic Rules Violation During Calendar Year",
                            method="Structured Table Coordinate Indexing",
                            matched_row="All India",
                            matched_column=f"Persons Killed ({year_to_use})",
                            extracted_value=ans,
                            raw_line=tbl_viol["records"]["all india"].get("raw_line", "Not available"),
                            confidence_score=conf,
                            confidence_basis="Exact table cell match with 100% entity score",
                            ocr_used=ocr_used
                        )
                    }

        # Default Abstain
        conf = self.confidence_estimator.calculate("fallback_abstain")
        return {
            "id": q_id,
            "answer": "NOT_FOUND",
            "page": None,
            "confidence": conf,
            "trace": self._make_trace(
                entity=analysis.extracted_entity if analysis.extracted_entity else "Not available",
                metric=analysis.metric if analysis.metric != "count" else "Not available",
                year=target_year,
                retrieved_page=None,
                table_name="Not available",
                method="Fallback Abstention Filter",
                matched_row="Not available",
                matched_column="Not available",
                extracted_value="NOT_FOUND",
                raw_line="Metric or entity unsupported by statistical tables in report.",
                confidence_score=conf,
                confidence_basis="Fallback abstention filter",
                ocr_used=False
            )
        }
