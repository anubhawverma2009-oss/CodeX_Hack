"""
OCR Processor for P5 - Report Navigator.
Provides optical character recognition fallback for scanned PDF pages
using poppler (pdf2image) and pytesseract.
"""
import os
import logging
from typing import Optional

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger("OCRProcessor")

class OCRProcessor:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd and OCR_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._cache = {}

    def is_available(self) -> bool:
        return OCR_AVAILABLE

    def ocr_page(self, pdf_path: str, page_number_1based: int) -> str:
        """
        Renders a single PDF page to an image and runs OCR via Tesseract.
        """
        if not OCR_AVAILABLE:
            logger.warning("OCR tools not available in environment.")
            return ""

        cache_key = (os.path.abspath(pdf_path), page_number_1based)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Convert only the single target page
            images = convert_from_path(
                pdf_path,
                first_page=page_number_1based,
                last_page=page_number_1based,
                dpi=200
            )
            if not images:
                return ""
            
            text = pytesseract.image_to_string(images[0], config="--psm 6")
            self._cache[cache_key] = text
            return text
        except Exception as e:
            logger.error(f"Error during OCR of page {page_number_1based}: {e}")
            return ""
