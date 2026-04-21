from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.scraper import scrape_and_store
from app.extractor import process_pending_decisions
from app.classifier import classify_pending_decisions
from app.alerts import run_alerts_for_new_decisions

logger = logging.getLogger("mairie-watch")

async def run_pipeline():
    logger.info("Starting pipeline: scrape")
    scraped = await scrape_and_store()
    logger.info(f"Scraped {scraped} decisions")

    logger.info("Extracting PDFs")
    extracted = process_pending_decisions()
    logger.info(f"Extracted {extracted} PDFs")

    logger.info("Classifying decisions")
    classified = classify_pending_decisions()
    logger.info(f"Classified {classified} decisions")

    logger.info("Running alerts")
    alerted = run_alerts_for_new_decisions()
    logger.info(f"Generated {alerted} alerts")

    return {"scraped": scraped, "extracted": extracted, "classified": classified, "alerted": alerted}

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(run_pipeline, IntervalTrigger(minutes=30), id="pipeline", replace_existing=True)
    scheduler.start()
