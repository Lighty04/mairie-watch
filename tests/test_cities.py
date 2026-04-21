from app.city_scrapers import get_enabled_cities, get_city_config, get_scraper, ParisScraper, SCRAPER_REGISTRY

def test_get_enabled_cities():
    cities = get_enabled_cities()
    assert "paris" in cities
    assert "marseille" in cities
    assert "lyon" in cities
    assert "bordeaux" not in cities  # disabled

def test_get_city_config():
    paris = get_city_config("paris")
    assert paris["name"] == "Paris"
    assert paris["enabled"] is True
    assert paris["arrondissements"] == 20
    
    lyon = get_city_config("lyon")
    assert lyon["name"] == "Lyon"
    assert lyon["enabled"] is True

def test_scraper_registry():
    assert "paris" in SCRAPER_REGISTRY
    assert "marseille" in SCRAPER_REGISTRY
    assert "lyon" in SCRAPER_REGISTRY

def test_paris_scraper():
    scraper = ParisScraper()
    assert scraper.city_slug == "paris"
    assert scraper.config["name"] == "Paris"
