# P5 · Report Navigator — public data (participant-facing)

- `report_A.pdf` — a long official statistical report (272 pages) with narrative text and many tables.
- `questions_with_answers.jsonl` — 50 example questions with gold answers and gold page numbers (`id, question, answer, answer_type, gold_pages, qtype`). Answers are integers written without commas, or `NOT_FOUND` when the report does not contain the answer.
- `sample_answers.jsonl` — output format: one JSON per line `{"id","answer","page","confidence"}`.

The hidden evaluation uses a DIFFERENT report of the same family (similar structure, different year, some pages are scanned images without a text layer) and 140 new questions.
