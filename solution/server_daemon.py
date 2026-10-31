#!/usr/bin/env python3
"""
Server Daemon for P5 - Report Navigator.
Keeps the active PDF index in-memory for sub-second web queries and page inspection.
Communicates via JSON-RPC lines on stdin/stdout.
"""
import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_processor import PDFProcessor
from table_extractor import TableExtractor
from answer_extractor import AnswerExtractor
from retriever import QueryAnalysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ServerDaemon")

class DaemonEngine:
    def __init__(self):
        self.active_pdf_path = None
        self.processor = None
        self.table_extractor = None
        self.answer_extractor = None
        self.num_pages = 0
        self.report_year = 2023

    def load_pdf(self, pdf_path: str, enable_ocr: bool = True):
        try:
            abs_path = os.path.abspath(pdf_path)
            if not os.path.exists(abs_path):
                return {"status": "error", "message": f"File not found: {abs_path}"}

            logger.info(f"Loading PDF with OCR enabled: {abs_path}")
            self.processor = PDFProcessor(pdf_path=abs_path, enable_ocr=enable_ocr)
            pages_text = self.processor.get_all_pages()
            self.num_pages = self.processor.num_pages
            self.report_year = self.processor.report_year
            self.table_extractor = TableExtractor(pages_text, default_year=self.report_year)
            self.answer_extractor = AnswerExtractor(self.table_extractor, pages_text, default_year=self.report_year)
            self.active_pdf_path = abs_path

            ocr_status = "active" if self.processor.ocr_processor.is_available() else "unavailable (tesseract/poppler not found)"
            logger.info(f"PDF loaded successfully. {self.num_pages} pages, report year {self.report_year}, OCR: {ocr_status}")
            return {
                "status": "ok",
                "pdf_path": abs_path,
                "num_pages": self.num_pages,
                "report_year": self.report_year,
                "ocr_status": ocr_status,
                "tables_indexed": list(self.table_extractor.tables.keys())
            }
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            return {"status": "error", "message": str(e)}

    def query(self, question: str, q_id: str = "custom"):
        if not self.answer_extractor:
            return {"status": "error", "message": "No active PDF loaded"}

        try:
            res = self.answer_extractor.extract_answer({"id": q_id, "question": question})
            analysis = QueryAnalysis(question, default_year=self.report_year)

            snippet = ""
            if res.get("page"):
                p_text = self.processor.get_page_text(res["page"])
                lines = [l for l in p_text.split('\n') if l.strip()]
                snippet = "\n".join(lines[:12])

            return {
                "status": "ok",
                "result": {
                    **res,
                    "query_analysis": {
                        "entity_type": analysis.entity_type,
                        "metric": analysis.metric,
                        "year": analysis.year,
                        "is_unanswerable": (res["answer"] == "NOT_FOUND")
                    },
                    "page_snippet": snippet
                }
            }
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {"status": "error", "message": str(e)}

    def get_page(self, page_num: int):
        if not self.processor:
            return {"status": "error", "message": "No active PDF loaded"}

        if page_num < 1 or page_num > self.num_pages:
            return {
                "status": "error",
                "message": f"Invalid page number {page_num}. Document has {self.num_pages} pages."
            }

        text = self.processor.get_page_text(page_num)
        return {
            "status": "ok",
            "page": page_num,
            "total_pages": self.num_pages,
            "text": text
        }

def main():
    engine = DaemonEngine()
    default_report = "public/assets/aistudio/report_A_90150542.pdf"
    if os.path.exists(default_report):
        engine.load_pdf(default_report, enable_ocr=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            action = msg.get("action")
            if action == "load_pdf":
                res = engine.load_pdf(msg.get("pdf_path", ""), enable_ocr=True)
            elif action == "query":
                res = engine.query(msg.get("question", ""), msg.get("id", "custom"))
            elif action == "get_page":
                res = engine.get_page(int(msg.get("page", 1)))
            elif action == "status":
                res = {
                    "status": "ok",
                    "active_pdf_path": engine.active_pdf_path,
                    "num_pages": engine.num_pages,
                    "report_year": engine.report_year
                }
            else:
                res = {"status": "error", "message": f"Unknown action: {action}"}
            print(json.dumps(res), flush=True)
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}), flush=True)

if __name__ == "__main__":
    main()
