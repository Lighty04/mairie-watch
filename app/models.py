from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, Index, func, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./data/mairie_watch.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    name = Column(String(128))
    role = Column(String(16), default="free")  # free, pro, admin
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    active = Column(Boolean, default=True)

class SessionToken(Base):
    __tablename__ = "session_tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    source_url = Column(String(2048), nullable=False, index=True)
    pdf_url = Column(String(2048), nullable=False)
    title = Column(Text)
    raw_text = Column(Text)
    category = Column(String(64), index=True)
    subcategories = Column(JSON, default=list)
    metadata_json = Column(JSON, default=dict)
    published_at = Column(DateTime, index=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)

    alerts = relationship("Alert", back_populates="decision", lazy="dynamic")

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    keywords = Column(JSON, default=list)  # list of strings
    categories = Column(JSON, default=list)  # list of category strings
    arrondissements = Column(JSON, default=list)  # list of int 1-20
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)  # advanced rules: amount_threshold, etc.

    alerts = relationship("Alert", back_populates="rule", lazy="dynamic")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False, index=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=False, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    seen = Column(Boolean, default=False)

    decision = relationship("Decision", back_populates="alerts")
    rule = relationship("AlertRule", back_populates="alerts")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
