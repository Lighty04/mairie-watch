from datetime import date
from sqlalchemy.orm import Session
from .models import SummaryUsage
from typing import Literal

# Define user roles for clarity
UserRole = Literal["free", "pro", "admin"]

# Constants
FREE_TIER_LIMIT = 3

def get_today_date_str() -> str:
    """Returns today's date in 'YYYY-MM-DD' format."""
    return date.today().strftime("%Y-%m-%d")

def get_remaining_summaries(user_id: int, role: str, db: Session) -> int:
    """
    Get remaining summaries for today.
    Returns -1 for unlimited.
    """
    if role in ["pro", "admin"]:
        return -1
    
    # Check usage for Free tier
    usage = db.query(SummaryUsage).filter(
        SummaryUsage.user_id == user_id,
        SummaryUsage.date == get_today_date_str()
    ).first()
    
    if usage:
        return FREE_TIER_LIMIT - usage.count
    else:
        return FREE_TIER_LIMIT

def can_generate_summary(user_id: int, role: str, db: Session) -> bool:
    """Check if user can generate a summary today."""
    remaining = get_remaining_summaries(user_id, role, db)
    return remaining > 0 or remaining == -1

def record_summary_usage(user_id: int, db: Session) -> None:
    """Increment today's summary usage for user."""
    today_str = get_today_date_str()
    
    # Try to find existing usage record
    usage = db.query(SummaryUsage).filter(
        SummaryUsage.user_id == user_id,
        SummaryUsage.date == today_str
    ).first()
    
    if usage:
        # Increment count
        usage.count += 1
    else:
        # Create new record
        new_usage = SummaryUsage(user_id=user_id, date=today_str, count=1)
        db.add(new_usage)
        
    db.flush()