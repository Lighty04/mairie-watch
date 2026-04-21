"""Advanced alert matching with boolean logic, amount thresholds, and exclusions."""

import re
from typing import Optional, List, Dict
from app.models import Decision, AlertRule, SessionLocal
from app.summarizer import generate_summary

def _split_sentences(text: str) -> List[str]:
    """Split text into sentences, handling French punctuation."""
    # Match sentence-ending punctuation followed by space or end
    pattern = r'(?<=[.!?])\s+(?=[A-ZÀ-ÿ])|(?<=[.!?])$'
    return [s.strip() for s in re.split(pattern, text) if s.strip()]

def extract_keyword_context(text: str, keyword: str, max_occurrences: int = 3) -> List[Dict]:
    """Extract 2 sentences before and after each keyword match.
    
    Returns list of dicts: {keyword, before, match, after, position}
    """
    text_lower = text.lower()
    kw_lower = keyword.lower()
    sentences = _split_sentences(text)
    results = []
    
    # Build a sentence index map for quick lookup
    sentence_ranges = []
    pos = 0
    for sent in sentences:
        start = text_lower.find(sent.lower(), pos)
        if start == -1:
            start = pos
        end = start + len(sent)
        sentence_ranges.append((start, end, sent))
        pos = end
    
    # Find all keyword occurrences
    idx = 0
    for _ in range(max_occurrences):
        idx = text_lower.find(kw_lower, idx)
        if idx == -1:
            break
        
        # Find which sentence contains the keyword
        sent_idx = None
        for i, (start, end, sent) in enumerate(sentence_ranges):
            if start <= idx < end:
                sent_idx = i
                break
        
        if sent_idx is None:
            idx += len(kw_lower)
            continue
        
        # Get 2 sentences before and after
        before_start = max(0, sent_idx - 2)
        after_end = min(len(sentences), sent_idx + 3)
        
        before_sents = sentences[before_start:sent_idx]
        after_sents = sentences[sent_idx + 1:after_end]
        match_sent = sentences[sent_idx]
        
        # Highlight keyword in the match sentence
        # Find keyword position in original case sentence
        ms_lower = match_sent.lower()
        kw_pos = ms_lower.find(kw_lower)
        if kw_pos >= 0:
            highlighted = (
                match_sent[:kw_pos] +
                f"<mark>{match_sent[kw_pos:kw_pos + len(keyword)]}</mark>" +
                match_sent[kw_pos + len(keyword):]
            )
        else:
            highlighted = match_sent
        
        results.append({
            "keyword": keyword,
            "before": " ".join(before_sents),
            "match": highlighted,
            "after": " ".join(after_sents),
            "position": idx,
        })
        
        idx += len(kw_lower)
    
    return results

def match_amount_threshold(text: str, threshold: float, operator: str = "gt") -> bool:
    """Check if a decision contains an amount matching the threshold.
    
    operator: gt, lt, gte, lte, eq
    """
    from app.summarizer import extract_amount
    amount, _ = extract_amount(text)
    if amount is None:
        return False
    
    ops = {
        "gt": amount > threshold,
        "lt": amount < threshold,
        "gte": amount >= threshold,
        "lte": amount <= threshold,
        "eq": amount == threshold,
    }
    return ops.get(operator, False)

def match_boolean_query(text: str, query: str) -> bool:
    """Match a boolean query like 'subvention AND (sport OR culture) NOT religion'.
    
    Supports: AND, OR, NOT, parentheses
    """
    text_lower = text.lower()
    
    # Tokenize
    tokens = []
    current = ""
    i = 0
    while i < len(query):
        if query[i] == '(':
            if current.strip():
                tokens.append(current.strip().lower())
                current = ""
            tokens.append('(')
            i += 1
        elif query[i] == ')':
            if current.strip():
                tokens.append(current.strip().lower())
                current = ""
            tokens.append(')')
            i += 1
        elif query[i].isspace():
            if current.strip():
                tokens.append(current.strip().lower())
                current = ""
            i += 1
        else:
            current += query[i]
            i += 1
    
    if current.strip():
        tokens.append(current.strip().lower())
    
    # Evaluate
    def eval_tokens(tokens, idx):
        """Evaluate tokens starting at idx. Returns (result, next_idx)."""
        result = None
        op = "AND"
        i = idx
        
        while i < len(tokens):
            token = tokens[i]
            
            if token == '(':
                sub_result, i = eval_tokens(tokens, i + 1)
                if result is None:
                    result = sub_result
                elif op == "AND":
                    result = result and sub_result
                elif op == "OR":
                    result = result or sub_result
            elif token == ')':
                return result, i + 1
            elif token == "and":
                op = "AND"
                i += 1
            elif token == "or":
                op = "OR"
                i += 1
            elif token == "not":
                # Next token should be negated
                i += 1
                if i < len(tokens):
                    if tokens[i] == '(':
                        sub_result, i = eval_tokens(tokens, i + 1)
                        sub_result = not sub_result
                    else:
                        sub_result = tokens[i] in text_lower
                        sub_result = not sub_result
                        i += 1
                    
                    if result is None:
                        result = sub_result
                    elif op == "AND":
                        result = result and sub_result
                    elif op == "OR":
                        result = result or sub_result
            else:
                # Keyword
                match = token in text_lower
                if result is None:
                    result = match
                elif op == "AND":
                    result = result and match
                elif op == "OR":
                    result = result or match
                i += 1
        
        return result if result is not None else False, i
    
    result, _ = eval_tokens(tokens, 0)
    return result

def match_advanced_rule(decision: Decision, rule: AlertRule) -> bool:
    """Match a decision against an advanced alert rule.
    
    Supports:
    - Boolean queries in keywords (AND, OR, NOT, parentheses)
    - Amount thresholds (amount_threshold, amount_operator)
    - Category matching
    - Arrondissement matching
    """
    text = (decision.raw_text or "").lower()
    title = (decision.title or "").lower()
    combined = f"{title} {text}"
    
    # Category match
    if rule.categories:
        cat_match = decision.category in rule.categories
        if not cat_match and decision.subcategories:
            cat_match = any(sub in rule.categories for sub in (decision.subcategories or []))
        if not cat_match:
            return False
    
    # Arrondissement match
    if rule.arrondissements:
        arr_match = False
        for arr in rule.arrondissements:
            arr_str = str(arr).lower()
            if arr_str in combined or f"{arr}e" in combined or f"{arr}ème" in combined:
                arr_match = True
                break
        if not arr_match:
            return False
    
    # Keyword match (supports boolean)
    if rule.keywords:
        # Check if any keyword looks like a boolean query
        for kw in rule.keywords:
            if any(op in kw.lower() for op in [' and ', ' or ', 'not ', '(']):
                if not match_boolean_query(combined, kw):
                    return False
            else:
                # Simple keyword match
                kw_lower = kw.lower()
                if kw_lower not in combined:
                    return False
    
    # Amount threshold (stored in metadata_json)
    if rule.metadata_json:
        threshold = rule.metadata_json.get('amount_threshold')
        operator = rule.metadata_json.get('amount_operator', 'gt')
        if threshold is not None:
            if not match_amount_threshold(text, threshold, operator):
                return False
    
    return True

def run_advanced_alerts(limit: int = 50):
    """Run advanced alert matching for all unalerted decisions."""
    db = SessionLocal()
    try:
        from app.alerts import Alert
        from sqlalchemy import exists
        
        # Find decisions with no alerts
        decisions = (
            db.query(Decision)
            .filter(Decision.category != None)
            .filter(~exists().where(Alert.decision_id == Decision.id))
            .limit(limit)
            .all()
        )
        
        rules = db.query(AlertRule).filter_by(active=True).all()
        count = 0
        
        for decision in decisions:
            for rule in rules:
                if match_advanced_rule(decision, rule):
                    alert = Alert(rule_id=rule.id, decision_id=decision.id)
                    db.add(alert)
                    count += 1
        
        db.commit()
        return count
    finally:
        db.close()

def generate_alert_email(alert_id: int) -> dict:
    """Generate email content for an alert."""
    db = SessionLocal()
    try:
        alert = db.query(Alert).get(alert_id)
        if not alert or not alert.decision:
            return None
        
        decision = alert.decision
        rule = alert.rule
        summary = generate_summary(decision.raw_text or "", decision.title)
        
        # Find matching keywords with context
        highlights = []
        if rule.keywords:
            text = decision.raw_text or ""
            for kw in rule.keywords:
                # Find keyword in text
                kw_lower = kw.lower()
                idx = text.lower().find(kw_lower)
                if idx >= 0:
                    start = max(0, idx - 100)
                    end = min(len(text), idx + len(kw) + 100)
                    context = text[start:end]
                    # Highlight keyword
                    highlighted = context.replace(
                        text[idx:idx+len(kw)],
                        f"**{text[idx:idx+len(kw)]}**"
                    )
                    highlights.append(highlighted)
        
        return {
            "subject": f"🔔 {rule.name}: {decision.title[:60]}",
            "summary": summary,
            "highlights": highlights[:3],  # Top 3 highlights
            "decision_url": f"/decision/{decision.id}",
            "pdf_url": decision.pdf_url,
            "category": decision.category,
            "sent_at": alert.sent_at.isoformat() if alert.sent_at else None,
        }
    finally:
        db.close()
