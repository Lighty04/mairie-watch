"""OCR fallback for scanned PDFs that pdfplumber can't extract text from."""

import subprocess
import os
import tempfile
import logging

logger = logging.getLogger("mairie-watch")

def needs_ocr(filepath: str) -> bool:
    """Check if a PDF has no extractable text (likely scanned/image-based)."""
    import pdfplumber
    try:
        with pdfplumber.open(filepath) as pdf:
            total_chars = 0
            for page in pdf.pages[:3]:  # Check first 3 pages
                text = page.extract_text() or ""
                total_chars += len(text.strip())
            return total_chars < 50  # Less than 50 chars = probably scanned
    except Exception:
        return True

def extract_with_ocr(filepath: str) -> str:
    """Extract text from scanned PDF using OCR (requires tesseract + poppler)."""
    if not os.path.exists(filepath):
        return "[OCR_ERROR: File not found]"
    
    # Try pdftotext first (faster, handles some image PDFs)
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", filepath, "-"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and len(result.stdout.strip()) > 100:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback: convert to images then OCR with tesseract
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Convert PDF to images using pdftoppm
            subprocess.run(
                ["pdftoppm", "-png", filepath, os.path.join(tmpdir, "page")],
                capture_output=True, timeout=60, check=True
            )
            
            # OCR each page with tesseract
            pages = []
            for img in sorted(os.listdir(tmpdir)):
                if img.endswith(".png"):
                    result = subprocess.run(
                        ["tesseract", os.path.join(tmpdir, img), "-", "-l", "fra"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        pages.append(result.stdout)
            
            return "\n".join(pages) if pages else "[OCR_ERROR: No text extracted]"
    except FileNotFoundError:
        logger.warning("OCR tools not installed (tesseract/pdftoppm). Skipping OCR.")
        return "[OCR_ERROR: OCR tools not installed]"
    except subprocess.TimeoutExpired:
        return "[OCR_ERROR: OCR timed out]"
    except Exception as e:
        return f"[OCR_ERROR: {e}]"

def smart_extract(filepath: str) -> str:
    """Extract text from PDF. Falls back to OCR if no text found."""
    import pdfplumber
    
    # Try normal extraction first
    text_parts = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        return f"[EXTRACTION_ERROR: {e}]"
    
    text = "\n".join(text_parts)
    
    # If very little text, try OCR
    if len(text.strip()) < 100:
        logger.info(f"PDF has little text ({len(text.strip())} chars), trying OCR: {filepath}")
        ocr_text = extract_with_ocr(filepath)
        if not ocr_text.startswith("[OCR_ERROR"):
            return ocr_text
    
    return text
