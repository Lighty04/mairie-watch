"""API rate limiting by user tier.

Free: 10/day
Pro: 100/day
Team/Enterprise: unlimited
"""

from datetime import date
from fastapi import Request
from fastapi.responses import JSONResponse
from app.models import SessionLocal, ApiUsage
from app.auth import get_user_by_token

TIER_LIMITS = {
    "free": 10,
    "pro": 100,
    "admin": -1,  # unlimited
}

def get_today_str() -> str:
    return date.today().strftime("%Y-%m-%d")

def get_api_usage_count(db, user_id: int, endpoint: str = None) -> int:
    """Get today's API usage count for a user."""
    q = db.query(ApiUsage).filter(
        ApiUsage.user_id == user_id,
        ApiUsage.date == get_today_str(),
    )
    if endpoint:
        q = q.filter(ApiUsage.endpoint == endpoint)
    
    usage = q.first()
    return usage.count if usage else 0

def record_api_usage(db, user_id: int, endpoint: str) -> None:
    """Record an API call."""
    today = get_today_str()
    usage = db.query(ApiUsage).filter(
        ApiUsage.user_id == user_id,
        ApiUsage.date == today,
        ApiUsage.endpoint == endpoint,
    ).first()
    
    if usage:
        usage.count += 1
    else:
        usage = ApiUsage(user_id=user_id, date=today, endpoint=endpoint, count=1)
        db.add(usage)

async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware: check rate limits for /api/* routes."""
    path = request.url.path
    
    # Skip exempt routes
    if path.startswith("/api/auth/") or path == "/api/health":
        return await call_next(request)
    
    if not path.startswith("/api/"):
        return await call_next(request)
    
    # Get user from session
    token = request.cookies.get("session")
    user = None
    if token:
        user = get_user_by_token(token)
    
    if not user:
        tier = "free"
        user_id = 0
    else:
        tier = user.role
        user_id = user.id
        request.state.user = user
    
    # Check if unlimited
    limit = TIER_LIMITS.get(tier, 10)
    if limit == -1:
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = "unlimited"
        response.headers["X-RateLimit-Remaining"] = "unlimited"
        return response
    
    # Check usage
    db = SessionLocal()
    try:
        count = get_api_usage_count(db, user_id, path)
        if count >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "API rate limit exceeded.",
                    "upgrade_url": "/pricing",
                    "limit": limit,
                    "used": count,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(date.today().replace(hour=23, minute=59).timestamp())),
                },
            )
        
        # Record usage
        record_api_usage(db, user_id, path)
        db.commit()
        
        remaining = limit - count - 1
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response
    finally:
        db.close()