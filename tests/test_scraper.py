from app.scraper import parse_decisions

def test_parse_links():
    html = '''
    <div class="itemODS">
        <div class="itemODS_article">
            <h3>Décision sur les subventions</h3>
            <div class="itemODS_content">Séance du 14 avril 2026</div>
        </div>
        <ul class="custom-list list-files">
            <li>
                <a href="jsp/site/plugins/solr/modules/ods/DoDownload.jsp?id_document=12345"
                   title="Télécharger le PDF">Télécharger le PDF 0</a>
            </li>
        </ul>
    </div>
    <div class="itemODS">
        <div class="itemODS_article">
            <h3>Nomination des représentants</h3>
            <div class="itemODS_content">Séance du 10 mars 2025</div>
        </div>
        <ul class="custom-list list-files">
            <li>
                <a href="jsp/site/plugins/solr/modules/ods/DoDownload.jsp?id_document=67890"
                   title="Télécharger le PDF">Télécharger le PDF 0</a>
            </li>
        </ul>
    </div>
    '''
    results = parse_decisions(html)
    assert len(results) == 2
    assert results[0]["title"] == "Décision sur les subventions"
    assert "12345" in results[0]["pdf_url"]
    assert results[0]["published_at"].year == 2026
    assert results[0]["published_at"].month == 4
    assert results[0]["published_at"].day == 14

def test_parse_no_results():
    html = "<html><body><p>No decisions today</p></body></html>"
    results = parse_decisions(html)
    assert results == []

def test_parse_missing_pdf():
    html = '''
    <div class="itemODS">
        <h3>No PDF here</h3>
    </div>
    '''
    results = parse_decisions(html)
    assert len(results) == 0

def test_parse_decision_number():
    html = '''
    <div class="itemODS">
        <div class="itemODS_article">
            <h3>Budget modification</h3>
            <div class="itemODS_content">
                Séance du 20 janvier 2024
                2024 BUDG 15-2
            </div>
        </div>
        <ul class="custom-list list-files">
            <li>
                <a href="DoDownload.jsp?id_document=99999">Télécharger le PDF 0</a>
            </li>
        </ul>
    </div>
    '''
    results = parse_decisions(html)
    assert len(results) == 1
    assert results[0]["decision_number"] == "2024 BUDG 15-2"
    assert results[0]["published_at"].year == 2024
    assert results[0]["published_at"].month == 1
    assert results[0]["published_at"].day == 20
