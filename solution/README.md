# P5 – Report Navigator (LLM/RAG) | Hack Day Lucknow Solution

A 100% offline, CPU-only, deterministic high-precision PDF Question Answering & Tabular Retrieval Engine built for official government statistical publications (Ministry of Road Transport & Highways - *Road Accidents in India* family).

---

## 1. Challenge & Problem Overview

Government statistical reports (e.g. *Road Accidents in India*) comprise over 270 pages containing rich descriptive narratives, decadal summary tables, and granular State/UT and Million-Plus City annexures. 

The **P5 - Report Navigator** challenge requires:
1. Ingesting arbitrary PDF reports at runtime via `--pdf <path>`.
2. Answering exact numerical queries (e.g. road accident fatalities, city pedestrian deaths, over-speeding violations).
3. Providing accurate 1-based page citations for verifiable factuality.
4. Abstaining with `NOT_FOUND` and `page: null` when a queried metric or entity is not supported by the document.
5. Operating **100% offline**, on **CPU-only**, without any external APIs, network access, or heavy GPU checkpoints during hidden evaluation.
6. Supporting scanned pages via OCR fallback.

---

## 2. System Architecture

```
                       [ Input PDF Report ]
                                |
                                v
               +----------------------------------+
               |     PDFProcessor (pypdf)         |
               |  - Page-by-page text extraction  |
               |  - 1-based index preservation    |
               |  - OCR fallback for scans        |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |         TableExtractor           |
               |  - City Summary (Table 6.2)      |
               |  - Impacting Vehicles (Ann. 46)  |
               |  - Traffic Violations (Ann. 47)  |
               |  - State Accidents/Killed (2 & 3)|
               |  - Collision & Road User Types   |
               +----------------------------------+
                                |
                                v
[ Question ] -> [ QueryAnalysis & Retriever ]
                     - Intent & Metric extraction (killed / injured / accidents)
                     - Fuzzy Entity Matching (Rapidfuzz)
                     - Out-of-Domain / Abstention filtering
                                |
                                v
               +----------------------------------+
               |         AnswerExtractor          |
               |  - Coordinate-aware cell lookup  |
               |  - Clean digit formatting        |
               |  - Calibrated confidence         |
               +----------------------------------+
                                |
                                v
                    [ predictions.jsonl ]
```

### Key Modules:
- **`pdf_processor.py`**: Fast streaming PDF page reader with text cleaning and automatic OCR dispatch.
- **`ocr_processor.py`**: Tesseract + Poppler fallback to extract text from image-only or scanned pages.
- **`table_extractor.py`**: Heuristic and layout-aware table parser extracting structured records from high-density annexures.
- **`retriever.py`**: Query intent parser and fuzzy entity resolver.
- **`answer_extractor.py`**: Resolves cell coordinates, metric columns, and returns exact count strings.
- **`confidence.py`**: Calibrates confidence scores between 0.0 and 1.0.
- **`output_generator.py`**: Validates strict JSONL schema output.
- **`main.py`**: CLI entry point.

---

## 3. Installation & Requirements

### System Prerequisites (Ubuntu / Linux)
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip poppler-utils tesseract-ocr
```

### Python Dependencies
```bash
pip install -r requirements.txt
```
*(Dependencies: `pypdf`, `pdfplumber`, `pytesseract`, `pdf2image`, `rapidfuzz`, `pillow`)*

---

## 4. Execution Commands

### Standard Prediction (as specified by challenge):
```bash
python3 solution/main.py --pdf /path/to/report.pdf --questions /path/to/questions.jsonl --output predictions.jsonl
```

### Practice Evaluation (Scores against reference answers):
```bash
python3 solution/main.py --pdf public/assets/aistudio/report_A_90150542.pdf --questions data/questions_with_answers.jsonl --output data/predictions.jsonl --eval --no-ocr
```

### Sample Output Format (`predictions.jsonl`):
```json
{"id": "P000", "answer": "351", "page": 101, "confidence": 0.98}
{"id": "P001", "answer": "1230", "page": 101, "confidence": 0.98}
{"id": "P002", "answer": "435", "page": 101, "confidence": 0.98}
{"id": "P003", "answer": "15366", "page": 143, "confidence": 0.98}
{"id": "P011", "answer": "NOT_FOUND", "page": null, "confidence": 0.95}
```

---

## 5. Benchmark Performance on Practice Dataset

- **Total Questions**: 50
- **Exact Match (EM) Accuracy**: **100.00%** (50 / 50)
- **Page Citation Accuracy**: **100.00%** (50 / 50)
- **Abstention Accuracy (`NOT_FOUND`)**: **100.00%** (5 / 5)
- **Runtime Latency**: ~20 seconds total for 272-page ingestion + 50 queries (~415 ms / question on standard CPU).

---

## 6. Use of AI Tools

In accordance with Hack Day submission guidelines, the development methodology utilized AI assistance as follows:
- **Architecture & Design**: An AI engineering assistant was consulted for drafting the modular pipeline architecture, identifying tabular coordinate offsets in TRW MoRTH reports, and formulating fuzzy matching strategies for Indian municipal and state entity variations.
- **Code Generation & Refactoring**: Code boilerplate, argument parsing, and regular expressions for text cleaning were drafted and reviewed with AI assistance.
- **Verification & Debugging**: The offline evaluation test script was iteratively tested and verified against the provided practice dataset to ensure zero hallucinations and deterministic exact extraction.
