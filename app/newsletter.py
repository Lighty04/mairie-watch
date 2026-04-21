"""Weekly "Decision of the Week" newsletter system.

Generates curated newsletter highlighting significant decisions.
"""

import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter

from app.models import SessionLocal, Decision
from app.summarizer import generate_summary
from app.comparison import find_similar_decisions, normalize_beneficiary

def get_significant_decisions(days: int = 7, limit: int = 5) -> List[Dict]:
    """Find the most significant decisions from the last N days.
    
    Significance scoring:
    - Large amounts (+)
    - Unanimous approval vs contested (+)
    - First-time beneficiary (+)
    - No-bid contract (+)
    - Affects multiple arrondissements (+)
    """
    db = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        decisions = (
            db.query(Decision)
            .filter(Decision.published_at >= since)
            .filter(Decision.category != None)
            .all()
        )
        
        scored = []
        for d in decisions:
            summary = generate_summary(d.raw_text or "", d.title)
            score = 0.0
            reasons = []
            
            # Large amount = significant
            if summary.amount:
                if summary.amount >= 500_000:
                    score += 5
                    reasons.append(f"€{summary.amount:,.0f} — very large amount")
                elif summary.amount >= 100_000:
                    score += 3
                    reasons.append(f"€{summary.amount:,.0f} — large amount")
                elif summary.amount >= 10_000:
                    score += 1
            
            # Unanimous vs contested
            if summary.approval_status == "unanimous":
                score += 0.5
            elif summary.approval_status and summary.approval_status != "unanimous":
                score += 1.5  # Controversial = more interesting
                reasons.append("Contested vote")
            
            # No-bid contract detection
            text_lower = (d.raw_text or "").lower()
            if any(kw in text_lower for kw in ["procédure adaptée", "gré à gré", "négocié", "sans publicité", "sans mise en concurrence"]):
                score += 3
                reasons.append("No competitive bidding")
            
            # First-time beneficiary
            if summary.recipient:
                # Check if this beneficiary appeared before
                all_decisions = db.query(Decision).filter(
                    Decision.id != d.id,
                    Decision.published_at < d.published_at,
                ).all()
                
                found_before = False
                norm_new = normalize_beneficiary(summary.recipient)
                for old in all_decisions:
                    old_summary = generate_summary(old.raw_text or "", old.title)
                    if old_summary.recipient:
                        norm_old = normalize_beneficiary(old_summary.recipient)
                        if norm_new == norm_old or norm_new in norm_old or norm_old in norm_new:
                            found_before = True
                            break
                
                if not found_before:
                    score += 1
                    reasons.append("First-time beneficiary")
            
            # Affects multiple arrondissements
            if summary.arrondissement:
                arr_text = re.findall(r'(\d{1,2})e?\s*arrondissement', text_lower)
                if len(set(arr_text)) > 1:
                    score += 1
                    reasons.append(f"Affects {len(set(arr_text))} arrondissements")
            
            scored.append({
                'decision': d,
                'summary': summary,
                'score': score,
                'reasons': reasons,
            })
        
        # Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:limit]
        
    finally:
        db.close()

def generate_newsletter(days: int = 7) -> Dict:
    """Generate the weekly newsletter content."""
    significant = get_significant_decisions(days=days, limit=5)
    
    # Get category breakdown for the week
    db = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        all_recent = (
            db.query(Decision)
            .filter(Decision.published_at >= since)
            .filter(Decision.category != None)
            .all()
        )
        
        categories = Counter(d.category for d in all_recent if d.category)
        total_amount = sum(
            (generate_summary(d.raw_text or "", d.title).amount or 0)
            for d in all_recent
        )
        
    finally:
        db.close()
    
    # Build newsletter
    newsletter = {
        'subject': f"📰 MairieWatch Weekly — {len(significant)} décisions marquantes",
        'period': f"{since.strftime('%d/%m')} — {datetime.utcnow().strftime('%d/%m/%Y')}",
        'stats': {
            'total_decisions': len(all_recent),
            'total_amount': total_amount,
            'top_category': categories.most_common(1)[0] if categories else None,
            'category_breakdown': dict(categories.most_common()),
        },
        'featured_decision': significant[0] if significant else None,
        'other_decisions': significant[1:] if len(significant) > 1 else [],
        'generated_at': datetime.utcnow().isoformat(),
    }
    
    return newsletter

def format_newsletter_html(newsletter: Dict) -> str:
    """Format newsletter as HTML email."""
    lines = [
        "<!DOCTYPE html>",
        "<html><body style='font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1a1a2e;'>",
        f"  <h1 style='color: #1a1a2e;'>📰 MairieWatch Weekly</h1>",
        f"  <p style='color: #5a6a7f;'>{newsletter['period']}</p>",
        "  <hr>",
        "  <h2>📊 Cette semaine en chiffres</h2>",
        f"  <p><strong>{newsletter['stats']['total_decisions']}</strong> décisions analysées</p>",
    ]
    
    if newsletter['stats']['total_amount'] > 0:
        lines.append(f"  <p>Montant total: <strong>€{newsletter['stats']['total_amount']:,.0f}</strong></p>")
    
    if newsletter['stats']['top_category']:
        cat, count = newsletter['stats']['top_category']
        lines.append(f"  <p>Catégorie principale: <strong>{cat}</strong> ({count} décisions)</p>")
    
    # Featured decision
    if newsletter['featured_decision']:
        fd = newsletter['featured_decision']
        d = fd['decision']
        s = fd['summary']
        
        lines.extend([
            "  <hr>",
            "  <h2>🎯 Décision de la semaine</h2>",
            f"  <h3>{d.title or 'Sans titre'}</h3>",
        ])
        
        if s.amount:
            lines.append(f"  <p>💰 <strong>Montant: €{s.amount:,.0f}</strong></p>")
        if s.recipient:
            lines.append(f"  <p>👤 <strong>Bénéficiaire: {s.recipient}</strong></p>")
        if s.approved_by:
            status = f" ({s.approval_status})" if s.approval_status else ""
            lines.append(f"  <p>✅ <strong>Approuvé par: {s.approved_by}{status}</strong></p>")
        
        if fd['reasons']:
            lines.append("  <p>📝 Pourquoi c'est important:</p>")
            lines.append("  <ul>")
            for reason in fd['reasons']:
                lines.append(f"    <li>{reason}</li>")
            lines.append("  </ul>")
        
        lines.append(f"  <p><a href='http://192.168.0.16:8083/decision/{d.id}' style='color: #4f46e5;'>📄 Voir la décision complète →</a></p>")
    
    # Other significant decisions
    if newsletter['other_decisions']:
        lines.extend([
            "  <hr>",
            "  <h2>📋 Autres décisions marquantes</h2>",
        ])
        
        for item in newsletter['other_decisions']:
            d = item['decision']
            s = item['summary']
            
            lines.append(f"  <h4>{d.title or 'Sans titre'}</h4>")
            
            details = []
            if s.amount:
                details.append(f"€{s.amount:,.0f}")
            if s.category:
                details.append(s.category)
            if s.arrondissement:
                details.append(f"{s.arrondissement} arrondissement")
            
            if details:
                lines.append(f"  <p>{', '.join(details)}</p>")
            
            if item['reasons']:
                lines.append(f"  <p><em>{item['reasons'][0]}</em></p>")
            
            lines.append(f"  <p><a href='http://192.168.0.16:8083/decision/{d.id}' style='color: #4f46e5;'>Voir →</a></p>")
    
    lines.extend([
        "  <hr>",
        "  <p style='color: #5a6a7f; font-size: 0.9em;'>",
        "    MairieWatch — Surveillance des décisions municipales <br>",
        "    <a href='http://192.168.0.16:8083/pricing' style='color: #4f46e5;'>Passer à Pro pour des alertes en temps réel →</a>",
        "  </p>",
        "</body></html>",
    ])
    
    return "\n".join(lines)

def format_newsletter_text(newsletter: Dict) -> str:
    """Format newsletter as plain text."""
    lines = [
        "📰 MAIRIEWATCH WEEKLY",
        f"{newsletter['period']}",
        "",
        f"📊 Cette semaine: {newsletter['stats']['total_decisions']} décisions analysées",
    ]
    
    if newsletter['stats']['total_amount'] > 0:
        lines.append(f"Montant total: €{newsletter['stats']['total_amount']:,.0f}")
    
    # Featured decision
    if newsletter['featured_decision']:
        fd = newsletter['featured_decision']
        d = fd['decision']
        s = fd['summary']
        
        lines.extend([
            "",
            "═══════════════════════════════════════",
            "🎯 DÉCISION DE LA SEMAINE",
            "═══════════════════════════════════════",
            "",
            d.title or "Sans titre",
            "",
        ])
        
        if s.amount:
            lines.append(f"💰 Montant: €{s.amount:,.0f}")
        if s.recipient:
            lines.append(f"👤 Bénéficiaire: {s.recipient}")
        if s.approved_by:
            status = f" ({s.approval_status})" if s.approval_status else ""
            lines.append(f"✅ Approuvé par: {s.approved_by}{status}")
        
        if fd['reasons']:
            lines.append("")
            lines.append("📝 Pourquoi c'est important:")
            for reason in fd['reasons']:
                lines.append(f"  • {reason}")
        
        lines.append("")
        lines.append(f"📄 Voir la décision: http://192.168.0.16:8083/decision/{d.id}")
    
    # Other decisions
    if newsletter['other_decisions']:
        lines.extend([
            "",
            "═══════════════════════════════════════",
            "📋 AUTRES DÉCISIONS MARQUANTES",
            "═══════════════════════════════════════",
        ])
        
        for item in newsletter['other_decisions']:
            d = item['decision']
            s = item['summary']
            
            lines.extend([
                "",
                d.title or "Sans titre",
            ])
            
            details = []
            if s.amount:
                details.append(f"€{s.amount:,.0f}")
            if s.category:
                details.append(s.category)
            if details:
                lines.append(", ".join(details))
            
            if item['reasons']:
                lines.append(f"→ {item['reasons'][0]}")
            
            lines.append(f"Voir: http://192.168.0.16:8083/decision/{d.id}")
    
    lines.extend([
        "",
        "═══════════════════════════════════════",
        "MairieWatch — http://192.168.0.16:8083",
        "Passez à Pro pour des alertes en temps réel",
        "═══════════════════════════════════════",
    ])
    
    return "\n".join(lines)
