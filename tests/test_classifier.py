from app.classifier import classify_text

def test_classify_subvention():
    text = "Le conseil municipal a voté une subvention de 50 000 euros à l'association ABC."
    cat, subs = classify_text(text)
    assert cat == "subventions"

def test_classify_appointment():
    text = "Désignation de M. Dupont en tant que membre de droit du conseil d'administration."
    cat, subs = classify_text(text)
    assert cat == "appointments"

def test_classify_contract():
    text = "Marché public pour la rénovation des écoles du 12e arrondissement."
    cat, subs = classify_text(text)
    assert cat == "contracts"

def test_classify_empty():
    cat, subs = classify_text("")
    assert cat == "uncategorized"
    assert subs == []

def test_multiple_categories():
    text = "Subvention pour un projet environnemental et désignation d'un conseiller."
    cat, subs = classify_text(text)
    assert cat in ("subventions", "appointments", "environment")

def test_subcategories():
    text = "Subvention culturelle et marché public pour un spectacle."
    cat, subs = classify_text(text)
    assert cat == "subventions" or cat == "contracts" or cat == "culture"
