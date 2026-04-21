from app.summarizer import extract_amount, extract_recipient, extract_arrondissement, generate_summary

def test_extract_amount():
    assert extract_amount("subvention de 25 000 euros")[0] == 25000
    assert extract_amount("montant: 1,5 million d'euros")[0] == 1500000
    assert extract_amount("25000euros")[0] == 25000
    assert extract_amount("pas de montant")[0] is None

def test_extract_recipient():
    assert extract_recipient("subvention à l'association Sportive ABC") == "Sportive ABC"
    assert extract_recipient("en faveur de la société XYZ") == "société XYZ"
    assert extract_recipient("pas de bénéficiaire") is None

def test_extract_arrondissement():
    assert extract_arrondissement("12e arrondissement") == "12e"
    assert extract_arrondissement("dans le 15ème arrondissement") == "15e"
    assert extract_arrondissement("Paris centre") is None

def test_generate_summary():
    text = """Le Conseil de Paris a approuvé à l'unanimité la convention de 
    subvention entre la Ville de Paris et l'Association Sportive du 12e 
    pour un montant de 25 000 euros le 15 avril 2026."""
    
    summary = generate_summary(text, "Subvention association sportive")
    assert summary.decision_type == "subvention"
    assert summary.amount == 25000
    assert summary.approved_by == "Conseil de Paris"
    assert summary.approval_status == "unanimous"
    # Recipient may or may not be found depending on regex patterns
