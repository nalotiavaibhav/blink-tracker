"""
Database models for Wellness at Work (WaW) Eye Tracker
Based on PRD specifications
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """User model as per PRD: id, email, name, consent, created_at"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    consent = Column(Boolean, default=False, nullable=False)  # GDPR compliance
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationship to blink samples
    blink_samples = relationship("BlinkSample", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')>"

class BlinkSample(Base):
    """Blink sample model as per PRD: id, user_id, client_sequence, captured_at_utc, blink_count, device_id, app_version"""
    __tablename__ = 'blink_samples'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    client_sequence = Column(Integer, nullable=False)  # For offline sync ordering
    captured_at_utc = Column(DateTime, nullable=False)
    blink_count = Column(Integer, nullable=False)
    device_id = Column(String(255), nullable=False)  # Unique device identifier
    app_version = Column(String(50), nullable=False)
    
    # Performance metrics from PRD
    cpu_percent = Column(Float)  # CPU usage percentage
    memory_mb = Column(Float)    # Memory usage in MB
    energy_impact = Column(String(20))  # Low/Medium/High
    
    # Additional metadata
    sync_status = Column(String(20), default='pending')  # pending, synced, failed
    created_at = Column(DateTime, default=func.now())
    
    # Relationship to user
    user = relationship("User", back_populates="blink_samples")
    
    def __repr__(self):
        return f"<BlinkSample(id={self.id}, user_id={self.user_id}, blink_count={self.blink_count})>"

class UserSession(Base):
    """Track user login sessions for JWT management"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

# Database connection utilities
def create_database_engine(database_url: str = "sqlite:///waw_local.db"):
    """Create database engine with proper settings"""
    if database_url.startswith("sqlite"):
        # SQLite specific settings
        engine = create_engine(
            database_url, 
            echo=True,  # Log SQL queries for development
            connect_args={"check_same_thread": False}  # Allow multiple threads
        )
    else:
        # PostgreSQL settings for production
        engine = create_engine(database_url, echo=True)
    
    return engine

def get_session_maker(engine):
    """Create sessionmaker for database operations"""
    return sessionmaker(bind=engine)

def init_database(database_url: str = "sqlite:///waw_local.db"):
    """Initialize database with all tables"""
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    return engine, get_session_maker(engine)

# Create default database connection for desktop app
engine, SessionLocal = init_database()

# Example usage for development
if __name__ == "__main__":
    # Initialize local SQLite database
    engine, SessionMaker = init_database()
    session = SessionMaker()
    
    # Create a test user
    test_user = User(
        email="test@example.com",
        name="Test User",
        consent=True
    )
    
    session.add(test_user)
    session.commit()
    
    # Create a test blink sample
    test_sample = BlinkSample(
        user_id=test_user.id,
        client_sequence=1,
        captured_at_utc=datetime.utcnow(),
        blink_count=15,
        device_id="test-device-001",
        app_version="1.0.0",
        cpu_percent=25.5,
        memory_mb=512.0,
        energy_impact="Low"
    )
    
    session.add(test_sample)
    session.commit()
    
    print(f"Created user: {test_user}")
    print(f"Created blink sample: {test_sample}")
    
    session.close()
