# P5 – Report Navigator (LLM/RAG)

**CodeXHack – Hack Day Lucknow**

An offline PDF question-answering system for extracting numerical information from large statistical reports.

## 1. Problem Statement

Government statistical reports contain hundreds of pages of information, tables and numerical data.

Finding a specific statistic manually is difficult and time-consuming.

Major challenges include:

- Searching through lengthy PDF documents.
- Finding specific data inside complex tables.
- Extracting information from scanned PDF pages.
- Identifying the correct source page.
- Verifying whether an answer is supported by the document.

**Our Goal:** Build a system that allows users to ask questions about statistical PDF reports and receive numerical answers with supporting evidence and page citations.

## 2. Our Solution

Report Navigator allows users to:

- Upload a statistical PDF report.
- Ask questions in natural language.
- Extract relevant numerical answers.
- View the source PDF page number.
- Check supporting document evidence.
- Process scanned pages using OCR.

The system is designed for offline, CPU-based execution without cloud LLM API dependency during evaluation.

## 3. Project File Structure

```text
CodeX_Hack/
│
├── src/
│   ├── App.tsx
│   └── components/
│
├── solution/
│   ├── main.py
│   ├── query.py
│   ├── server_daemon.py
│   ├── pdf_processor.py
│   ├── ocr_processor.py
│   ├── table_extractor.py
│   ├── retriever.py
│   ├── answer_extractor.py
│   ├── confidence.py
│   ├── output_generator.py
│   └── README.md
│
├── data/
│   ├── questions_with_answers.jsonl
│   └── predictions.jsonl
│
├── public/
│   ├── assets/
│   └── downloads/
│
├── server.ts
├── package.json
└── README.md
```

### Important Files

| File | Purpose |
|---|---|
| `App.tsx` | Interactive ChatGPT-style frontend interface |
| `server.ts` | Express backend server with dynamic port binding |
| `main.py` | Main Python evaluation pipeline entry point |
| `query.py` | Question-answering and CLI logic |
| `server_daemon.py` | Real-time PDF processing daemon service |
| `output_generator.py` | Strict standard JSONL output generator |
| `questions_with_answers.jsonl` | Practice benchmark dataset |
| `predictions.jsonl` | Precomputed benchmark output data |
| `package.json` | Node.js dependencies and build scripts |

## 4. How It Works

```text
PDF Upload
    |
    v
PDF Processing
    |
    v
Text & Table Extraction
    |
    v
OCR for Scanned Pages
    |
    v
Question Processing
    |
    v
Relevant Data Retrieval
    |
    v
Numerical Answer Extraction
    |
    v
Answer + Page Citation + Evidence
```

## 5. Technology Stack

- Frontend: React 19, TypeScript, Tailwind CSS
- Backend: Node.js, Express, `tsx`
- Processing Engine: Python 3, PyPDF2 / pdfplumber, RapidFuzz
- OCR Engine: Tesseract OCR, PyTesseract, Poppler
- Build Tool: Vite
- Output Standard: JSONL

## 6. Output Format

Example:

```json
{"id":"Q1","answer":"12345","page":42,"confidence":0.95}
{"id":"Q2","answer":"NOT_FOUND","page":null,"confidence":0.20}
```

## 7. Practice Evaluation

Reported practice benchmark:

- Exact answer matches: 50/50 (100.0%)
- Correct page citations: 50/50 (100.0%)
- Reported execution time: 22.52 seconds with OCR disabled.

These results are from the practice dataset and do not guarantee performance on unseen reports.

## 8. Future Scope

- Improve OCR accuracy for heavily distorted historical scans.
- Support complex multi-page nested PDF table layouts.
- Enhance deep natural language query understanding.
- Support additional government and corporate statistical report formats.
- Improve automated answer verification and confidence scoring.

## 9. AI Tools Disclosure

AI tools were used during development for coding assistance, debugging, documentation and implementation refinement.

---

**Report Navigator – From hundreds of PDF pages to one verified answer.**
