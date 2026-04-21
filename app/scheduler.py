from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime

from app.models import Decision, SessionLocal, init_db
from app.city_scrapers import scrape_all_cities, get_enabled_cities
from app.scraper import scrape_and_store
from app.extractor import process_pending_decisions
from app.classifier import classify_pending_decisions
from app.alerts import run_alerts_for_new_decisions

logger = logging.getLogger("mairie-watch")

async def run_pipeline(use_llm: bool = False, all_cities: bool = True):
    """Run the full pipeline: scrape → extract → classify → alert.
    
    Args:
        use_llm: Whether to use LLM for classification
        all_cities: If True, scrape all enabled cities. If False, scrape Paris only.
    """
    init_db()  # Ensure tables exist (safe to call multiple times)
    
    # Scrape
    if all_cities:
        logger.info("Starting multi-city pipeline")
        city_results = await scrape_all_cities(limit_per_city=50)
        total_scraped = sum(r.get("scraped", 0) for r in city_results.values())
        total_new = sum(r.get("new", 0) for r in city_results.values())
        logger.info(f"Scraped {total_scraped} decisions across {len(city_results)} cities, {total_new} new")
    else:
        logger.info("Starting Paris-only pipeline")
        scrape_result = await scrape_and_store(query=str(datetime.now().year))
        total_scraped = scrape_result["scraped"]
        total_new = scrape_result["new"]
        logger.info(f"Scraped {total_scraped} decisions, {total_new} new")

    logger.info("Extracting PDFs")
    extracted = process_pending_decisions()
    logger.info(f"Extracted {extracted} PDFs")

    if use_llm:
        from app.llm_classifier import classify_single_decision
        logger.info("Classifying decisions with LLM")
        db = SessionLocal()
        try:
            pending = (
                db.query(Decision)
                .filter(Decision.processed == True)
                .filter(Decision.category == None)
                .limit(50)
                .all()
            )
            for decision in pending:
                await classify_single_decision(decision.id)
            logger.info(f"LLM-classified {len(pending)} decisions")
        finally:
            db.close()
    else:
        logger.info("Classifying decisions (keyword-based)")
        classified = classify_pending_decisions()
        logger.info(f"Classified {classified} decisions")

    logger.info("Running alerts")
    alerted = run_alerts_for_new_decisions()
    logger.info(f"Generated {alerted} alerts")

    return {
        "scraped": total_scraped,
        "new": total_new,
        "extracted": extracted,
        "classified": classified if not use_llm else len(pending),
        "alerted": alerted,
        "cities": city_results if all_cities else {"paris": {"scraped": total_scraped, "new": total_new}},
    }

scheduler = AsyncIOScheduler()

def start_scheduler():
    """Start the background scheduler."""
    try:
        scheduler.add_job(run_pipeline, IntervalTrigger(minutes=30), id="pipeline", replace_existing=True)
        scheduler.start()
        logger.info("Scheduler started (30min interval)")
    except RuntimeError:
        logger.info("Scheduler not started (no event loop — expected in non-async contexts)")
