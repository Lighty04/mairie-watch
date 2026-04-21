from app.models import AlertRule, Alert, Decision, SessionLocal
from sqlalchemy import func

def match_decision_to_rules(decision: Decision) -> list[int]:
    """Returns list of matching rule IDs for a given decision."""
    if not decision.raw_text:
        return []
    db = SessionLocal()
    try:
        rules = db.query(AlertRule).filter_by(active=True).all()
        matches = []
        text_lower = (decision.raw_text or "").lower()
        title_lower = (decision.title or "").lower()
        for rule in rules:
            matched = False
            # Category match
            if rule.categories and decision.category in rule.categories:
                matched = True
            # Keyword match
            if rule.keywords:
                for kw in rule.keywords:
                    kw_lower = kw.lower()
                    if kw_lower in text_lower or kw_lower in title_lower:
                        matched = True
                        break
            if matched:
                matches.append(rule.id)
        return matches
    finally:
        db.close()

def run_alerts_for_new_decisions():
    db = SessionLocal()
    try:
        # Find decisions that have category set but no alerts yet
        decisions = (
            db.query(Decision)
            .filter(Decision.category != None)
            .filter(~Decision.alerts.any())
            .all()
        )
        count = 0
        for decision in decisions:
            rule_ids = match_decision_to_rules(decision)
            for rid in rule_ids:
                alert = Alert(rule_id=rid, decision_id=decision.id)
                db.add(alert)
                count += 1
        db.commit()
        return count
    finally:
        db.close()
