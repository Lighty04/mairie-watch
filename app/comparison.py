"""Decision comparison and recurring tracking tools.

- Side-by-side comparison of similar decisions
- Year-over-year trend tracking for same beneficiary
- Anomaly detection: unusual amounts, frequency changes
"""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from app.models import SessionLocal, Decision
from app.summarizer import extract_amount, extract_recipient, generate_summary

@dataclass
class ComparisonResult:
    decision_a_id: int
    decision_b_id: int
    similarity_score: float
    common_fields: Dict[str, any]
    differences: Dict[str, tuple]
    trend: Optional[str] = None  # "increase", "decrease", "stable", "new"

@dataclass
class TrendResult:
    beneficiary: str
    category: str
    decisions: List[Decision]
    total_amount_current_year: float
    total_amount_previous_year: float
    year_over_year_change: Optional[float]  # percentage
    frequency_current: int
    frequency_previous: int
    anomaly: Optional[str] = None

def normalize_beneficiary(name: str) -> str:
    """Normalize beneficiary name for matching."""
    if not name:
        return ""
    # Lowercase, remove common suffixes, strip
    name = name.lower()
    name = re.sub(r'\s+', ' ', name)
    # Remove common French suffixes
    for suffix in [' association', ' sas', ' sarl', ' eurl', ' sa', ' scic']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()

def find_similar_decisions(decision_id: int, limit: int = 10) -> List[ComparisonResult]:
    """Find decisions similar to the given one."""
    db = SessionLocal()
    try:
        target = db.query(Decision).get(decision_id)
        if not target:
            return []
        
        # Get all decisions in same category
        candidates = (
            db.query(Decision)
            .filter(Decision.category == target.category)
            .filter(Decision.id != target.id)
            .filter(Decision.published_at >= datetime.utcnow() - timedelta(days=365))
            .all()
        )
        
        target_summary = generate_summary(target.raw_text or "", target.title)
        results = []
        
        for candidate in candidates:
            cand_summary = generate_summary(candidate.raw_text or "", candidate.title)
            
            # Calculate similarity score (0-1)
            score = 0.0
            common = {}
            diffs = {}
            
            # Same beneficiary?
            if target_summary.recipient and cand_summary.recipient:
                norm_target = normalize_beneficiary(target_summary.recipient)
                norm_cand = normalize_beneficiary(cand_summary.recipient)
                if norm_target == norm_cand or norm_target in norm_cand or norm_cand in norm_target:
                    score += 0.4
                    common['beneficiary'] = target_summary.recipient
                else:
                    diffs['beneficiary'] = (target_summary.recipient, cand_summary.recipient)
            
            # Same arrondissement?
            if target_summary.arrondissement and cand_summary.arrondissement:
                if target_summary.arrondissement == cand_summary.arrondissement:
                    score += 0.2
                    common['arrondissement'] = target_summary.arrondissement
                else:
                    diffs['arrondissement'] = (target_summary.arrondissement, cand_summary.arrondissement)
            
            # Same type?
            if target_summary.decision_type and cand_summary.decision_type:
                if target_summary.decision_type == cand_summary.decision_type:
                    score += 0.2
                    common['type'] = target_summary.decision_type
                else:
                    diffs['type'] = (target_summary.decision_type, cand_summary.decision_type)
            
            # Amount comparison
            if target_summary.amount and cand_summary.amount:
                if target_summary.amount == cand_summary.amount:
                    score += 0.1
                    common['amount'] = target_summary.amount
                else:
                    diffs['amount'] = (target_summary.amount, cand_summary.amount)
                    # Determine trend
                    if cand_summary.amount > target_summary.amount * 1.2:
                        trend = "decrease"  # Candidate is larger (earlier?)
                    elif cand_summary.amount < target_summary.amount * 0.8:
                        trend = "increase"
                    else:
                        trend = "stable"
            else:
                trend = None
            
            # Title similarity
            if target.title and candidate.title:
                target_words = set(target.title.lower().split())
                cand_words = set(candidate.title.lower().split())
                overlap = len(target_words & cand_words)
                union = len(target_words | cand_words)
                if union > 0:
                    jaccard = overlap / union
                    score += jaccard * 0.1
            
            if score >= 0.3:  # Minimum threshold
                results.append(ComparisonResult(
                    decision_a_id=target.id,
                    decision_b_id=candidate.id,
                    similarity_score=round(score, 2),
                    common_fields=common,
                    differences=diffs,
                    trend=trend,
                ))
        
        # Sort by similarity score descending
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:limit]
        
    finally:
        db.close()

def track_beneficiary_trends(beneficiary_name: str, category: str = None, year: int = None) -> TrendResult:
    """Track year-over-year trends for a specific beneficiary."""
    db = SessionLocal()
    try:
        if year is None:
            year = datetime.utcnow().year
        
        # Find all decisions for this beneficiary
        all_decisions = db.query(Decision).filter(
            Decision.category == category if category else True
        ).all()
        
        # Filter by beneficiary name match
        matching = []
        norm_target = normalize_beneficiary(beneficiary_name)
        for d in all_decisions:
            summary = generate_summary(d.raw_text or "", d.title)
            if summary.recipient:
                norm_recipient = normalize_beneficiary(summary.recipient)
                if norm_target == norm_recipient or norm_target in norm_recipient or norm_recipient in norm_target:
                    matching.append(d)
        
        # Split by year
        current_year = [d for d in matching if d.published_at and d.published_at.year == year]
        previous_year = [d for d in matching if d.published_at and d.published_at.year == year - 1]
        
        # Calculate amounts
        current_amounts = []
        for d in current_year:
            summary = generate_summary(d.raw_text or "", d.title)
            if summary.amount:
                current_amounts.append(summary.amount)
        
        previous_amounts = []
        for d in previous_year:
            summary = generate_summary(d.raw_text or "", d.title)
            if summary.amount:
                previous_amounts.append(summary.amount)
        
        total_current = sum(current_amounts)
        total_previous = sum(previous_amounts)
        
        # Calculate YoY change
        yoy_change = None
        if total_previous > 0:
            yoy_change = ((total_current - total_previous) / total_previous) * 100
        
        # Detect anomalies
        anomaly = None
        if len(current_amounts) >= 2:
            avg = sum(current_amounts) / len(current_amounts)
            for amt in current_amounts:
                if amt > avg * 3:
                    anomaly = f"Unusually high amount: €{amt:,.0f} (avg: €{avg:,.0f})"
                    break
        
        if yoy_change is not None and yoy_change > 100:
            anomaly = f"Amount more than doubled (+{yoy_change:.0f}% YoY)"
        elif yoy_change is not None and yoy_change < -50:
            anomaly = f"Amount dropped significantly ({yoy_change:.0f}% YoY)"
        
        return TrendResult(
            beneficiary=beneficiary_name,
            category=category or "all",
            decisions=matching,
            total_amount_current_year=total_current,
            total_amount_previous_year=total_previous,
            year_over_year_change=yoy_change,
            frequency_current=len(current_year),
            frequency_previous=len(previous_year),
            anomaly=anomaly,
        )
        
    finally:
        db.close()

def find_all_recurring_beneficiaries(category: str = None, min_occurrences: int = 2) -> List[Dict]:
    """Find all beneficiaries that appear multiple times."""
    db = SessionLocal()
    try:
        decisions = db.query(Decision).filter(
            Decision.category == category if category else True
        ).all()
        
        # Group by normalized beneficiary
        beneficiary_map = defaultdict(list)
        for d in decisions:
            summary = generate_summary(d.raw_text or "", d.title)
            if summary.recipient:
                norm = normalize_beneficiary(summary.recipient)
                if norm:
                    beneficiary_map[norm].append({
                        'id': d.id,
                        'title': d.title,
                        'published_at': d.published_at.isoformat() if d.published_at else None,
                        'amount': summary.amount,
                        'arrondissement': summary.arrondissement,
                    })
        
        # Filter for recurring
        recurring = []
        for beneficiary, items in beneficiary_map.items():
            if len(items) >= min_occurrences:
                total_amount = sum(i['amount'] or 0 for i in items)
                recurring.append({
                    'beneficiary': beneficiary,
                    'occurrences': len(items),
                    'total_amount': total_amount,
                    'decisions': items,
                })
        
        # Sort by total amount
        recurring.sort(key=lambda x: x['total_amount'], reverse=True)
        return recurring
        
    finally:
        db.close()

def format_comparison(result: ComparisonResult) -> str:
    """Format a comparison result for display."""
    lines = [f"🔍 Similarity: {result.similarity_score:.0%}"]
    
    if result.common_fields:
        lines.append("\n✅ Common:")
        for k, v in result.common_fields.items():
            lines.append(f"  • {k}: {v}")
    
    if result.differences:
        lines.append("\n📊 Differences:")
        for k, (a, b) in result.differences.items():
            lines.append(f"  • {k}: €{a:,.0f} → €{b:,.0f}" if isinstance(a, (int, float)) else f"  • {k}: {a} → {b}")
    
    if result.trend:
        emoji = {"increase": "📈", "decrease": "📉", "stable": "➡️", "new": "🆕"}
        lines.append(f"\n{emoji.get(result.trend, '📊')} Trend: {result.trend}")
    
    return "\n".join(lines)
