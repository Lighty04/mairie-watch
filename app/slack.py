"""Slack integration for team alerts."""

import httpx
import json
import logging
from typing import Optional

from app.models import SessionLocal, Alert, AlertRule
from app.summarizer import generate_summary

logger = logging.getLogger("mairie-watch")

async def send_slack_alert(webhook_url: str, alert_id: int) -> bool:
    """Send a formatted alert to a Slack webhook."""
    db = SessionLocal()
    try:
        alert = db.query(Alert).get(alert_id)
        if not alert or not alert.decision:
            return False
        
        decision = alert.decision
        rule = alert.rule
        summary = generate_summary(decision.raw_text or "", decision.title)
        
        # Build Slack message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {rule.name}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{decision.category or 'Non catégorisé'}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Date:*\n{decision.published_at.strftime('%d/%m/%Y') if decision.published_at else 'N/A'}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Décision:*\n{decision.title or 'Sans titre'}"
                }
            }
        ]
        
        # Add amount if found
        if summary.amount:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Montant:*\n€{summary.amount:,.0f}"
                    }
                ]
            })
        
        # Add recipient if found
        if summary.recipient:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Bénéficiaire:*\n{summary.recipient}"
                }
            })
        
        # Add action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📄 Voir le PDF"
                    },
                    "url": decision.pdf_url,
                    "action_id": "view_pdf"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 Voir sur MairieWatch"
                    },
                    "url": f"http://192.168.0.16:8083/decision/{decision.id}",
                    "action_id": "view_dashboard"
                }
            ]
        })
        
        payload = {
            "text": f"Nouvelle alerte: {rule.name}",
            "blocks": blocks
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            resp.raise_for_status()
            return True
            
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")
        return False
    finally:
        db.close()

def generate_webhook_payload(alert_id: int) -> Optional[dict]:
    """Generate JSON payload for webhook."""
    db = SessionLocal()
    try:
        alert = db.query(Alert).get(alert_id)
        if not alert or not alert.decision:
            return None
        
        decision = alert.decision
        rule = alert.rule
        summary = generate_summary(decision.raw_text or "", decision.title)
        
        return {
            "event": "decision_alert",
            "timestamp": alert.sent_at.isoformat() if alert.sent_at else None,
            "rule": {
                "id": rule.id,
                "name": rule.name,
                "keywords": rule.keywords,
                "categories": rule.categories,
            },
            "decision": {
                "id": decision.id,
                "title": decision.title,
                "category": decision.category,
                "subcategories": decision.subcategories,
                "published_at": decision.published_at.isoformat() if decision.published_at else None,
                "pdf_url": decision.pdf_url,
                "dashboard_url": f"http://192.168.0.16:8083/decision/{decision.id}",
            },
            "summary": {
                "type": summary.decision_type,
                "recipient": summary.recipient,
                "amount": summary.amount,
                "amount_str": summary.amount_str,
                "arrondissement": summary.arrondissement,
                "approved_by": summary.approved_by,
                "approval_status": summary.approval_status,
            }
        }
    finally:
        db.close()

async def send_webhook(webhook_url: str, alert_id: int) -> bool:
    """Send alert to a generic webhook URL."""
    payload = generate_webhook_payload(alert_id)
    if not payload:
        return False
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Failed to send webhook: {e}")
        return False
