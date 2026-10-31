#!/usr/bin/env python3
"""
Single query CLI runner for P5 - Report Navigator.
Usage:
  python3 solution/query.py --pdf <path_to_pdf> --question "<question>" [--id <id>]
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_processor import PDFProcessor
from table_extractor import TableExtractor
from answer_extractor import AnswerExtractor
from retriever import QueryAnalysis

def main():
    parser = argparse.ArgumentParser(description="Query single question from PDF report")
    parser.add_argument("--pdf", default="public/assets/aistudio/report_A_90150542.pdf", help="Path to PDF report")
    parser.add_argument("--question", required=True, help="Question text")
    parser.add_argument("--id", default="custom", help="Question ID")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR")
    args = parser.parse_args()

    proc = PDFProcessor(pdf_path=args.pdf, enable_ocr=not args.no_ocr)
    tables = TableExtractor(proc.get_all_pages(), default_year=proc.report_year)
    extractor = AnswerExtractor(tables, proc.get_all_pages(), default_year=proc.report_year, pdf_processor=proc)
    
    res = extractor.extract_answer({"id": args.id, "question": args.question})
    analysis = QueryAnalysis(args.question, default_year=proc.report_year)
    
    snippet = ""
    if res.get("page"):
        p_text = proc.get_page_text(res["page"])
        lines = [l for l in p_text.split('\n') if l.strip()]
        snippet = "\n".join(lines[:12])

    output = {
        **res,
        "query_analysis": {
            "entity_type": analysis.entity_type,
            "metric": analysis.metric,
            "year": analysis.year,
            "is_unanswerable": (res["answer"] == "NOT_FOUND")
        },
        "page_snippet": snippet
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()
