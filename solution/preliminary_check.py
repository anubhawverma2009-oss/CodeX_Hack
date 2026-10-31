#!/usr/bin/env python3
"""
Prototype testing script for P5 practice questions.
"""
import json
import re
import pypdf
from rapidfuzz import fuzz

def load_practice_questions(filepath="data/questions_with_answers.jsonl"):
    questions = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions

def run_preliminary_check():
    questions = load_practice_questions()
    print(f"Loaded {len(questions)} questions")
    
    qtypes = {}
    for q in questions:
        qt = q.get("qtype", "unknown")
        qtypes[qt] = qtypes.get(qt, 0) + 1
    
    print("\nQuestion types distribution:")
    for qt, count in sorted(qtypes.items(), key=lambda x: -x[1]):
        print(f"  {qt}: {count}")

if __name__ == "__main__":
    run_preliminary_check()
