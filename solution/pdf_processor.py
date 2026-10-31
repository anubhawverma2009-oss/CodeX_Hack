"""
PDF Processor for P5 - Report Navigator.
Handles PDF ingestion, page-by-page text extraction, normalization,
and OCR fallback for scanned pages.
"""
import os
import re
import logging
from typing import Dict, List, Optional
import pypdf

from ocr_processor import OCRProcessor

logger = logging.getLogger("PDFProcessor")

class PDFProcessor:
    def __init__(self, pdf_path: str, enable_ocr: bool = True):
        self.pdf_path = pdf_path
        self.enable_ocr = enable_ocr
        self.ocr_processor = OCRProcessor()
        self.pages_text: Dict[int, str] = {}
        self.num_pages: int = 0
        self._load_document()

    def _load_document(self):
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF not found at {self.pdf_path}")

        reader = pypdf.PdfReader(self.pdf_path)
        self.num_pages = len(reader.pages)
        logger.info(f"Loaded PDF with {self.num_pages} pages: {self.pdf_path}")

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            extracted = page.extract_text() or ""
            extracted = extracted.strip()

            # Check if page text is essentially empty (scanned image page)
            if len(extracted) < 30 and self.enable_ocr and self.ocr_processor.is_available():
                logger.info(f"Page {page_num} has sparse text ({len(extracted)} chars). Running OCR...")
                ocr_text = self.ocr_processor.ocr_page(self.pdf_path, page_num)
                if len(ocr_text.strip()) > len(extracted):
                    extracted = ocr_text.strip()

            self.pages_text[page_num] = extracted

    def get_page_text(self, page_num: int) -> str:
        """Returns normalized text for a 1-based page number."""
        return self.pages_text.get(page_num, "")

    def get_all_pages(self) -> Dict[int, str]:
        return self.pages_text

    @staticmethod
    def clean_number_string(val_str: str) -> str:
        """
        Removes commas, spaces, currency symbols, and converts to pure digits.
        Example: '1,50,177' -> '150177', '1230' -> '1230'
        """
        cleaned = re.sub(r"[,\s]", "", val_str)
        # Match only integer digits
        match = re.search(r"^\d+", cleaned)
        if match:
            return match.group(0)
        return cleaned
