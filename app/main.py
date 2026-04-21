from fastapi import FastAPI, Request, Depends, Query, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
import os

from app.models import init_db, get_db, Decision, AlertRule, Alert
from app.scraper import scrape_and_store
from app.extractor import process_pending_decisions
from app.classifier import classify_pending_decisions
from app.alerts import run_alerts_for_new_decisions
from app.scheduler import start_scheduler, run_pipeline

# Ensure database is initialized before first request
init_db()
start_scheduler()

app = FastAPI(title="MairieWatch")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# --- Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    category: str = "",
    page: int = Query(1, ge=1),
):
    per_page = 20
    query = db.query(Decision).filter(Decision.processed == True)
    if q:
        query = query.filter(func.to_tsvector("french", Decision.raw_text).match(q))
    if category:
        query = query.filter(Decision.category == category)
    total = query.count()
    decisions = (
        query.order_by(Decision.scraped_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    categories = [c[0] for c in db.query(Decision.category).distinct().all() if c[0]]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "decisions": decisions,
            "categories": categories,
            "q": q,
            "category": category,
            "page": page,
            "total": total,
            "per_page": per_page,
        },
    )

# HTMX partial for infinite scroll or search updates
@app.get("/partials/decisions", response_class=HTMLResponse)
async def decisions_partial(
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    category: str = "",
    page: int = Query(1, ge=1),
):
    per_page = 20
    query = db.query(Decision).filter(Decision.processed == True)
    if q:
        query = query.filter(func.to_tsvector("french", Decision.raw_text).match(q))
    if category:
        query = query.filter(Decision.category == category)
    total = query.count()
    decisions = (
        query.order_by(Decision.scraped_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return templates.TemplateResponse(
        "partials/decisions.html",
        {
            "request": request,
            "decisions": decisions,
            "page": page,
            "total": total,
            "per_page": per_page,
        },
    )

# --- Decision Detail ---

@app.get("/decision/{decision_id}", response_class=HTMLResponse)
async def decision_detail(request: Request, decision_id: int, db: Session = Depends(get_db)):
    decision = db.query(Decision).get(decision_id)
    return templates.TemplateResponse("decision.html", {"request": request, "decision": decision})

# --- Alert Rules ---

@app.get("/alerts", response_class=HTMLResponse)
async def alerts_dashboard(request: Request, db: Session = Depends(get_db)):
    rules = db.query(AlertRule).all()
    alerts = (
        db.query(Alert)
        .order_by(Alert.sent_at.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(
        "alerts.html",
        {"request": request, "rules": rules, "alerts": alerts},
    )

@app.post("/api/alert-rules")
async def create_alert_rule(
    name: str = Form(...),
    keywords: str = Form(""),
    categories: str = Form(""),
    db: Session = Depends(get_db),
):
    rule = AlertRule(
        user_id=1,  # MVP: single user
        name=name,
        keywords=[k.strip() for k in keywords.split(",") if k.strip()],
        categories=[c.strip() for c in categories.split(",") if c.strip()],
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "name": rule.name}

@app.get("/api/alert-rules")
async def list_alert_rules(db: Session = Depends(get_db)):
    rules = db.query(AlertRule).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "keywords": r.keywords,
            "categories": r.categories,
            "active": r.active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rules
    ]

@app.delete("/api/alert-rules/{rule_id}")
async def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).get(rule_id)
    if not rule:
        return JSONResponse(status_code=404, content={"error": "Rule not found"})
    db.delete(rule)
    db.commit()
    return {"deleted": True}

# --- Alerts Feed ---

@app.get("/api/alerts")
async def list_alerts(
    unseen_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Alert).order_by(Alert.sent_at.desc())
    if unseen_only:
        query = query.filter(Alert.seen == False)
    alerts = query.limit(limit).all()
    return [
        {
            "id": a.id,
            "rule_id": a.rule_id,
            "decision_id": a.decision_id,
            "decision_title": a.decision.title if a.decision else None,
            "decision_category": a.decision.category if a.decision else None,
            "sent_at": a.sent_at.isoformat() if a.sent_at else None,
            "seen": a.seen,
        }
        for a in alerts
    ]

@app.post("/api/alerts/{alert_id}/mark-seen")
async def mark_alert_seen(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).get(alert_id)
    if not alert:
        return JSONResponse(status_code=404, content={"error": "Alert not found"})
    alert.seen = True
    db.commit()
    return {"seen": True}

# --- Pipeline & Stats ---

@app.post("/api/run-pipeline")
async def api_run_pipeline():
    result = await run_pipeline()
    return result

@app.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    total = db.query(Decision).count()
    processed = db.query(Decision).filter(Decision.processed == True).count()
    categorized = db.query(Decision).filter(Decision.category != None).count()
    alerts = db.query(Alert).count()
    return {"total": total, "processed": processed, "categorized": categorized, "alerts": alerts}

# --- Health Check ---

@app.get("/api/health")
async def health():
    return {"status": "ok"}
