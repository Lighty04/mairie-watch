# MairieWatch

Automated monitoring and alerting system for municipal decisions across French cities, starting with Paris.

## What it does

1. **Monitors** official municipal publication sites for new PDFs
2. **Extracts** text from deliberations, arrêtés, and other decisions
3. **Categorizes** decisions: subventions, appointments, contracts, urbanism, etc.
4. **Alerts** users when decisions match their keywords or areas of interest
5. **Archives** everything with full-text search

## MVP (Paris only)

- Scans Paris municipal decisions (https://www.paris.fr/decisions)
- Extracts text from PDFs
- Auto-categorizes with keyword rules
- Web dashboard: timeline, search, filters
- Alert system: keyword + category based
- Free tier: 3 alerts | Pro: €39/mo unlimited

## Tech Stack

- Backend: FastAPI
- Database: PostgreSQL + pg_trgm (full-text search)
- PDF parsing: pdfplumber
- NLP: local LLM / keyword rules (MVP)
- Frontend: HTML + HTMX
- Deployment: Docker
- Scheduling: APScheduler

## Project Structure

```
mairie-watch/
├── app/              # FastAPI application
│   ├── main.py
│   ├── models.py
│   ├── scraper.py    # PDF monitoring + download
│   ├── extractor.py  # PDF text extraction
│   ├── classifier.py # Auto-categorization
│   ├── alerts.py     # Alert rules + notifications
│   └── templates/    # HTMX frontend
├── tests/
├── docker-compose.yml
└── README.md
```

## Running locally

```bash
docker-compose up -d
```

## License

MIT
