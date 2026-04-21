from fastapi import FastAPI, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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

init_db()
start_scheduler()

app = FastAPI(title="MairieWatch")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), q: str = "", category: str = "", page: int = 1):
    per_page = 20
    query = db.query(Decision).filter(Decision.processed == True)
    if q:
        query = query.filter(func.to_tsvector("french", Decision.raw_text).match(q))
    if category:
        query = query.filter(Decision.category == category)
    total = query.count()
    decisions = query.order_by(Decision.scraped_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    categories = [c[0] for c in db.query(Decision.category).distinct().all() if c[0]]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "decisions": decisions,
        "categories": categories,
        "q": q,
        "category": category,
        "page": page,
        "total": total,
        "per_page": per_page,
    })

@app.get("/decision/{decision_id}", response_class=HTMLResponse)
async def decision_detail(request: Request, decision_id: int, db: Session = Depends(get_db)):
    decision = db.query(Decision).get(decision_id)
    return templates.TemplateResponse("decision.html", {"request": request, "decision": decision})

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
