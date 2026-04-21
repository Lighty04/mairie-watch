"""City configuration and multi-city scraper framework.

Defines city-specific scraping configurations and a base scraper class
that city-specific scrapers extend.
"""

import re
import httpx
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# City configurations
# ---------------------------------------------------------------------------

CITY_CONFIGS: Dict[str, Dict[str, Any]] = {
    "paris": {
        "name": "Paris",
        "name_fr": "Ville de Paris",
        "portal_url": "https://www.paris.fr/debat-d-elus/debat-d-elus/",
        "pdf_base_url": "https://cdn.paris.fr/",
        "scraping_strategy": "paris_debat_delibs",
        "arrondissements": 20,
        "population": 2_165_000,
        "region": "Île-de-France",
        "enabled": True,
    },
    "marseille": {
        "name": "Marseille",
        "name_fr": "Ville de Marseille",
        "portal_url": "https://www.marseille.fr/",
        "pdf_base_url": None,
        "scraping_strategy": "marseille",
        "arrondissements": 16,  # 8 arrondissements × 2 secteurs
        "population": 870_000,
        "region": "Provence-Alpes-Côte d'Azur",
        "enabled": True,
    },
    "lyon": {
        "name": "Lyon",
        "name_fr": "Ville de Lyon",
        "portal_url": "https://www.lyon.fr/",
        "pdf_base_url": None,
        "scraping_strategy": "lyon",
        "arrondissements": 9,
        "population": 515_000,
        "region": "Auvergne-Rhône-Alpes",
        "enabled": True,
    },
    "bordeaux": {
        "name": "Bordeaux",
        "name_fr": "Ville de Bordeaux",
        "portal_url": "https://www.bordeaux.fr/",
        "pdf_base_url": None,
        "scraping_strategy": "bordeaux",
        "arrondissements": 0,
        "population": 260_000,
        "region": "Nouvelle-Aquitaine",
        "enabled": False,
    },
}

def get_enabled_cities() -> List[str]:
    """Return list of enabled city slugs."""
    return [slug for slug, cfg in CITY_CONFIGS.items() if cfg.get("enabled", True)]

def get_city_config(city_slug: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific city."""
    return CITY_CONFIGS.get(city_slug)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def fetch_html(url: str, timeout: int = 30) -> str:
    """Fetch HTML content from a URL."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.text

# ---------------------------------------------------------------------------
# Base scraper class
# ---------------------------------------------------------------------------

@dataclass
class ScrapedDecision:
    """Represents a single scraped decision before storage."""
    city: str
    title: str
    pdf_url: Optional[str]
    published_at: Optional[datetime]
    raw_html: str
    external_id: Optional[str] = None
    metadata: Dict[str, Any] = None

class CityScraper(ABC):
    """Base class for city-specific scrapers."""
    
    def __init__(self, city_slug: str):
        self.city_slug = city_slug
        self.config = get_city_config(city_slug)
        if not self.config:
            raise ValueError(f"Unknown city: {city_slug}")
    
    @abstractmethod
    async def get_portal_url(self, page: int = 1) -> str:
        """Return the portal URL for the given page."""
        pass
    
    @abstractmethod
    async def parse_decisions_page(self, html: str) -> List[ScrapedDecision]:
        """Parse a portal page and extract decision metadata."""
        pass
    
    @abstractmethod
    def get_pdf_url(self, decision_element) -> Optional[str]:
        """Extract the PDF URL from a decision element."""
        pass
    
    @abstractmethod
    def extract_metadata(self, decision_element) -> Dict[str, Any]:
        """Extract metadata (date, arrondissement, etc.) from a decision element."""
        pass
    
    async def scrape_page(self, page: int = 1) -> List[ScrapedDecision]:
        """Scrape a single page of decisions."""
        url = await self.get_portal_url(page)
        html = await fetch_html(url)
        return await self.parse_decisions_page(html)
    
    async def scrape_all(self, max_pages: int = 5) -> List[ScrapedDecision]:
        """Scrape multiple pages of decisions."""
        all_decisions = []
        for page in range(1, max_pages + 1):
            decisions = await self.scrape_page(page)
            if not decisions:
                break
            all_decisions.extend(decisions)
        return all_decisions

# ---------------------------------------------------------------------------
# Paris Scraper
# ---------------------------------------------------------------------------

class ParisScraper(CityScraper):
    """Scraper for Paris Débat-Délibs portal."""
    
    def __init__(self):
        super().__init__("paris")
    
    async def get_portal_url(self, page: int = 1) -> str:
        base = self.config["portal_url"]
        return f"{base}?page={page}"
    
    async def parse_decisions_page(self, html: str) -> List[ScrapedDecision]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        decisions = []
        
        for row in soup.select(".decision-row, .result-item, tr"):
            # Try to extract title
            title_tag = row.select_one("a, .title, h3, h4, td:nth-child(2)")
            if not title_tag:
                continue
            
            title = title_tag.get_text(strip=True)
            pdf_url = self.get_pdf_url(title_tag)
            meta = self.extract_metadata(row)
            
            published_at = meta.get("published_at")
            if isinstance(published_at, str):
                # Try to parse date string
                for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d %B %Y"]:
                    try:
                        published_at = datetime.strptime(published_at, fmt)
                        break
                    except ValueError:
                        continue
            
            decisions.append(ScrapedDecision(
                city="paris",
                title=title,
                pdf_url=pdf_url,
                published_at=published_at if isinstance(published_at, datetime) else None,
                raw_html=str(row),
                external_id=meta.get("external_id"),
                metadata=meta,
            ))
        
        return decisions
    
    def get_pdf_url(self, decision_element) -> Optional[str]:
        # Look for PDF link in the element or parent
        link = decision_element.find("a", href=re.compile(r"\.pdf$", re.I))
        if link:
            href = link.get("href", "")
            if href.startswith("http"):
                return href
            base = self.config.get("pdf_base_url", "")
            return f"{base}{href}" if base else href
        return None
    
    def extract_metadata(self, decision_element) -> Dict[str, Any]:
        meta = {}
        text = decision_element.get_text()
        
        # Extract date
        date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
        if date_match:
            try:
                meta["published_at"] = datetime.strptime(date_match.group(0), "%d/%m/%Y")
            except ValueError:
                meta["published_at"] = date_match.group(0)
        
        # Extract arrondissement
        arr_match = re.search(r'(\d{1,2})(?:er|e|ème)?\s*arrondissement', text, re.I)
        if arr_match:
            meta["arrondissement"] = int(arr_match.group(1))
        
        return meta

# ---------------------------------------------------------------------------
# Marseille Scraper (placeholder — will be implemented when portal analyzed)
# ---------------------------------------------------------------------------

class MarseilleScraper(CityScraper):
    """Scraper for Marseille municipal decisions."""
    
    def __init__(self):
        super().__init__("marseille")
    
    async def get_portal_url(self, page: int = 1) -> str:
        # Marseille uses a different URL pattern — needs analysis
        base = self.config["portal_url"]
        # Placeholder: assume similar pagination
        return f"{base}deliberations?page={page}"
    
    async def parse_decisions_page(self, html: str) -> List[ScrapedDecision]:
        # TODO: Implement when Marseille portal structure is analyzed
        # For now, return empty list (graceful degradation)
        return []
    
    def get_pdf_url(self, decision_element) -> Optional[str]:
        return None
    
    def extract_metadata(self, decision_element) -> Dict[str, Any]:
        return {}

# ---------------------------------------------------------------------------
# Lyon Scraper (placeholder — will be implemented when portal analyzed)
# ---------------------------------------------------------------------------

class LyonScraper(CityScraper):
    """Scraper for Lyon municipal decisions."""
    
    def __init__(self):
        super().__init__("lyon")
    
    async def get_portal_url(self, page: int = 1) -> str:
        base = self.config["portal_url"]
        return f"{base}deliberations?page={page}"
    
    async def parse_decisions_page(self, html: str) -> List[ScrapedDecision]:
        # TODO: Implement when Lyon portal structure is analyzed
        return []
    
    def get_pdf_url(self, decision_element) -> Optional[str]:
        return None
    
    def extract_metadata(self, decision_element) -> Dict[str, Any]:
        return {}

# ---------------------------------------------------------------------------
# Scraper factory
# ---------------------------------------------------------------------------

SCRAPER_REGISTRY: Dict[str, type] = {
    "paris": ParisScraper,
    "marseille": MarseilleScraper,
    "lyon": LyonScraper,
}

def get_scraper(city_slug: str) -> CityScraper:
    """Get the appropriate scraper for a city."""
    scraper_class = SCRAPER_REGISTRY.get(city_slug)
    if not scraper_class:
        raise ValueError(f"No scraper registered for city: {city_slug}")
    return scraper_class()

def get_all_scrapers() -> List[CityScraper]:
    """Get scrapers for all enabled cities."""
    scrapers = []
    for slug in get_enabled_cities():
        if slug in SCRAPER_REGISTRY:
            try:
                scrapers.append(get_scraper(slug))
            except Exception as e:
                print(f"Warning: Failed to initialize scraper for {slug}: {e}")
    return scrapers

# ---------------------------------------------------------------------------
# Backward-compatible import
# ---------------------------------------------------------------------------

# Re-export the old scrape_and_store function for compatibility
async def scrape_and_store(limit: int = 50):
    """Backwards-compatible scraper for Paris."""
    scraper = ParisScraper()
    decisions = await scraper.scrape_all(max_pages=5)
    return store_scraped_decisions(decisions)

def store_scraped_decisions(decisions: List[ScrapedDecision]) -> Dict[str, int]:
    """Store scraped decisions in the database."""
    from app.models import SessionLocal, Decision
    
    db = SessionLocal()
    try:
        new_count = 0
        for sd in decisions:
            # Check for duplicates by external_id or title+date
            existing = db.query(Decision).filter(
                (Decision.external_id == sd.external_id) if sd.external_id else False
            ).first()
            
            if not existing and sd.title:
                existing = db.query(Decision).filter(
                    Decision.title == sd.title,
                    Decision.published_at == sd.published_at,
                ).first()
            
            if existing:
                # Update city if not set
                if not existing.city:
                    existing.city = sd.city
                    db.commit()
                continue
            
            decision = Decision(
                city=sd.city,
                title=sd.title,
                pdf_url=sd.pdf_url,
                published_at=sd.published_at,
                external_id=sd.external_id,
            )
            db.add(decision)
            new_count += 1
        
        db.commit()
        return {"scraped": len(decisions), "new": new_count}
    finally:
        db.close()

async def scrape_all_cities(limit_per_city: int = 50) -> Dict[str, Dict[str, int]]:
    """Scrape all enabled cities and store results."""
    results = {}
    scrapers = get_all_scrapers()
    
    for scraper in scrapers:
        city = scraper.city_slug
        try:
            decisions = await scraper.scrape_all(max_pages=5)
            stats = store_scraped_decisions(decisions)
            results[city] = stats
        except Exception as e:
            results[city] = {"error": str(e), "scraped": 0, "new": 0}
    
    return results
