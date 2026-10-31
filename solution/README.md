# P5 – Report Navigator (LLM/RAG) | Hack Day Lucknow Solution

A 100% offline, CPU-only, deterministic high-precision PDF Question Answering & Tabular Retrieval Engine built for official government statistical publications (Ministry of Road Transport & Highways - *Road Accidents in India* report family).

---

## 1. Project Overview & Problem Statement

Government statistical publications span hundreds of pages of dense narrative, decadal summary tables, and granular State/UT and Million-Plus City annexures. 

The **P5 - Report Navigator** challenge requires:
1. Ingesting arbitrary PDF reports at runtime via `--pdf <path>`.
2. Answering exact numerical queries (e.g. road accident fatalities, city pedestrian deaths, over-speeding violations).
3. Providing accurate 1-based page citations for verifiable factuality.
4. Abstaining with `NOT_FOUND` and `page: null` when a queried metric or entity is not supported by the document.
5. Operating **100% offline**, on **CPU-only**, without any external APIs, network access, or heavy GPU checkpoints during evaluation.
6. Supporting scanned pages via automated OCR fallback.

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
               |  - OCR fallback (Tesseract/Poppler)|
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
                     - Rapidfuzz fuzzy entity matching & word boundary checks
                     - Document evidence verification
                                |
                                v
               +----------------------------------+
               |         AnswerExtractor          |
               |  - Coordinate-aware cell lookup  |
               |  - Dynamic column offset handler |
               |  - Integer formatting (no commas)|
               +----------------------------------+
                                |
                                v
                    [ predictions.jsonl ]
```

### Modular Components:
- **`pdf_processor.py`**: Streaming PDF page reader with text cleaning, dynamic year detection, and automatic OCR fallback for scanned pages.
- **`ocr_processor.py`**: Tesseract OCR + Poppler integration for image-only PDF pages.
- **`table_extractor.py`**: Heuristic and layout-aware table parser extracting structured records from multi-dimensional annexures.
- **`retriever.py`**: Query intent parser, entity resolver, and document evidence validator.
- **`answer_extractor.py`**: Resolves cell coordinates, metric columns, and returns exact count strings.
- **`confidence.py`**: Calibrates confidence scores between 0.0 and 1.0.
- **`output_generator.py`**: Strict JSONL schema validator ensuring correct keys, types, and abstention rules.
- **`server_daemon.py`**: Persistent Python background worker for sub-second web queries and page inspections.
- **`main.py`**: Standalone CLI entry point for batch evaluation.

---

## 3. Prerequisites & Installation

### System Prerequisites (Ubuntu / Linux)
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip poppler-utils tesseract-ocr
```

### Python Dependencies
```bash
pip install -r solution/requirements.txt
```
*(Dependencies: `pypdf`, `pdfplumber`, `pytesseract`, `pdf2image`, `rapidfuzz`, `pillow`)*

### Node.js Dependencies (for Web UI & Express Bridge)
```bash
npm install
```

---

## 4. Execution Commands

### Standalone CLI Evaluation (Competition Standard):
```bash
python3 solution/main.py --pdf /path/to/report.pdf --questions /path/to/questions.jsonl --output predictions.jsonl
```

### Practice Evaluation (Scores against reference answers):
```bash
python3 solution/main.py --pdf public/assets/aistudio/report_A_90150542.pdf --questions data/questions_with_answers.jsonl --output data/predictions.jsonl --eval
```

---

## 5. PDF Upload & Query Workflow (Web UI)
1. Start the development/production server: `npm run dev` (runs on port 3000).
2. Open the UI in your browser.
3. In the **Interactive QA Playground**, click **Upload Custom PDF** to select any report PDF from your device.
4. The backend streams the upload safely to disk, validates the `%PDF` signature, and indexes the document in-memory with OCR enabled.
5. Enter any question or click quick test pills to perform live deterministic inference.

---

## 6. JSONL Output Format Specification
Every prediction emitted in `predictions.jsonl` strictly adheres to:
```json
{"id": "P000", "answer": "351", "page": 101, "confidence": 0.98}
{"id": "P011", "answer": "NOT_FOUND", "page": null, "confidence": 0.95}
```
- **`id`**: Non-empty string.
- **`answer`**: Digits-only string or exactly `"NOT_FOUND"`.
- **`page`**: Positive integer (1-based) or `null` (strictly `null` when answer is `"NOT_FOUND"`).
- **`confidence`**: Floating-point number between `0.0` and `1.0`.

---

## 7. Use of AI Tools Disclosure
In accordance with Hack Day guidelines, AI tools were utilized during development for:
- System architecture planning and modular separation.
- Crafting regular expressions and fuzzy entity matching for Indian statistical annexures.
- Verification and testing against the 50 practice questions.
The runtime execution is 100% deterministic, offline, CPU-only, and makes zero API calls during evaluation.
