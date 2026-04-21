from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime

from app.models import Decision, SessionLocal, init_db
from app.scraper import scrape_and_store
from app.extractor import process_pending_decisions
from app.classifier import classify_pending_decisions
from app.alerts import run_alerts_for_new_decisions

logger = logging.getLogger("mairie-watch")

async def run_pipeline(use_llm: bool = False):
    """Run the full pipeline: scrape → extract → classify → alert."""
    init_db()  # Ensure tables exist (safe to call multiple times)
    logger.info("Starting pipeline: scrape")
    scrape_result = await scrape_and_store(query=str(datetime.now().year))
    logger.info(f"Scraped {scrape_result['scraped']} decisions, {scrape_result['new']} new")

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
        "scraped": scrape_result["scraped"],
        "new": scrape_result["new"],
        "extracted": extracted,
        "classified": classified if not use_llm else len(pending),
        "alerted": alerted,
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
