"""
Database models for Wellness at Work (WaW) Eye Tracker
Based on PRD specifications
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime

# Compatible import for both SQLAlchemy 1.x and 2.x
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

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


class TrackingSession(Base):
    """A single summary row per tracking session (start/end/total blinks)."""
    __tablename__ = 'tracking_sessions'
    __table_args__ = (
        UniqueConstraint('user_id', 'device_id', 'client_session_id', name='uq_session_per_device'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    client_session_id = Column(String(64), nullable=False)
    started_at_utc = Column(DateTime, nullable=False)
    ended_at_utc = Column(DateTime, nullable=False)
    total_blinks = Column(Integer, nullable=False, default=0)
    device_id = Column(String(255), nullable=False)
    app_version = Column(String(50), nullable=False)

    avg_cpu_percent = Column(Float)
    avg_memory_mb = Column(Float)
    energy_impact = Column(String(20))

    sync_status = Column(String(20), default='synced')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User")

    def __repr__(self):
        return f"<TrackingSession(id={self.id}, user_id={self.user_id}, total_blinks={self.total_blinks})>"

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

class EmailOTP(Base):
    """Stores email OTP codes for signup/verification."""
    __tablename__ = 'email_otps'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<EmailOTP(email={self.email}, consumed={self.consumed})>"


class UserPassword(Base):
    """Stores password hashes for users (separate table to avoid ALTER TABLE migrations)."""
    __tablename__ = 'user_passwords'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserPassword(user_id={self.user_id})>"

# Database connection utilities
def create_database_engine(database_url: str = "sqlite:///waw_local.db", *, echo: bool = False):
    """Create database engine with proper settings.

    - SQLite: allow multi-thread access for local dev.
    - Postgres: enable pool_pre_ping for stale-connection recovery (useful on AWS RDS).
    - Normalize legacy 'postgres://' scheme to 'postgresql://'.
    """
    # Normalize DSN scheme if needed (some providers still use postgres://)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    if database_url.startswith("sqlite"):
        # SQLite specific settings
        engine = create_engine(
            database_url,
            echo=echo,  # Log SQL queries for development
            connect_args={"check_same_thread": False},  # Allow multiple threads
        )
    else:
        # PostgreSQL (or other SQLAlchemy-supported) settings for production
        # pool_pre_ping helps avoid dropped-connection errors (e.g., RDS idle timeouts)
        engine = create_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,
            pool_recycle=1800,  # recycle connections every 30 minutes
        )

    return engine

def get_session_maker(engine):
    """Create sessionmaker for database operations"""
    return sessionmaker(bind=engine)

def init_database(database_url: str = "sqlite:///waw_local.db"):
    """Initialize database with all tables"""
    engine = create_database_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine, get_session_maker(engine)

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
