"""
Output Generator for P5 - Report Navigator.
Validates and exports predictions to standard JSONL format with strict schema enforcement.
"""
import json
import re
from typing import List, Dict, Any

class OutputGenerator:
    @staticmethod
    def validate_prediction(pred: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strict validation schema:
        - Exactly required keys: id, answer, page, confidence
        - id: non-empty string
        - answer: digits only or exactly 'NOT_FOUND'
        - page: positive integer or null (must be null if NOT_FOUND)
        - confidence: float between 0 and 1
        """
        expected_keys = {"id", "answer", "page", "confidence"}
        actual_keys = set(pred.keys())
        if actual_keys != expected_keys:
            raise ValueError(f"Invalid keys in prediction: {actual_keys}. Must be exactly {expected_keys}")

        q_id = pred.get("id")
        if not isinstance(q_id, str) or not q_id.strip():
            raise ValueError(f"Invalid 'id': {q_id}. Must be a non-empty string.")

        answer = str(pred.get("answer", "")).strip()
        if answer != "NOT_FOUND" and not re.match(r"^\d+$", answer):
            raise ValueError(f"Invalid 'answer': {answer}. Must be digits only or 'NOT_FOUND'.")

        page = pred.get("page")
        if answer == "NOT_FOUND":
            if page is not None:
                raise ValueError(f"Invalid 'page': {page}. Records with 'NOT_FOUND' must have page null.")
        else:
            if not isinstance(page, int) or page <= 0:
                raise ValueError(f"Invalid 'page': {page}. Must be a positive integer.")

        confidence = pred.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            raise ValueError(f"Invalid 'confidence': {confidence}. Must be a number between 0 and 1.")

        return {
            "id": q_id,
            "answer": answer,
            "page": page,
            "confidence": round(float(confidence), 2)
        }

    @classmethod
    def write_jsonl(cls, predictions: List[Dict[str, Any]], output_filepath: str):
        with open(output_filepath, "w", encoding="utf-8") as f:
            for p in predictions:
                validated = cls.validate_prediction(p)
                f.write(json.dumps(validated, ensure_ascii=False) + "\n")
