# MairieWatch — Project Agent Rules

## QA Checklist (Pre-Deploy)

- [ ] Tests pass: `pytest tests/`
- [ ] Docker build succeeds: `docker build .`
- [ ] Local run: `docker-compose up -d`, verify http://localhost:8000/
- [ ] PDF extraction works with real Paris PDF
- [ ] Classifier tags decisions correctly (spot-check 5)
- [ ] Pipeline runs without errors (trigger /api/run-pipeline)

## Deployment Targets

- **Primary:** decisionhelper@192.168.0.16 (see deploy-decisionhelper skill)
- **Future:** VPS with Docker Compose

## Data Directory

- `/app/data/pdfs/` — Downloaded PDFs (persistent volume)

## Non-Regression Tests

When fixing PDF extraction or classification bugs, add a test in `tests/` with the failing PDF text snippet.
