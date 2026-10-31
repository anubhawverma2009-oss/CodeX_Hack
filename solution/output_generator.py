"""
Output Generator for P5 - Report Navigator.
Validates and exports predictions to standard JSONL format.
"""
import json
from typing import List, Dict, Any

class OutputGenerator:
    @staticmethod
    def validate_prediction(pred: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates schema:
        id: str
        answer: str (digits or 'NOT_FOUND')
        page: int or None
        confidence: float between 0 and 1
        """
        assert "id" in pred, "Prediction must contain 'id'"
        assert "answer" in pred, "Prediction must contain 'answer'"
        assert "page" in pred, "Prediction must contain 'page'"
        assert "confidence" in pred, "Prediction must contain 'confidence'"

        q_id = str(pred["id"])
        answer = str(pred["answer"]).strip()
        page = pred["page"]
        if page is not None:
            page = int(page)
        confidence = float(pred["confidence"])
        confidence = max(0.0, min(1.0, round(confidence, 2)))

        return {
            "id": q_id,
            "answer": answer,
            "page": page,
            "confidence": confidence
        }

    @classmethod
    def write_jsonl(cls, predictions: List[Dict[str, Any]], output_filepath: str):
        with open(output_filepath, "w", encoding="utf-8") as f:
            for p in predictions:
                validated = cls.validate_prediction(p)
                f.write(json.dumps(validated, ensure_ascii=False) + "\n")
