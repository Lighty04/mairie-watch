import re
from app.models import Decision, SessionLocal

CATEGORIES = {
    "subventions": ["subvention", "aide financière", "attribution d'une subvention", "versement d'une subvention"],
    "appointments": ["nomination", "désignation", "mandat", "élu", "conseiller", "membre de droit"],
    "contracts": ["marché public", "contrat", "procédure adaptée", "appel d'offres", "consultation"],
    "urbanism": ["urbanisme", "permis de construire", "PLU", "déclaration préalable", "travaux"],
    "environment": ["environnement", "déchets", "propreté", "vert", "végétalisation", "climat"],
    "budget": ["budget", "décision modificative", "compte administratif", "exécution du budget"],
    "real_estate": ["domaine", "cession", "acquisition", "immobilier", "bail", "location"],
    "social": ["social", "aide alimentaire", "logement", "sans-abri", "solidarité", "insertion"],
    "education": ["école", "crèche", "enseignement", "périscolaire", "université", "étudiant"],
    "culture": ["culture", "bibliothèque", "musée", "spectacle", "festival", "patrimoine"],
}

def classify_text(text: str) -> tuple[str, list[str]]:
    if not text:
        return "uncategorized", []
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[category] = score
    if not scores:
        return "uncategorized", []
    # Primary category = highest score
    primary = max(scores, key=scores.get)
    # Subcategories = all categories with score >= 50% of max
    max_score = scores[primary]
    subs = [cat for cat, score in scores.items() if score >= max_score * 0.5 and cat != primary]
    return primary, subs

def classify_pending_decisions():
    db = SessionLocal()
    try:
        pending = db.query(Decision).filter(Decision.processed == True, Decision.category == None).all()
        for decision in pending:
            cat, subs = classify_text(decision.raw_text or "")
            decision.category = cat
            decision.subcategories = subs
            db.add(decision)
        db.commit()
        return len(pending)
    finally:
        db.close()
