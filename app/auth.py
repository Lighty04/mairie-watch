import hashlib
import secrets
from datetime import datetime, timedelta

from app.models import User, SessionToken, SessionLocal, AlertRule

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email: str, password: str, name: str = None, role: str = "free"):
    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(User).filter_by(email=email.lower().strip()).first()
        if existing:
            raise ValueError("Email already registered")
        
        user = User(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            name=name,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()

def authenticate_user(email: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email.lower().strip(), active=True).first()
        if user and user.password_hash == hash_password(password):
            user.last_login = datetime.utcnow()
            db.commit()
            return user
        return None
    finally:
        db.close()

def create_session(user_id: int, days: int = 30):
    db = SessionLocal()
    try:
        token = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(days=days)
        session = SessionToken(user_id=user_id, token=token, expires_at=expires)
        db.add(session)
        db.commit()
        return token
    finally:
        db.close()

def get_user_by_token(token: str):
    if not token:
        return None
    db = SessionLocal()
    try:
        session = db.query(SessionToken).filter_by(token=token).first()
        if session and session.expires_at > datetime.utcnow():
            return db.query(User).get(session.user_id)
        return None
    finally:
        db.close()

def count_user_alert_rules(user_id: int) -> int:
    db = SessionLocal()
    try:
        return db.query(AlertRule).filter_by(user_id=user_id, active=True).count()
    finally:
        db.close()

def can_create_alert(user_id: int) -> bool:
    """Check if user can create another alert (free tier = 3 max)."""
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user:
            return False
        if user.role == "pro" or user.role == "admin":
            return True
        return count_user_alert_rules(user_id) < 3
    finally:
        db.close()
