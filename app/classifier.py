import re
from app.models import Decision, SessionLocal

CATEGORIES = {
    "subventions": [
        "subvention", "aide financière", "attribution d'une subvention",
        "versement d'une subvention", "allocation", "dotation", "fonds", "budget participatif"
    ],
    "appointments": [
        "nomination", "désignation", "mandat", "élu", "conseiller",
        "membre de droit", "représentant", "délégué", "titulaire", "suppléant"
    ],
    "contracts": [
        "marché public", "contrat", "procédure adaptée", "appel d'offres",
        "consultation", "affermissement", "convention", "bail emphytéotique", "délégation de service public"
    ],
    "urbanism": [
        "urbanisme", "permis de construire", "PLU", "plan local d'urbanisme",
        "déclaration préalable", "travaux", "aménagement", "rénovation", "construction"
    ],
    "environment": [
        "environnement", "déchets", "propreté", "vert", "végétalisation",
        "climat", "biodiversité", "énergie", "pollution", "dépollution", "recyclage"
    ],
    "budget": [
        "budget", "décision modificative", "compte administratif",
        "exécution du budget", "autorisation de programme", "crédit", "dépense", "recette"
    ],
    "real_estate": [
        "domaine", "cession", "acquisition", "immobilier", "bail", "location",
        "propriété", "immeuble", "terrain", "surplus", "servitude"
    ],
    "social": [
        "social", "aide alimentaire", "logement", "sans-abri", "solidarité",
        "insertion", "handicap", "personne âgée", "famille", "jeunesse", "petite enfance"
    ],
    "education": [
        "école", "crèche", "enseignement", "périscolaire", "université",
        "étudiant", "scolaire", "pédagogie", "professeur", "maître", "CDEN"
    ],
    "culture": [
        "culture", "bibliothèque", "musée", "spectacle", "festival",
        "patrimoine", "conservatoire", "théâtre", "cinéma", "art"
    ],
    "sports": [
        "sport", "stade", "gymnase", "piscine", "équipement sportif",
        "club", "tournoi", "compétition", "jogging", "fitness"
    ],
    "health": [
        "santé", "hôpital", "médical", "soin", "prévention", "hygiène",
        "désinfection", "covid", "vaccin", "épisode de pollution"
    ],
    "transport": [
        "transport", "circulation", "stationnement", "vélo", "bus",
        "métro", "tramway", "voie", "route", "trottoir", "piste cyclable"
    ],
    "safety": [
        "sécurité", "police", "préfecture de police", "vidéoprotection",
        "surveillance", "ordre public", "manifestation", "règlement de police"
    ],
    "governance": [
        "indemnité", "rémunération", "frais de représentation", "moyens des groupes",
        "droit de garde", "règlement intérieur", "charte", "éthique"
    ],
}

def classify_text(text: str) -> tuple[str, list[str]]:
    """Classify text into primary category and subcategories."""
    if not text or len(text.strip()) < 20:
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
    max_score = scores[primary]

    # Subcategories = all categories with score >= 40% of max and different from primary
    threshold = max_score * 0.4
    subs = [cat for cat, score in scores.items() if score >= threshold and cat != primary]

    return primary, subs

def classify_pending_decisions(limit: int = 50, use_llm: bool = False):
    """Classify all extracted but unclassified decisions."""
    db = SessionLocal()
    try:
        pending = (
            db.query(Decision)
            .filter(Decision.processed == True)
            .filter(Decision.category == None)
            .limit(limit)
            .all()
        )
        for decision in pending:
            cat, subs = classify_text(decision.raw_text or "")
            decision.category = cat
            decision.subcategories = subs
            db.add(decision)
        db.commit()
        return len(pending)
    finally:
        db.close()
