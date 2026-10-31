#!/usr/bin/env python3
"""
P5 – Report Navigator (LLM/RAG) | Main Execution Entry Point
Hack Day Lucknow Competition Solution

Usage:
  python3 solution/main.py --pdf <path_to_pdf> --questions <path_to_questions.jsonl> --output <path_to_predictions.jsonl>
"""
import sys
import os
import argparse
import json
import time

# Ensure solution dir is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_processor import PDFProcessor
from table_extractor import TableExtractor
from answer_extractor import AnswerExtractor
from output_generator import OutputGenerator

def parse_args():
    parser = argparse.ArgumentParser(description="P5 Report Navigator (LLM/RAG) Offline Extraction Engine")
    parser.add_argument("--pdf", required=True, help="Path to the PDF report file")
    parser.add_argument("--questions", required=True, help="Path to input questions JSONL file")
    parser.add_argument("--output", default="predictions.jsonl", help="Path to output predictions JSONL file")
    parser.add_argument("--eval", action="store_true", help="Evaluate against gold answers if present")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback")
    return parser.parse_args()

def run_pipeline(pdf_path: str, questions_path: str, output_path: str, eval_mode: bool = False, enable_ocr: bool = True):
    start_time = time.time()
    print(f"===========================================================")
    print(f" P5 Report Navigator (LLM/RAG) — Offline Evaluation Engine")
    print(f" PDF: {pdf_path}")
    print(f" Questions: {questions_path}")
    print(f" Output: {output_path}")
    print(f"===========================================================")

    # 1. Ingest PDF
    print("[1/4] Ingesting and indexing PDF pages...")
    pdf_proc = PDFProcessor(pdf_path=pdf_path, enable_ocr=enable_ocr)
    pages_text = pdf_proc.get_all_pages()
    report_year = pdf_proc.report_year
    print(f"      Total indexed pages: {len(pages_text)} | Detected Report Year: {report_year}")

    # 2. Extract and index tables
    print("[2/4] Parsing structured tables and statistical annexures...")
    table_extractor = TableExtractor(pages_text, default_year=report_year)
    print(f"      Indexed {len(table_extractor.tables)} table sections: {list(table_extractor.tables.keys())}")

    # 3. Answer questions
    print("[3/4] Processing queries and extracting answers...")
    answer_extractor = AnswerExtractor(table_extractor, pages_text, default_year=report_year)

    questions = []
    with open(questions_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    predictions = []
    correct_answers = 0
    correct_pages = 0
    total = len(questions)

    for q in questions:
        pred = answer_extractor.extract_answer(q)
        predictions.append(pred)

        if eval_mode and "answer" in q:
            gold_ans = str(q.get("answer", "")).strip()
            gold_pages = q.get("gold_pages", [])
            pred_ans = str(pred["answer"]).strip()
            pred_page = pred["page"]

            ans_match = (pred_ans == gold_ans)
            page_match = (pred_page in gold_pages) if gold_pages else (pred_page is None)

            if ans_match:
                correct_answers += 1
            if page_match:
                correct_pages += 1

            status = "✓" if ans_match and page_match else "✗"
            print(f"  [{status}] {q.get('id', '')}: Pred='{pred_ans}' (P.{pred_page}) | Gold='{gold_ans}' (P.{gold_pages})")

    # 4. Generate JSONL output
    print(f"[4/4] Writing predictions to {output_path}...")
    OutputGenerator.write_jsonl(predictions, output_path)

    elapsed = time.time() - start_time
    print(f"\nExecution completed in {elapsed:.2f} seconds ({elapsed/max(1, total)*1000:.1f} ms/question)")

    if eval_mode:
        print("\n" + "="*45)
        print("          EVALUATION SCORECARD")
        print("="*45)
        print(f" Total Questions:        {total}")
        print(f" Exact Match Accuracy:   {correct_answers}/{total} ({correct_answers/total*100:.2f}%)")
        print(f" Page Citation Accuracy: {correct_pages}/{total} ({correct_pages/total*100:.2f}%)")
        print("="*45)

def main():
    args = parse_args()
    run_pipeline(
        pdf_path=args.pdf,
        questions_path=args.questions,
        output_path=args.output,
        eval_mode=args.eval,
        enable_ocr=not args.no_ocr
    )

if __name__ == "__main__":
    main()
