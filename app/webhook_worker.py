"""Webhook delivery worker for alert rules.

Automatically delivers alerts to configured webhooks with retry logic.
"""

import asyncio
import logging
import aiohttp
from typing import List
from app.models import SessionLocal, Alert, AlertRule

logger = logging.getLogger(__name__)

async def _http_post(url: str, payload: dict) -> bool:
    """POST to webhook URL. Returns True on 2xx."""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                return 200 <= response.status < 300
    except Exception as e:
        logger.warning(f"Webhook POST failed for {url}: {e}")
        return False

async def deliver_webhooks_for_alert(alert_id: int):
    """Deliver alert to all configured webhooks for the rule.
    
    Retry logic: 3 attempts with exponential backoff (5s, 15s, 45s).
    """
    db = SessionLocal()
    try:
        alert = db.query(Alert).get(alert_id)
        if not alert or not alert.rule:
            logger.warning(f"Alert {alert_id} not found or has no rule")
            return
        
        rule = alert.rule
        if not rule.webhook_url:
            return
        
        payload = {
            "alert_id": alert.id,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "decision_id": alert.decision_id,
            "decision_title": alert.decision.title if alert.decision else None,
            "category": alert.decision.category if alert.decision else None,
            "timestamp": alert.sent_at.isoformat() if alert.sent_at else None,
        }
        
        max_attempts = 3
        backoff_times = [5, 15, 45]
        
        for attempt in range(max_attempts):
            success = await _http_post(rule.webhook_url, payload)
            if success:
                alert.webhook_delivered = True
                db.commit()
                logger.info(f"Webhook delivered for alert {alert_id} on attempt {attempt + 1}")
                return
            
            if attempt < max_attempts - 1:
                wait_time = backoff_times[attempt]
                logger.warning(f"Webhook attempt {attempt + 1} failed for alert {alert_id}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        logger.error(f"Webhook delivery failed for alert {alert_id} after {max_attempts} attempts")
    finally:
        db.close()

def run_webhook_delivery(limit: int = 50):
    """Find undelivered alerts and send webhooks."""
    db = SessionLocal()
    try:
        undelivered = (
            db.query(Alert)
            .filter(Alert.webhook_delivered == False)
            .limit(limit)
            .all()
        )
        
        if not undelivered:
            return 0
        
        logger.info(f"Delivering webhooks for {len(undelivered)} undelivered alerts")
        
        async def _run_all():
            tasks = [deliver_webhooks_for_alert(a.id) for a in undelivered]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        asyncio.run(_run_all())
        return len(undelivered)
    finally:
        db.close()