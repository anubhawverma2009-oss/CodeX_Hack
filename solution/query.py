#!/usr/bin/env python3
"""
Single query runner for interactive UI.
Loads pre-indexed pages if available for sub-100ms response time.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_processor import PDFProcessor
from table_extractor import TableExtractor
from answer_extractor import AnswerExtractor
from retriever import QueryAnalysis

_CACHED_EXTRACTOR = None
_CACHED_PAGES = None

def get_extractor(pdf_path="public/assets/aistudio/report_A_90150542.pdf"):
    global _CACHED_EXTRACTOR, _CACHED_PAGES
    if _CACHED_EXTRACTOR is not None:
        return _CACHED_EXTRACTOR, _CACHED_PAGES

    cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cached_pages.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            raw_pages = json.load(f)
            # Keys in json are strings, convert to int
            _CACHED_PAGES = {int(k): v for k, v in raw_pages.items()}
    else:
        proc = PDFProcessor(pdf_path=pdf_path, enable_ocr=False)
        _CACHED_PAGES = proc.get_all_pages()

    table_extractor = TableExtractor(_CACHED_PAGES)
    _CACHED_EXTRACTOR = AnswerExtractor(table_extractor, _CACHED_PAGES)
    return _CACHED_EXTRACTOR, _CACHED_PAGES

def query_one(question: str, q_id: str = "custom", pdf_path="public/assets/aistudio/report_A_90150542.pdf"):
    extractor, pages = get_extractor(pdf_path)
    res = extractor.extract_answer({"id": q_id, "question": question})
    analysis = QueryAnalysis(question)
    
    snippet = ""
    if res.get("page"):
        p_text = pages.get(res["page"], "")
        lines = [l for l in p_text.split('\n') if l.strip()]
        snippet = "\n".join(lines[:12])

    return {
        **res,
        "query_analysis": {
            "entity_type": analysis.entity_type,
            "metric": analysis.metric,
            "year": analysis.year,
            "is_unanswerable": analysis.is_unanswerable
        },
        "page_snippet": snippet
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = sys.argv[1]
        out = query_one(q)
        print(json.dumps(out))
    else:
        print(json.dumps({"error": "No question provided"}))
