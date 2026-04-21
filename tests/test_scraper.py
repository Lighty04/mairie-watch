from app.scraper import parse_decision_links

def test_parse_links():
    html = '''
    <html>
    <body>
        <a href="/doc/decision1.pdf">Décision 1</a>
        <a href="https://example.com/doc.pdf">External PDF</a>
        <a href="/page.html">Not a PDF</a>
    </body>
    </html>
    '''
    results = parse_decision_links(html)
    assert len(results) == 2
    assert results[0]["title"] == "Décision 1"
    assert results[0]["pdf_url"] == "https://www.paris.fr/doc/decision1.pdf"
    assert results[1]["pdf_url"] == "https://example.com/doc.pdf"

def test_parse_no_links():
    html = "<html><body><p>No decisions today</p></body></html>"
    results = parse_decision_links(html)
    assert results == []
