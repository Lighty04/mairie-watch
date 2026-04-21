import httpx
import re
from bs4 import BeautifulSoup
from datetime import datetime
import os

from app.models import Decision, SessionLocal

BASE_URL = "https://a06-v7.apps.paris.fr/a06/jsp/site/Portal.jsp"
SEARCH_URL = f"{BASE_URL}?page=search-solr&items_per_page=20&sort_name=date&sort_order=desc"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")
os.makedirs(DATA_DIR, exist_ok=True)

async def fetch_search_results(query: str = "", page_index: int = 1, items_per_page: int = 20):
    """Fetch search results from Débat-Délibs portal."""
    params = {
        "page": "search-solr",
        "items_per_page": items_per_page,
        "sort_name": "date",
        "sort_order": "desc",
        "page_index": page_index,
    }
    if query:
        params["query"] = query

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(BASE_URL, params=params, headers={"User-Agent": "MairieWatch/0.1"})
        resp.raise_for_status()
        return resp.text

def parse_decisions(html: str):
    """Parse Débat-Délibs HTML into decision dicts."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for item in soup.find_all("div", class_="itemODS"):
        # Title
        h3 = item.find("h3")
        title = h3.get_text(strip=True) if h3 else None

        # PDF link
        pdf_link = item.find("a", href=re.compile(r"DoDownload\.jsp.*id_document="))
        pdf_url = None
        if pdf_link:
            href = pdf_link.get("href", "")
            # Make absolute URL
            if href.startswith("jsp/"):
                pdf_url = f"https://a06-v7.apps.paris.fr/a06/{href}"
            elif href.startswith("/"):
                pdf_url = f"https://a06-v7.apps.paris.fr{href}"
            else:
                pdf_url = href

        # Extract decision number and date from content
        content_div = item.find("div", class_="itemODS_content")
        content_text = content_div.get_text(" ", strip=True) if content_div else ""

        # Parse decision number like "2026 DDCT 69"
        decision_number = None
        number_match = re.search(r'(\d{4}\s+[A-Z]+\s+\d+(?:-\d+)?)', content_text)
        if number_match:
            decision_number = number_match.group(1)

        # Parse date like "14 avril 2026" or "15 avril 2026"
        published_at = None
        date_match = re.search(r'Séance du (\d{1,2})\s+([a-zéû]+)\s+(\d{4})', content_text, re.IGNORECASE)
        if date_match:
            day, month_str, year = date_match.groups()
            month_map = {
                'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4,
                'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8,
                'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12
            }
            month = month_map.get(month_str.lower(), 1)
            try:
                published_at = datetime(int(year), month, int(day))
            except ValueError:
                pass

        if pdf_url and title:
            results.append({
                "title": title,
                "pdf_url": pdf_url,
                "source_url": SEARCH_URL,
                "decision_number": decision_number,
                "published_at": published_at,
                "content_preview": content_text[:500] if content_text else None,
            })

    return results

async def download_pdf(pdf_url: str) -> str:
    """Download PDF to local storage, return filepath."""
    # Extract id_document from URL for filename
    match = re.search(r'id_document=(\d+)', pdf_url)
    if match:
        filename = f"paris_delib_{match.group(1)}.pdf"
    else:
        filename = f"{datetime.utcnow().timestamp()}.pdf"

    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        return filepath

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(pdf_url, headers={"User-Agent": "MairieWatch/0.1"})
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
    return filepath

async def scrape_and_store(query: str = "", page_index: int = 1):
    """Scrape decisions and store in database."""
    html = await fetch_search_results(query=query, page_index=page_index)
    decisions = parse_decisions(html)

    db = SessionLocal()
    try:
        new_count = 0
        for d in decisions:
            exists = db.query(Decision).filter_by(pdf_url=d["pdf_url"]).first()
            if exists:
                continue

            filepath = await download_pdf(d["pdf_url"])
            decision = Decision(
                source_url=d["source_url"],
                pdf_url=d["pdf_url"],
                title=d["title"],
                published_at=d.get("published_at"),
                metadata_json={
                    "local_path": filepath,
                    "decision_number": d.get("decision_number"),
                    "content_preview": d.get("content_preview"),
                },
            )
            db.add(decision)
            new_count += 1
        db.commit()
        return {"scraped": len(decisions), "new": new_count}
    finally:
        db.close()
