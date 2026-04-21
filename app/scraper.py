import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import os

from app.models import Decision, SessionLocal

PARIS_DECISIONS_URL = "https://www.paris.fr/decisions"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")
os.makedirs(DATA_DIR, exist_ok=True)

async def fetch_decisions_page():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(PARIS_DECISIONS_URL, headers={"User-Agent": "MairieWatch/0.1"})
        resp.raise_for_status()
        return resp.text

def parse_decision_links(html: str):
    soup = BeautifulSoup(html, "html.parser")
    decisions = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if ".pdf" in href.lower():
            title = link.get_text(strip=True) or href.split("/")[-1]
            decisions.append({
                "title": title,
                "pdf_url": href if href.startswith("http") else f"https://www.paris.fr{href}",
                "source_url": PARIS_DECISIONS_URL,
            })
    return decisions

async def download_pdf(pdf_url: str) -> str:
    filename = pdf_url.split("/")[-1].split("?")[0] or f"{datetime.utcnow().timestamp()}.pdf"
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        return filepath
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(pdf_url, headers={"User-Agent": "MairieWatch/0.1"})
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
    return filepath

async def scrape_and_store():
    html = await fetch_decisions_page()
    decisions = parse_decision_links(html)
    db = SessionLocal()
    try:
        for d in decisions:
            exists = db.query(Decision).filter_by(pdf_url=d["pdf_url"]).first()
            if exists:
                continue
            filepath = await download_pdf(d["pdf_url"])
            decision = Decision(
                source_url=d["source_url"],
                pdf_url=d["pdf_url"],
                title=d["title"],
                metadata_json={"local_path": filepath},
            )
            db.add(decision)
        db.commit()
    finally:
        db.close()
    return len(decisions)
