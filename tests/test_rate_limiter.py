"""Tests for rate limiting middleware."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date
from app.models import Base, User, ApiUsage
from app.rate_limiter import get_api_usage_count, record_api_usage, TIER_LIMITS, get_today_str

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_rate_limiter.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_get_api_usage_count_empty(db_session):
    """Usage count is 0 when no records exist."""
    count = get_api_usage_count(db_session, 1, "/api/decisions")
    assert count == 0

def test_record_api_usage_creates_record(db_session):
    """Recording usage creates a new record."""
    record_api_usage(db_session, 1, "/api/decisions")
    db_session.commit()
    
    usage = db_session.query(ApiUsage).filter_by(user_id=1).first()
    assert usage is not None
    assert usage.count == 1
    assert usage.endpoint == "/api/decisions"
    assert usage.date == get_today_str()

def test_record_api_usage_increments(db_session):
    """Recording usage increments existing record."""
    record_api_usage(db_session, 1, "/api/decisions")
    record_api_usage(db_session, 1, "/api/decisions")
    db_session.commit()
    
    usage = db_session.query(ApiUsage).filter_by(user_id=1).first()
    assert usage.count == 2

def test_different_endpoints_separate_counts(db_session):
    """Different endpoints have separate counts."""
    record_api_usage(db_session, 1, "/api/decisions")
    record_api_usage(db_session, 1, "/api/alerts")
    db_session.commit()
    
    assert get_api_usage_count(db_session, 1, "/api/decisions") == 1
    assert get_api_usage_count(db_session, 1, "/api/alerts") == 1

def test_different_users_separate_counts(db_session):
    """Different users have separate counts."""
    record_api_usage(db_session, 1, "/api/decisions")
    record_api_usage(db_session, 2, "/api/decisions")
    db_session.commit()
    
    assert get_api_usage_count(db_session, 1) == 1
    assert get_api_usage_count(db_session, 2) == 1

def test_tier_limits_defined(db_session):
    """Tier limits are defined correctly."""
    assert TIER_LIMITS["free"] == 10
    assert TIER_LIMITS["pro"] == 100
    assert TIER_LIMITS["admin"] == -1
