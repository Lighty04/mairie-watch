from fastapi import FastAPI, Request, Depends, Query, Form, status, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
import os

from app.models import init_db, get_db, Decision, AlertRule, Alert, User, SessionToken
from app.scraper import scrape_and_store
from app.extractor import process_pending_decisions
from app.classifier import classify_pending_decisions
from app.alerts import run_alerts_for_new_decisions
from app.scheduler import start_scheduler, run_pipeline
from app.metrics import get_all_metrics
from app.auth import (
    create_user, authenticate_user, create_session, get_user_by_token,
    hash_password, can_create_alert, count_user_alert_rules
)

# Ensure database is initialized before first request
init_db()
start_scheduler()

app = FastAPI(title="MairieWatch")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

def get_current_user(request: Request) -> User:
    """Get current user from session cookie."""
    token = request.cookies.get("session")
    if token:
        return get_user_by_token(token)
    return None

from app.advanced_alerts import match_advanced_rule, generate_alert_email
from app.summarizer import generate_summary, format_summary_for_display
from app.slack import send_slack_alert, send_webhook, generate_webhook_payload

# --- Auth Routes ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/auth/register")
async def register(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(""),
):
    try:
        user = create_user(email=email, password=password, name=name or None)
        token = create_session(user.id)
        response.set_cookie(key="session", value=token, httponly=True, max_age=2592000)
        return {"success": True, "user": {"id": user.id, "email": user.email, "role": user.role}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.post("/api/auth/login")
async def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
):
    user = authenticate_user(email, password)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Invalid credentials"})
    token = create_session(user.id)
    response.set_cookie(key="session", value=token, httponly=True, max_age=2592000)
    return {"success": True, "user": {"id": user.id, "email": user.email, "role": user.role}}

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="session")
    return {"success": True}

@app.get("/api/auth/me")
async def me(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "alert_count": count_user_alert_rules(user.id),
        "alert_limit": 3 if user.role == "free" else 999,
    }

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

# --- Advanced Alert Rules (Pro tier) ---

@app.post("/api/alert-rules/advanced")
async def create_advanced_alert_rule(
    request: Request,
    name: str = Form(...),
    keywords: str = Form(""),
    categories: str = Form(""),
    arrondissements: str = Form(""),
    amount_threshold: float = Form(None),
    amount_operator: str = Form("gt"),
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Authentication required"})
    
    # Check tier
    if user.role == "free" and count_user_alert_rules(user.id) >= 3:
        return JSONResponse(status_code=403, content={
            "error": "Free tier limit reached. Upgrade to Pro for unlimited alerts.",
            "upgrade_url": "/pricing"
        })
    
    metadata = {}
    if amount_threshold is not None:
        metadata["amount_threshold"] = amount_threshold
        metadata["amount_operator"] = amount_operator
    
    rule = AlertRule(
        user_id=user.id,
        name=name,
        keywords=[k.strip() for k in keywords.split(",") if k.strip()],
        categories=[c.strip() for c in categories.split(",") if c.strip()],
        arrondissements=[int(a.strip()) for a in arrondissements.split(",") if a.strip().isdigit()],
        metadata_json=metadata,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "name": rule.name, "tier": user.role}

# --- Smart Summaries ---

@app.get("/api/decisions/{decision_id}/summary")
async def get_decision_summary(decision_id: int, db: Session = Depends(get_db)):
    decision = db.query(Decision).get(decision_id)
    if not decision:
        return JSONResponse(status_code=404, content={"error": "Decision not found"})
    
    summary = generate_summary(decision.raw_text or "", decision.title)
    return {
        "decision_id": decision_id,
        "summary": {
            "type": summary.decision_type,
            "recipient": summary.recipient,
            "amount": summary.amount,
            "amount_str": summary.amount_str,
            "approved_by": summary.approved_by,
            "approval_status": summary.approval_status,
            "arrondissement": summary.arrondissement,
            "date": summary.date,
            "context": summary.context,
        },
        "formatted": format_summary_for_display(summary),
    }

# --- Slack / Webhook ---

@app.post("/api/slack/test")
async def test_slack(
    webhook_url: str = Form(...),
    alert_id: int = Form(...),
):
    success = await send_slack_alert(webhook_url, alert_id)
    return {"sent": success}

@app.post("/api/webhook/test")
async def test_webhook(
    webhook_url: str = Form(...),
    alert_id: int = Form(...),
):
    success = await send_webhook(webhook_url, alert_id)
    return {"sent": success}

# --- Pricing ---

@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    return templates.TemplateResponse("pricing.html", {"request": request})

# --- Metrics ---

@app.get("/api/metrics")
async def api_metrics():
    return get_all_metrics()

@app.get("/metrics", response_class=HTMLResponse)
async def metrics_dashboard(request: Request):
    return templates.TemplateResponse("metrics.html", {"request": request})

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
