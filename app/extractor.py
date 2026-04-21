import pdfplumber
import os
from app.models import Decision, SessionLocal

def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF using pdfplumber."""
    text_parts = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        return f"[EXTRACTION_ERROR: {e}]"
    return "\n".join(text_parts)

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
