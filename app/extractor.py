import os
from app.models import Decision, SessionLocal
from app.ocr import smart_extract

def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF using smart extraction (pdfplumber + OCR fallback)."""
    return smart_extract(filepath)

def process_pending_decisions(limit: int = 50):
    """Extract text from all unprocessed decisions."""
    db = SessionLocal()
    try:
        pending = db.query(Decision).filter_by(processed=False).limit(limit).all()
        for decision in pending:
            filepath = decision.metadata_json.get("local_path") if decision.metadata_json else None
            if not filepath or not os.path.exists(filepath):
                continue
            text = extract_text_from_pdf(filepath)
            decision.raw_text = text
            decision.processed = True
            db.add(decision)
        db.commit()
        return len(pending)
    finally:
        db.close()
