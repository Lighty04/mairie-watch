"""Metrics and analytics for MairieWatch."""

from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import SessionLocal, Decision, Alert, AlertRule

def get_coverage_stats() -> dict:
    """Calculate coverage metrics: decisions captured vs expected."""
    db = SessionLocal()
    try:
        # Total decisions in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        total_recent = db.query(Decision).filter(Decision.scraped_at >= thirty_days_ago).count()
        
        # Processed decisions
        processed_recent = (
            db.query(Decision)
            .filter(Decision.scraped_at >= thirty_days_ago)
            .filter(Decision.processed == True)
            .count()
        )
        
        # Categorized decisions
        categorized_recent = (
            db.query(Decision)
            .filter(Decision.scraped_at >= thirty_days_ago)
            .filter(Decision.category != None)
            .count()
        )
        
        # Category breakdown
        cat_breakdown = (
            db.query(Decision.category, func.count(Decision.id))
            .filter(Decision.scraped_at >= thirty_days_ago)
            .group_by(Decision.category)
            .all()
        )
        
        # Time to process (average)
        avg_time = (
            db.query(func.avg(
                func.julianday(Decision.scraped_at) - func.julianday(Decision.published_at)
            ))
            .filter(Decision.scraped_at >= thirty_days_ago)
            .filter(Decision.published_at != None)
            .scalar()
        )
        
        return {
            "period_days": 30,
            "total_captured": total_recent,
            "processed": processed_recent,
            "categorized": categorized_recent,
            "processing_rate": round(processed_recent / total_recent * 100, 1) if total_recent > 0 else 0,
            "categorization_rate": round(categorized_recent / total_recent * 100, 1) if total_recent > 0 else 0,
            "avg_time_to_capture_hours": round(avg_time * 24, 1) if avg_time else None,
            "category_breakdown": {cat: count for cat, count in cat_breakdown if cat},
        }
    finally:
        db.close()

def get_alert_accuracy() -> dict:
    """Calculate alert accuracy metrics."""
    db = SessionLocal()
    try:
        total_alerts = db.query(Alert).count()
        seen_alerts = db.query(Alert).filter(Alert.seen == True).count()
        
        # False positive estimate: alerts where decision text doesn't match rule keywords
        # (simplified: alerts for decisions with no matching keywords)
        from app.alerts import match_decision_to_rules
        
        # Get recent alerts
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_alerts = (
            db.query(Alert)
            .filter(Alert.sent_at >= seven_days_ago)
            .all()
        )
        
        false_positives = 0
        for alert in recent_alerts:
            if alert.decision and alert.rule:
                rule_ids = match_decision_to_rules(alert.decision)
                if alert.rule_id not in rule_ids:
                    false_positives += 1
        
        return {
            "total_alerts": total_alerts,
            "seen_alerts": seen_alerts,
            "engagement_rate": round(seen_alerts / total_alerts * 100, 1) if total_alerts > 0 else 0,
            "recent_alerts": len(recent_alerts),
            "false_positives_estimate": false_positives,
            "false_positive_rate": round(false_positives / len(recent_alerts) * 100, 1) if recent_alerts else 0,
        }
    finally:
        db.close()

def get_all_metrics() -> dict:
    """Get all metrics in one call."""
    return {
        "coverage": get_coverage_stats(),
        "alerts": get_alert_accuracy(),
        "timestamp": datetime.utcnow().isoformat(),
    }
