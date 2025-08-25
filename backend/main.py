"""
FastAPI Backend for Wellness at Work (WaW) Eye Tracker
Based on PRD API specifications:
- GET /v1/me → user profile
- POST /v1/blinks → batch upload blink samples  
- GET /v1/blinks → fetch blink data (date-filtered)
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import os
from dotenv import load_dotenv

# Import our models
from .models import init_database, User, BlinkSample, UserSession

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Wellness at Work API",
    description="Cloud-synced eye tracker backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-dashboard.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///waw_local.db")
engine, SessionMaker = init_database(DATABASE_URL)

# Security
security = HTTPBearer()

# Pydantic models for API requests/responses
class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    consent: bool
    created_at: datetime

    class Config:
        from_attributes = True

class BlinkSampleRequest(BaseModel):
    client_sequence: int
    captured_at_utc: datetime
    blink_count: int
    device_id: str
    app_version: str
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    energy_impact: Optional[str] = None

    @validator('energy_impact')
    def validate_energy_impact(cls, v):
        if v and v not in ['Low', 'Medium', 'High']:
            raise ValueError('energy_impact must be Low, Medium, or High')
        return v

class BlinkSampleResponse(BaseModel):
    id: int
    client_sequence: int
    captured_at_utc: datetime
    blink_count: int
    device_id: str
    app_version: str
    cpu_percent: Optional[float]
    memory_mb: Optional[float]
    energy_impact: Optional[str]
    sync_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class BatchBlinkRequest(BaseModel):
    samples: List[BlinkSampleRequest]

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Database dependency
def get_db():
    session = SessionMaker()
    try:
        yield session
    finally:
        session.close()

# Authentication dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Extract and validate JWT token to get current user"""
    token = credentials.credentials
    
    # For now, simple session token lookup (replace with JWT in production)
    session_record = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == session_record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

# API Endpoints

@app.get("/")
async def root():
    return {"message": "Wellness at Work API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/v1/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """User login endpoint - simplified for MVP"""
    # In production, verify password hash
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        # For MVP, create user if doesn't exist
        user = User(
            email=login_data.email,
            name=login_data.email.split('@')[0],  # Simple name extraction
            consent=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create session token (simplified - use JWT in production)
    import secrets
    token = secrets.token_urlsafe(32)
    
    session = UserSession(
        user_id=user.id,
        session_token=token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()
    
    return LoginResponse(
        access_token=token,
        user=UserResponse.from_orm(user)
    )

@app.get("/v1/me", response_model=UserResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse.from_orm(current_user)

@app.post("/v1/blinks")
async def upload_blink_samples(
    batch_data: BatchBlinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Batch upload blink samples - handles offline sync"""
    
    if not current_user.consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User consent required for data collection"
        )
    
    created_samples = []
    
    for sample_data in batch_data.samples:
        # Check for duplicate client_sequence to handle retry scenarios
        existing_sample = db.query(BlinkSample).filter(
            BlinkSample.user_id == current_user.id,
            BlinkSample.client_sequence == sample_data.client_sequence,
            BlinkSample.device_id == sample_data.device_id
        ).first()
        
        if existing_sample:
            # Update sync status if needed
            existing_sample.sync_status = 'synced'
            continue
        
        # Create new blink sample
        blink_sample = BlinkSample(
            user_id=current_user.id,
            **sample_data.dict(),
            sync_status='synced'
        )
        
        db.add(blink_sample)
        created_samples.append(blink_sample)
    
    db.commit()
    
    return {
        "message": f"Successfully processed {len(batch_data.samples)} samples",
        "created": len(created_samples),
        "duplicates": len(batch_data.samples) - len(created_samples)
    }

@app.get("/v1/blinks", response_model=List[BlinkSampleResponse])
async def get_blink_samples(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 1000,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch user's blink data with optional date filtering"""
    
    query = db.query(BlinkSample).filter(BlinkSample.user_id == current_user.id)
    
    if start_date:
        query = query.filter(BlinkSample.captured_at_utc >= start_date)
    
    if end_date:
        query = query.filter(BlinkSample.captured_at_utc <= end_date)
    
    samples = query.order_by(BlinkSample.captured_at_utc.desc()).limit(limit).all()
    
    return [BlinkSampleResponse.from_orm(sample) for sample in samples]

@app.get("/v1/blinks/summary")
async def get_blink_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get aggregated blink statistics for dashboard"""
    
    from sqlalchemy import func
    
    query = db.query(BlinkSample).filter(BlinkSample.user_id == current_user.id)
    
    if start_date:
        query = query.filter(BlinkSample.captured_at_utc >= start_date)
    
    if end_date:
        query = query.filter(BlinkSample.captured_at_utc <= end_date)
    
    # Aggregate statistics
    summary = query.with_entities(
        func.sum(BlinkSample.blink_count).label('total_blinks'),
        func.avg(BlinkSample.blink_count).label('avg_blinks'),
        func.count(BlinkSample.id).label('sample_count'),
        func.avg(BlinkSample.cpu_percent).label('avg_cpu'),
        func.avg(BlinkSample.memory_mb).label('avg_memory')
    ).first()
    
    return {
        "total_blinks": summary.total_blinks or 0,
        "average_blinks_per_sample": round(summary.avg_blinks or 0, 2),
        "total_samples": summary.sample_count or 0,
        "average_cpu_percent": round(summary.avg_cpu or 0, 2),
        "average_memory_mb": round(summary.avg_memory or 0, 2),
        "period": {
            "start_date": start_date,
            "end_date": end_date
        }
    }

# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
