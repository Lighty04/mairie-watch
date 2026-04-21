from app.comparison import normalize_beneficiary

def test_normalize_beneficiary():
    assert normalize_beneficiary("Association Sportive ABC") == "association sportive abc"
    assert normalize_beneficiary("XYZ SARL") == "xyz"  # suffix removal
    assert normalize_beneficiary("  Association   Test  ") == "association test"
    assert normalize_beneficiary("") == ""
    assert normalize_beneficiary(None) == ""
