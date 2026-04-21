"""LLM-based classifier for municipal decisions.

Falls back to keyword classification if LLM is unavailable.
Uses local Ollama by default, configurable via LLM_ENDPOINT env var.
"""

import os
import re
import httpx
import logging
from typing import Optional

from app.classifier import classify_text as keyword_classify

logger = logging.getLogger("mairie-watch")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.0.2:11434")
MODEL = os.getenv("OLLAMA_MODEL", "claw-worker:latest")

CATEGORY_PROMPT = """Tu es un expert en analyse de documents municipaux français. Classe chaque décision dans une catégorie.

Catégories possibles: subventions, appointments, contracts, urbanism, environment, budget, real_estate, social, education, culture, sports, health, transport, safety, governance, uncategorized

Exemples:
- "Subvention de 50000€ à l'association ABC" → subventions
- "Désignation de M. Dupont comme représentant" → appointments
- "Marché public pour la rénovation des écoles" → contracts
- "Modification du PLU du 12e arrondissement" → urbanism
- "Plan de gestion des déchets" → environment
- "Décision modificative du budget" → budget
- "Cession d'immeuble municipal" → real_estate
- "Aide au logement pour personnes sans-abri" → social
- "Création d'une nouvelle classe dans l'école" → education
- "Subvention pour le festival de musique" → culture
- "Rénovation du stade municipal" → sports
- "Campagne de vaccination" → health
- "Création d'une piste cyclable" → transport
- "Installation de caméras de vidéosurveillance" → safety
- "Indemnités de fonction des élus" → governance

Texte:
{}

Catégorie (UN SEUL MOT):"""

async def classify_with_llm(text: str) -> Optional[str]:
    """Classify text using local LLM with few-shot prompting."""
    if not text or len(text.strip()) < 50:
        return None

    # Truncate to avoid context overflow
    truncated = text[:3000]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": CATEGORY_PROMPT.format(truncated),
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 30},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "").strip().lower()

            if not response_text:
                return None

            # Remove punctuation, keep letters and underscores
            response_text = re.sub(r'[^a-z_\s]', '', response_text).strip()

            valid_categories = [
                "subventions", "appointments", "contracts", "urbanism",
                "environment", "budget", "real_estate", "social",
                "education", "culture", "sports", "health",
                "transport", "safety", "governance"
            ]

            # Direct match
            if response_text in valid_categories:
                return response_text

            # Try to find a valid category as substring (e.g., "gouvernance" → "governance")
            for cat in valid_categories:
                if cat in response_text or response_text in cat:
                    return cat

            # Handle French translations
            french_map = {
                "subvention": "subventions",
                "nomination": "appointments",
                "marché": "contracts",
                "urbanisme": "urbanism",
                "environnement": "environment",
                "budget": "budget",
                "immobilier": "real_estate",
                "social": "social",
                "éducation": "education",
                "culture": "culture",
                "sport": "sports",
                "santé": "health",
                "transport": "transport",
                "sécurité": "safety",
                "gouvernance": "governance",
            }
            for fr, en in french_map.items():
                if fr in response_text:
                    return en

            return None
    except Exception as e:
        logger.warning(f"LLM classification failed: {e}")
        return None

async def classify_text_hybrid(text: str) -> tuple[str, list[str]]:
    """Try LLM first, fall back to keyword classification."""
    llm_category = await classify_with_llm(text)
    if llm_category:
        # Get subcategories from keyword classifier for context
        _, subs = keyword_classify(text)
        return llm_category, subs
    return keyword_classify(text)

async def classify_single_decision(decision_id: int):
    """Classify a single decision by ID using hybrid approach."""
    from app.models import SessionLocal, Decision

    db = SessionLocal()
    try:
        decision = db.query(Decision).get(decision_id)
        if not decision or not decision.raw_text:
            return None

        category, subs = await classify_text_hybrid(decision.raw_text)
        decision.category = category
        decision.subcategories = subs
        db.commit()
        return category
    finally:
        db.close()
