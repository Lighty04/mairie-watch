"""Smart summary extraction from municipal decision text.

Extracts structured data: amounts, recipients, dates, approval status, etc.
"""

import re
from typing import Optional
from dataclasses import dataclass

@dataclass
class DecisionSummary:
    decision_type: Optional[str] = None
    recipient: Optional[str] = None
    amount: Optional[float] = None
    amount_str: Optional[str] = None
    approved_by: Optional[str] = None
    approval_status: Optional[str] = None
    date: Optional[str] = None
    arrondissement: Optional[str] = None
    context: Optional[str] = None
    full_text: Optional[str] = None

def extract_amount(text: str) -> tuple[Optional[float], Optional[str]]:
    """Extract monetary amount from text. Returns (amount_float, original_string)."""
    # Match patterns like: 25 000 euros, 25000€, 1.5 million d'euros, etc.
    patterns = [
        # "25 000 euros" or "25 000,50 euros" (with thousands separator - check FIRST)
        r'(\d{1,3}(?:\s+\d{3})+(?:,\d{2})?)\s*(?:euros?|€)',
        # "25000 euros" or "25000€" (no thousands separator)
        r'(\d{1,6}(?:,\d{2})?)\s*(?:euros?|€)',
        # "1,5 million d'euros"
        r'(\d{1,3}(?:,\d{1,2})?)\s*(?:million|milliard)s?\s*d\s*[\'\']?\s*euros?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            amount_str = match.group(1)
            # Remove spaces
            clean = amount_str.replace(' ', '').replace(',', '.')
            try:
                amount = float(clean)
                # Handle millions
                if 'million' in text.lower()[match.start():match.end()+20]:
                    amount *= 1_000_000
                elif 'milliard' in text.lower()[match.start():match.end()+20]:
                    amount *= 1_000_000_000
                return amount, match.group(0)
            except ValueError:
                continue
    return None, None

def extract_recipient(text: str) -> Optional[str]:
    """Extract the recipient/beneficiary of a decision."""
    patterns = [
        # "à l'association ABC" or "à la société XYZ"
        r"(?:à|au|aux)\s+(?:l['\s])?(?:association|société|entreprise|collectivité|établissement)\s*([A-Z][^\.,\n]{3,80})",
        # "attribution d'une subvention à ABC"
        r"(?:attribution|versement|allocation)\s+(?:d['\s])?une?\s+\w+\s+à\s*([A-Z][^\.,\n]{3,80})",
        # "entre la Ville de Paris et l'Association Sportive"
        r"(?:entre|et)\s+(?:l['\s])?(?:association|société|entreprise|collectivité|établissement)\s*([A-Z][^\.,\n]{3,80})",
        # "en faveur de l'association ABC"
        r"en faveur de\s+(?:l['\s])?(?:association|la|le)?\s*([A-Z][^\.,\n]{3,80})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            recipient = match.group(1).strip()
            # Clean up
            recipient = re.sub(r'\s+', ' ', recipient)
            if len(recipient) > 3:
                return recipient
    return None

def extract_arrondissement(text: str) -> Optional[str]:
    """Extract Paris arrondissement reference."""
    patterns = [
        r'(\d{1,2})\s*(?:er|e|ème|eme)?\s*arrondissement',
        r'arrondissement\s*(?:du\s*)?(\d{1,2})',
        r'\b(\d{1,2})(?:er|e|ème|eme)?\s*arrondissement\b',
        r'\barrondissement\s*(?:du\s*)?(\d{1,2})\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 20:
                return f"{num}e"
    return None

def extract_approval(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract approval body and status. Returns (body, status)."""
    # Approval body
    bodies = [
        r'Conseil de Paris',
        r'Conseil municipal',
        r'Conseil d\'arrondissement',
        r'Maire de Paris',
        r'Préfet de police',
    ]
    
    body = None
    for pattern in bodies:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            body = match.group(0)
            break
    
    # Approval status
    status = None
    if re.search(r'à\s+l\s*\'\s*unanimité', text, re.IGNORECASE):
        status = "unanimous"
    elif re.search(r'vote\s*:\s*(\d+)\s*pour\s*(?:et\s*)?(\d+)\s*contre', text, re.IGNORECASE):
        match = re.search(r'vote\s*:\s*(\d+)\s*pour\s*(?:et\s*)?(\d+)\s*contre', text, re.IGNORECASE)
        status = f"{match.group(1)}-{match.group(2)}"
    elif re.search(r'adopt[ée]', text, re.IGNORECASE):
        status = "adopted"
    
    return body, status

def extract_date(text: str) -> Optional[str]:
    """Extract decision date."""
    # Match French date formats
    patterns = [
        r'(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
        r'(\d{1,2})-(\d{1,2})-(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 3 and match.group(2).isdigit():
                # DD/MM/YYYY format
                return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
            else:
                # French text date
                return f"{match.group(1)} {match.group(2).lower()} {match.group(3)}"
    return None

def generate_summary(text: str, title: str = None) -> DecisionSummary:
    """Generate a smart summary from decision text."""
    amount, amount_str = extract_amount(text)
    recipient = extract_recipient(text)
    arrondissement = extract_arrondissement(text)
    approved_by, approval_status = extract_approval(text)
    date = extract_date(text)
    
    # Determine type from title or text
    decision_type = None
    if title:
        type_keywords = {
            'subvention': 'subvention',
            'décision modificative': 'budget',
            'nomination': 'appointment',
            'marché public': 'contract',
            'contrat': 'contract',
            'urbanisme': 'urbanism',
        }
        for keyword, dtype in type_keywords.items():
            if keyword.lower() in title.lower():
                decision_type = dtype
                break
    
    # Build context
    context_parts = []
    if arrondissement:
        context_parts.append(f"{arrondissement} arrondissement")
    if decision_type:
        context_parts.append(decision_type)
    
    return DecisionSummary(
        decision_type=decision_type,
        recipient=recipient,
        amount=amount,
        amount_str=amount_str,
        approved_by=approved_by,
        approval_status=approval_status,
        date=date,
        arrondissement=arrondissement,
        context=', '.join(context_parts) if context_parts else None,
        full_text=text,
    )

def format_summary_for_display(summary: DecisionSummary) -> str:
    """Format a DecisionSummary into human-readable text."""
    lines = []
    
    if summary.decision_type:
        lines.append(f"• Type: {summary.decision_type}")
    if summary.recipient:
        lines.append(f"• Bénéficiaire: {summary.recipient}")
    if summary.amount:
        lines.append(f"• Montant: €{summary.amount:,.0f}")
    if summary.approved_by:
        status = f" ({summary.approval_status})" if summary.approval_status else ""
        lines.append(f"• Approuvé par: {summary.approved_by}{status}")
    if summary.arrondissement:
        lines.append(f"• Arrondissement: {summary.arrondissement}")
    if summary.date:
        lines.append(f"• Date: {summary.date}")
    
    return "\n".join(lines)
