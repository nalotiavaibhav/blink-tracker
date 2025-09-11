"""
FastAPI Backend for Wellness at Work (WaW) Eye Tracker
Based on PRD API specifications:
- GET /v1/me → user profile
- POST /v1/blinks → batch upload blink samples  
- GET /v1/blinks → fetch blink data (date-filtered)
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

# JWT and Google Auth
from jose import JWTError, jwt
from pydantic import BaseModel, validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.emailer import send_email

# Import our models
# Import within package context so `uvicorn backend.main:app` works
from backend.models import (
    BlinkSample,
    EmailOTP,
    TrackingSession,
    User,
    UserPassword,
    UserSession,
    init_database,
)

# Load environment variables without overriding already-specified runtime env
load_dotenv(override=False)

# Initialize FastAPI app
app = FastAPI(
    title="Wellness at Work API",
    description="Cloud-synced eye tracker backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Basic logger (can be configured externally for production)
logger = logging.getLogger("waw.backend")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Simple in-memory rate limiting for auth endpoints (MVP) ---
# Not suitable for multi-process / distributed deployments; use Redis in production.
from collections import defaultdict, deque
from time import time as _time

RATE_LIMIT_WINDOW_SEC = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW", "300"))  # 5 minutes
RATE_LIMIT_MAX_ATTEMPTS = int(
    os.getenv("LOGIN_RATE_LIMIT_MAX", "10")
)  # attempts per (email, ip)
RATE_LIMIT_BLOCK_SECONDS = int(
    os.getenv("LOGIN_BLOCK_SECONDS", "300")
)  # block duration after exceeding

_login_attempts: dict = defaultdict(lambda: deque())  # key -> deque[timestamps]
_login_blocks: dict = {}  # key -> unblock_epoch


def _rate_limit_key(email: str, request: Request):
    ip = getattr(request.client, "host", "unknown") if request else "unknown"
    return f"{email.lower()}|{ip}" if email else f"-|{ip}"


def _prune_attempts(dq: deque, now_ts: float):
    # Remove timestamps older than window
    while dq and (now_ts - dq[0]) > RATE_LIMIT_WINDOW_SEC:
        dq.popleft()


def check_login_rate_limit(email: str, request: Request):
    if RATE_LIMIT_MAX_ATTEMPTS <= 0:
        return  # disabled
    now_ts = _time()
    key = _rate_limit_key(email, request)
    # If blocked
    unblock = _login_blocks.get(key)
    if unblock and now_ts < unblock:
        retry_after = int(unblock - now_ts)
        raise HTTPException(
            status_code=429, detail=f"Too many attempts. Retry in {retry_after}s"
        )
    dq = _login_attempts[key]
    _prune_attempts(dq, now_ts)
    if len(dq) >= RATE_LIMIT_MAX_ATTEMPTS:
        # Block further attempts
        _login_blocks[key] = now_ts + RATE_LIMIT_BLOCK_SECONDS
        del _login_attempts[key]
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Retry in {RATE_LIMIT_BLOCK_SECONDS}s",
        )
    # Record attempt (even before success); success path will clear on demand
    dq.append(now_ts)


def clear_login_attempts(email: str, request: Request):
    key = _rate_limit_key(email, request)
    _login_attempts.pop(key, None)
    _login_blocks.pop(key, None)


# In-memory debug token registry (prefix -> metadata) when AUTH_DEBUG enabled
DEBUG_TOKENS: dict = {}

# Static assets (favicons, icons)
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
if ASSETS_DIR.exists():
    # Serve under /assets (e.g., /assets/favicon-32x32.png)
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/favicon.ico")
def favicon():
    """Serve root favicon for browsers and Swagger UI."""
    icon_path = ASSETS_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path)
    raise HTTPException(status_code=404, detail="favicon not found")


# CORS middleware for web dashboard
# Read origins from env var CORS_ORIGINS (JSON array or comma-separated),
# fallback to local defaults.
def _load_cors_origins():
    raw = os.getenv("CORS_ORIGINS")
    if not raw:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://your-dashboard.com",
        ]
    try:
        import json

        origins = json.loads(raw)
        if isinstance(origins, list):
            return [str(o) for o in origins]
    except Exception:
        # Not JSON, treat as comma separated
        pass
    return [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///waw_local.db")
engine, SessionMaker = init_database(DATABASE_URL)

# --- Readiness state ---
READINESS_OK = False


@app.on_event("startup")
def startup_checks():
    """Perform basic startup checks (DB connectivity)."""
    global READINESS_OK
    if os.getenv("DISABLE_STARTUP_DB_CHECK", "false").lower() in ("1", "true", "yes"):
        logger.warning(
            "Startup DB connectivity check disabled via DISABLE_STARTUP_DB_CHECK"
        )
        READINESS_OK = True
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        READINESS_OK = True
        logger.info("Startup checks: database connectivity OK")
    except Exception as e:
        READINESS_OK = False
        logger.error("Startup checks failed: database connectivity error: %s", e)

    # Warn if using shared admin password (temporary model)
    if os.getenv("ADMIN_SHARED_PASSWORD"):
        logger.warning(
            "Using shared admin password model; replace with per-admin hashed passwords for production hardening."
        )


# Security
security = HTTPBearer()
JWT_SECRET = os.getenv(
    "JWT_SECRET", os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
)
JWT_ALG = os.getenv("JWT_ALGORITHM", os.getenv("JWT_ALG", "HS256"))
JWT_EXPIRES_MIN = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", os.getenv("JWT_EXPIRES_MIN", "10080"))
)  # default 7 days; allow fallback env

# Shared admin password (simple gate) - for the small deployment scenario
ADMIN_SHARED_PASSWORD = os.getenv("ADMIN_SHARED_PASSWORD", "admin@waw")

# Google OAuth config (desktop app client ID)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


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

    @validator("energy_impact")
    def validate_energy_impact(cls, v):
        if v and v not in ["Low", "Medium", "High"]:
            raise ValueError("energy_impact must be Low, Medium, or High")
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


class SendOtpRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    code: str
    password: Optional[str] = None  # Optional password set during signup


class GoogleLoginRequest(BaseModel):
    id_token: str


class SetPasswordRequest(BaseModel):
    password: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    email: str
    code: str
    new_password: str


class TrackingSessionRequest(BaseModel):
    client_session_id: str
    started_at_utc: datetime
    ended_at_utc: datetime
    total_blinks: int
    device_id: str
    app_version: str
    avg_cpu_percent: Optional[float] = None
    avg_memory_mb: Optional[float] = None
    energy_impact: Optional[str] = None

    @validator("energy_impact")
    def validate_energy_impact(cls, v):
        if v and v not in ["Low", "Medium", "High"]:
            raise ValueError("energy_impact must be Low, Medium, or High")
        return v


class TrackingSessionResponse(BaseModel):
    id: int
    client_session_id: str
    started_at_utc: datetime
    ended_at_utc: datetime
    total_blinks: int
    device_id: str
    app_version: str
    avg_cpu_percent: Optional[float]
    avg_memory_mb: Optional[float]
    energy_impact: Optional[str]
    sync_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BatchTrackingSessionRequest(BaseModel):
    sessions: List[TrackingSessionRequest]


# Database dependency
def get_db():
    session = SessionMaker()
    try:
        yield session
    finally:
        session.close()


def create_access_token(
    *,
    user_id: int,
    email: str,
    expires_minutes: int = JWT_EXPIRES_MIN,
    scope: str = "user",
) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
        "scope": scope,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    if os.getenv("AUTH_DEBUG"):
        logger.info(
            "AUTH_DEBUG: issued JWT sub=%s scope=%s iat=%s exp=%s prefix=%s",
            payload["sub"],
            scope,
            payload["iat"],
            payload["exp"],
            token[:16],
        )
    # Store for later inspection
    DEBUG_TOKENS[token[:16]] = payload
    return token


def decode_access_token(token: str) -> Optional[dict]:
    try:
        # Disable built-in exp verification (was falsely triggering) and verify manually.
        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG],
            options={"verify_aud": False, "verify_exp": False},
        )
        exp = decoded.get("exp")
        now_ts = int(datetime.utcnow().timestamp())
        if exp is not None and not os.getenv("JWT_IGNORE_EXPIRATION"):
            if exp + 300 < now_ts:  # expired more than 5 minutes ago
                if os.getenv("AUTH_DEBUG"):
                    logger.warning(
                        "AUTH_DEBUG: manual exp check fail exp=%s now=%s delta=%s prefix=%s",
                        exp,
                        now_ts,
                        exp - now_ts,
                        token[:16],
                    )
                return None
            if os.getenv("AUTH_DEBUG"):
                logger.info(
                    "AUTH_DEBUG: manual exp ok exp=%s now=%s remaining=%s prefix=%s",
                    exp,
                    now_ts,
                    exp - now_ts,
                    token[:16],
                )
        return decoded
    except JWTError as e:
        if os.getenv("AUTH_DEBUG"):
            logger.warning(
                "AUTH_DEBUG: JWT decode exception (%s) prefix=%s", e, token[:16]
            )
        return None


if os.getenv("AUTH_DEBUG"):
    logger.info(
        "AUTH_DEBUG: startup jwt_alg=%s secret_hash=%s expires_min=%s",
        JWT_ALG,
        hash(JWT_SECRET),
        JWT_EXPIRES_MIN,
    )

    @app.middleware("http")
    async def auth_debug_mw(request: Request, call_next):
        auth = request.headers.get("Authorization") or request.headers.get(
            "authorization"
        )
        if auth and auth.lower().startswith("bearer "):
            token_part = auth.split(None, 1)[1]
            logger.info(
                "AUTH_DEBUG: inbound bearer len=%s prefix=%s",
                len(token_part),
                token_part[:24],
            )
        return await call_next(request)

    @app.get("/v1/debug/time")
    async def debug_time():
        now_dt = datetime.utcnow()
        now_ts = int(now_dt.timestamp())
        return {"utc_iso": now_dt.isoformat() + "Z", "epoch": now_ts}

    @app.get("/v1/debug/tokens")
    async def debug_tokens():
        return {"count": len(DEBUG_TOKENS), "tokens": DEBUG_TOKENS}


# Authentication dependency
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Extract and validate token to get current user. Prefer JWT; fallback to legacy session token."""
    token = credentials.credentials
    # Try JWT first
    payload = decode_access_token(token)
    if payload and payload.get("sub"):
        user = db.query(User).filter(User.id == int(payload["sub"])).first()
        if not user:
            if os.getenv("AUTH_DEBUG"):
                logger.warning(
                    "AUTH_DEBUG: JWT sub %s not found in DB", payload.get("sub")
                )
            raise HTTPException(status_code=404, detail="User not found")
        if os.getenv("AUTH_DEBUG"):
            logger.info(
                "AUTH_DEBUG: token ok for user_id=%s scope=%s exp=%s now=%s",
                user.id,
                payload.get("scope"),
                payload.get("exp"),
                int(datetime.utcnow().timestamp()),
            )
        return user
    # Fallback: legacy session token
    session_record = (
        db.query(UserSession)
        .filter(
            UserSession.session_token == token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if session_record:
        user = db.query(User).filter(User.id == session_record.user_id).first()
        if user:
            return user
    if os.getenv("AUTH_DEBUG"):
        logger.warning(
            "AUTH_DEBUG: auth failure. jwt_decoded=%s legacy_session_found=%s prefix=%s",
            bool(payload),
            bool(session_record),
            token[:10],
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


# API Endpoints


@app.get("/")
async def root():
    return {"message": "Wellness at Work API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.get("/health/liveness")
async def liveness():
    """Container / process liveness probe (no external deps)."""
    return {"status": "alive", "time": datetime.utcnow()}


@app.get("/health/readiness")
async def readiness():
    """Readiness probe (verifies DB connectivity succeeded at startup)."""
    global READINESS_OK
    if not READINESS_OK:
        # Attempt a quick re-check (for transient startup ordering issues)
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            READINESS_OK = True
        except Exception:
            raise HTTPException(status_code=503, detail="Not ready")
    return {"status": "ready", "time": datetime.utcnow()}


@app.post("/v1/auth/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    """User login endpoint - simplified for MVP"""
    # In production, verify password hash
    email = login_data.email.strip().lower()
    # Rate limit check
    try:
        check_login_rate_limit(email, request)
    except HTTPException:
        # do not leak whether email exists
        raise
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Only auto-create when explicitly allowed via env flag
        allow_auto = os.getenv("ALLOW_AUTO_USER_CREATE", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if not allow_auto:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user = User(email=email, name=email.split("@")[0], consent=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Determine admin scope via env var list & enforce shared password if admin
    admin_emails = {
        e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    }
    is_admin = user.email.lower() in admin_emails
    if is_admin:
        # Enforce shared admin password; reject if mismatch
        if login_data.password != ADMIN_SHARED_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    scope = "admin" if is_admin else "user"
    # Success -> clear attempts
    clear_login_attempts(email, request)
    # Issue JWT (new auth) and also maintain a legacy session (optional)
    jwt_token = create_access_token(user_id=user.id, email=user.email, scope=scope)
    legacy_token = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        session_token=legacy_token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(session)
    db.commit()
    return LoginResponse(access_token=jwt_token, user=UserResponse.from_orm(user))


@app.post("/v1/auth/send-otp")
async def send_otp(req: SendOtpRequest, db: Session = Depends(get_db)):
    """Issue an OTP for email signup/login and email it if SMTP is configured."""
    import random
    from datetime import timedelta

    email = req.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    # If user already exists, do not send signup OTP (guide to sign-in)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409, detail="Email already registered. Please sign in."
        )
    # Create OTP
    code = f"{random.randint(100000, 999999)}"
    expires = datetime.utcnow() + timedelta(minutes=10)
    otp = EmailOTP(email=email, code=code, expires_at=expires, consumed=False)

    db.add(otp)
    db.commit()

    # Try to send via SMTP if configured
    try:
        if os.getenv("SMTP_HOST"):
            subject = "Your WaW login code"
            text = f"Your verification code is {code}. It expires in 10 minutes."
            html = f"<p>Your verification code is <strong>{code}</strong>. It expires in 10 minutes.</p>"
            send_email(email, subject, text, html)
            return {"message": "OTP sent to email"}
    except Exception as e:
        # Don't break flow; fall back to dev mode output
        print(f"SMTP send failed: {e}")

    # Fallback for development when SMTP isn't set up
    if os.getenv("DEBUG_OTP", "true").lower() in ("1", "true", "yes"):
        return {"message": "OTP generated (email not configured)", "debug_code": code}
    return {"message": "OTP generated"}


@app.post("/v1/auth/login-password", response_model=LoginResponse)
async def login_password(
    login_data: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    """Password-based login. Requires user to exist and have a password set."""
    from passlib.hash import bcrypt

    email = login_data.email.strip().lower()
    try:
        check_login_rate_limit(email, request)
    except HTTPException:
        raise
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please sign up.")
    admin_emails = {
        e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    }
    if user.email.lower() in admin_emails:
        # For admin emails, override to use shared admin password only
        if login_data.password != ADMIN_SHARED_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid email or password")
    else:
        pw = db.query(UserPassword).filter(UserPassword.user_id == user.id).first()
        if not pw:
            raise HTTPException(
                status_code=400,
                detail="Password not set for this account. Use OTP or set a password.",
            )
        if not bcrypt.verify(login_data.password, pw.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    scope = "admin" if user.email.lower() in admin_emails else "user"
    clear_login_attempts(email, request)
    jwt_token = create_access_token(user_id=user.id, email=user.email, scope=scope)
    legacy_token = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        session_token=legacy_token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(session)
    db.commit()
    if os.getenv("AUTH_DEBUG"):
        logger.info(
            "AUTH_DEBUG: login-password issued session user_id=%s legacy_prefix=%s",
            user.id,
            legacy_token[:12],
        )
    return LoginResponse(access_token=jwt_token, user=UserResponse.from_orm(user))


@app.post("/v1/auth/set-password")
async def set_password(
    req: SetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or update the password for the authenticated user (after OTP or Google)."""
    from passlib.hash import bcrypt

    password = req.password.strip()
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters long"
        )

    existing = (
        db.query(UserPassword).filter(UserPassword.user_id == current_user.id).first()
    )
    hashed = bcrypt.hash(password)
    if existing:
        existing.password_hash = hashed
    else:
        db.add(UserPassword(user_id=current_user.id, password_hash=hashed))
    db.commit()
    return {"message": "Password set successfully"}


@app.post("/v1/auth/verify-otp", response_model=LoginResponse)
async def verify_otp(req: VerifyOtpRequest, db: Session = Depends(get_db)):
    """Verify OTP and create user if new; optionally set password in same step."""
    from passlib.hash import bcrypt

    email = req.email.strip().lower()
    rec = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.code == req.code,
            EmailOTP.consumed == False,
            EmailOTP.expires_at > datetime.utcnow(),
        )
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    rec.consumed = True
    # Ensure user exists
    user = db.query(User).filter(User.email == email).first()
    created_new = False
    if not user:
        user = User(email=email, name=email.split("@")[0], consent=True)
        db.add(user)
        db.flush()
        created_new = True

    # If password provided, set it (only if user has no password yet)
    if req.password:
        pw_text = req.password.strip()
        if len(pw_text) < 8:
            raise HTTPException(
                status_code=400, detail="Password must be at least 8 characters long"
            )
        existing_pw = (
            db.query(UserPassword).filter(UserPassword.user_id == user.id).first()
        )
        if existing_pw and not created_new:
            # Avoid silently overwriting an existing password via OTP reuse
            raise HTTPException(
                status_code=400,
                detail="Password already set. Use password login or reset flow.",
            )
        hashed = bcrypt.hash(pw_text)
        if existing_pw:
            existing_pw.password_hash = hashed
        else:
            db.add(UserPassword(user_id=user.id, password_hash=hashed))

    # Issue token
    admin_emails = {
        e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    }
    scope = "admin" if user.email.lower() in admin_emails else "user"
    token = create_access_token(user_id=user.id, email=user.email, scope=scope)
    db.commit()
    return LoginResponse(access_token=token, user=UserResponse.from_orm(user))


@app.post("/v1/auth/google", response_model=LoginResponse)
async def google_login(google_req: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Login with Google ID token (desktop app obtains id_token with Installed App flow)."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500, detail="Google auth not configured on server"
        )
    try:
        idinfo = google_id_token.verify_oauth2_token(
            google_req.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        if os.getenv("GOOGLE_LOG_IDINFO"):
            # Log non-sensitive summary (avoid dumping full token or full picture claims)
            safe_keys = {
                k: idinfo.get(k)
                for k in ["aud", "iss", "sub", "email", "email_verified", "exp", "iat"]
                if k in idinfo
            }
            logger.info("Google ID token verified: %s", safe_keys)
        email = idinfo.get("email")
        name = idinfo.get("name") or (email.split("@")[0] if email else "User")
        if not email:
            raise ValueError("No email in Google token")
        # Audience mismatch explicit check for clearer error
        if idinfo.get("aud") != GOOGLE_CLIENT_ID:
            raise ValueError(f"Token audience mismatch (aud={idinfo.get('aud')})")
    except Exception as e:
        logger.warning(
            "Google login failed: %s | client_id=%s token_prefix=%s",
            e,
            GOOGLE_CLIENT_ID,
            (google_req.id_token or "")[:12],
        )
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {e}")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name, consent=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    admin_emails = {
        e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    }
    scope = "admin" if user.email.lower() in admin_emails else "user"
    jwt_token = create_access_token(user_id=user.id, email=user.email, scope=scope)
    return LoginResponse(access_token=jwt_token, user=UserResponse.from_orm(user))


# --- Password reset (OTP-based) ---
@app.post("/v1/auth/request-password-reset")
async def request_password_reset(
    req: PasswordResetRequest, db: Session = Depends(get_db)
):
    """Issue an OTP for password reset (even if user already exists).

    Returns generic message to avoid user enumeration. In dev (DEBUG_OTP) returns debug_code.
    """
    import random

    email = req.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    user = db.query(User).filter(User.email == email).first()
    # Always act as if success; only generate OTP if user exists
    debug_code = None
    if user:
        from datetime import timedelta

        code = f"{random.randint(100000, 999999)}"
        expires = datetime.utcnow() + timedelta(minutes=10)
        otp = EmailOTP(email=email, code=code, expires_at=expires, consumed=False)
        db.add(otp)
        db.commit()
        try:
            if os.getenv("SMTP_HOST"):
                subject = "Your WaW password reset code"
                text = f"Your password reset code is {code}. It expires in 10 minutes."
                html = f"<p>Your password reset code is <strong>{code}</strong>. It expires in 10 minutes.</p>"
                send_email(email, subject, text, html)
            else:
                if os.getenv("DEBUG_OTP", "true").lower() in ("1", "true", "yes"):
                    debug_code = code
        except Exception as e:
            logger.warning("Password reset email send failed: %s", e)
            if os.getenv("DEBUG_OTP", "true").lower() in ("1", "true", "yes"):
                debug_code = code
    resp = {"message": "If the email exists, a reset code was sent"}
    if debug_code:
        resp["debug_code"] = debug_code
    return resp


@app.post("/v1/auth/confirm-password-reset")
async def confirm_password_reset(
    req: PasswordResetConfirm, db: Session = Depends(get_db)
):
    """Confirm password reset with OTP and set new password."""
    from passlib.hash import bcrypt

    email = req.email.strip().lower()
    if len(req.new_password.strip()) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters long"
        )
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Generic error (avoid enumeration) but keep 400 to signal client
        raise HTTPException(status_code=400, detail="Invalid code or email")
    rec = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.code == req.code,
            EmailOTP.consumed == False,
            EmailOTP.expires_at > datetime.utcnow(),
        )
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    rec.consumed = True
    # Upsert password
    existing_pw = db.query(UserPassword).filter(UserPassword.user_id == user.id).first()
    hashed = bcrypt.hash(req.new_password.strip())
    if existing_pw:
        existing_pw.password_hash = hashed
    else:
        db.add(UserPassword(user_id=user.id, password_hash=hashed))
    db.commit()
    return {"message": "Password reset successful"}


@app.get("/v1/auth/google/status")
async def google_auth_status():
    """Diagnostic endpoint to verify server-side Google auth readiness."""
    return {
        "configured": bool(GOOGLE_CLIENT_ID),
        "client_id_present": bool(GOOGLE_CLIENT_ID),
        "secret_present": bool(GOOGLE_CLIENT_SECRET),
        "audience": GOOGLE_CLIENT_ID,
    }


@app.get("/v1/me", response_model=UserResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse.from_orm(current_user)


@app.post("/v1/sessions")
async def upload_tracking_sessions(
    batch: BatchTrackingSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upsert tracking session summaries (one row per session)."""
    if not current_user.consent:
        raise HTTPException(status_code=403, detail="User consent required")

    created = 0
    updated = 0
    for s in batch.sessions:
        existing = (
            db.query(TrackingSession)
            .filter(
                TrackingSession.user_id == current_user.id,
                TrackingSession.device_id == s.device_id,
                TrackingSession.client_session_id == s.client_session_id,
            )
            .first()
        )
        if existing:
            existing.started_at_utc = s.started_at_utc
            existing.ended_at_utc = s.ended_at_utc
            existing.total_blinks = s.total_blinks
            existing.app_version = s.app_version
            existing.avg_cpu_percent = s.avg_cpu_percent
            existing.avg_memory_mb = s.avg_memory_mb
            existing.energy_impact = s.energy_impact
            existing.sync_status = "synced"
            updated += 1
        else:
            row = TrackingSession(
                user_id=current_user.id,
                client_session_id=s.client_session_id,
                started_at_utc=s.started_at_utc,
                ended_at_utc=s.ended_at_utc,
                total_blinks=s.total_blinks,
                device_id=s.device_id,
                app_version=s.app_version,
                avg_cpu_percent=s.avg_cpu_percent,
                avg_memory_mb=s.avg_memory_mb,
                energy_impact=s.energy_impact,
                sync_status="synced",
            )
            db.add(row)
            created += 1
    db.commit()
    return {
        "message": "Processed tracking sessions",
        "created": created,
        "updated": updated,
    }


@app.get("/v1/sessions", response_model=List[TrackingSessionResponse])
async def get_tracking_sessions(
    limit: int = 200,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(TrackingSession)
        .filter(TrackingSession.user_id == current_user.id)
        .order_by(TrackingSession.ended_at_utc.desc())
        .limit(limit)
        .all()
    )
    return [TrackingSessionResponse.from_orm(r) for r in rows]


@app.get("/v1/sessions/summary")
async def get_session_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from sqlalchemy import func

    q = db.query(TrackingSession).filter(TrackingSession.user_id == current_user.id)
    agg = q.with_entities(
        func.sum(TrackingSession.total_blinks).label("total_blinks"),
        func.count(TrackingSession.id).label("session_count"),
        func.avg(TrackingSession.avg_cpu_percent).label("avg_cpu"),
        func.avg(TrackingSession.avg_memory_mb).label("avg_memory"),
    ).first()
    return {
        "total_blinks": agg.total_blinks or 0,
        "total_sessions": agg.session_count or 0,
        "average_cpu_percent": round(agg.avg_cpu or 0, 2),
        "average_memory_mb": round(agg.avg_memory or 0, 2),
    }


@app.post("/v1/blinks")
async def upload_blink_samples(
    batch_data: BatchBlinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Batch upload blink samples - handles offline sync"""

    if not current_user.consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User consent required for data collection",
        )

    created_samples = []

    for sample_data in batch_data.samples:
        # Check for duplicate client_sequence to handle retry scenarios
        existing_sample = (
            db.query(BlinkSample)
            .filter(
                BlinkSample.user_id == current_user.id,
                BlinkSample.client_sequence == sample_data.client_sequence,
                BlinkSample.device_id == sample_data.device_id,
            )
            .first()
        )

        if existing_sample:
            # Update sync status if needed
            existing_sample.sync_status = "synced"
            continue

        # Create new blink sample
        blink_sample = BlinkSample(
            user_id=current_user.id, **sample_data.dict(), sync_status="synced"
        )

        db.add(blink_sample)
        created_samples.append(blink_sample)

    db.commit()

    return {
        "message": f"Successfully processed {len(batch_data.samples)} samples",
        "created": len(created_samples),
        "duplicates": len(batch_data.samples) - len(created_samples),
    }


@app.get("/v1/blinks", response_model=List[BlinkSampleResponse])
async def get_blink_samples(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 1000,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
):
    """Get aggregated blink statistics for dashboard"""
    from sqlalchemy import func

    # Blink sample aggregation
    sample_q = db.query(BlinkSample).filter(BlinkSample.user_id == current_user.id)
    if start_date:
        sample_q = sample_q.filter(BlinkSample.captured_at_utc >= start_date)
    if end_date:
        sample_q = sample_q.filter(BlinkSample.captured_at_utc <= end_date)
    sample_summary = sample_q.with_entities(
        func.sum(BlinkSample.blink_count).label("total_blinks"),
        func.avg(BlinkSample.blink_count).label("avg_blinks"),
        func.count(BlinkSample.id).label("sample_count"),
        func.avg(BlinkSample.cpu_percent).label("avg_cpu"),
        func.avg(BlinkSample.memory_mb).label("avg_memory"),
    ).first()

    # Tracking session aggregation (fallback / supplemental)
    session_q = db.query(TrackingSession).filter(
        TrackingSession.user_id == current_user.id
    )
    if start_date:
        session_q = session_q.filter(TrackingSession.started_at_utc >= start_date)
    if end_date:
        session_q = session_q.filter(TrackingSession.ended_at_utc <= end_date)
    session_summary = session_q.with_entities(
        func.sum(TrackingSession.total_blinks).label("total_blinks"),
        func.count(TrackingSession.id).label("session_count"),
        func.avg(TrackingSession.avg_cpu_percent).label("avg_cpu"),
        func.avg(TrackingSession.avg_memory_mb).label("avg_memory"),
    ).first()

    # Determine which data to use
    total_blinks = (
        (sample_summary.total_blinks or 0) or (session_summary.total_blinks or 0) or 0
    )
    sample_count = sample_summary.sample_count or 0
    session_count = session_summary.session_count or 0

    if sample_count > 0:
        avg_per_sample = round(sample_summary.avg_blinks or 0, 2)
        avg_cpu = round(sample_summary.avg_cpu or 0, 2)
        avg_mem = round(sample_summary.avg_memory or 0, 2)
    else:
        # Fallback to sessions if no blink samples
        if session_count > 0:
            avg_per_sample = round(
                (session_summary.total_blinks or 0) / session_count, 2
            )
        else:
            avg_per_sample = 0
        avg_cpu = round(session_summary.avg_cpu or 0, 2)
        avg_mem = round(session_summary.avg_memory or 0, 2)

    return {
        "source": "blink_samples" if sample_count > 0 else "tracking_sessions",
        "total_blinks": total_blinks,
        "average_blinks_per_sample": avg_per_sample,
        "total_samples": sample_count if sample_count > 0 else session_count,
        "average_cpu_percent": avg_cpu,
        "average_memory_mb": avg_mem,
        "period": {"start_date": start_date, "end_date": end_date},
    }


# --- Admin endpoints (simple API key auth via X-Admin-Key header) ---
def require_admin(
    x_admin_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    """Allow admin via either X-Admin-Key header or an admin-scoped Bearer token."""
    admin_key = os.getenv("ADMIN_API_KEY")
    # API key path
    if admin_key and x_admin_key == admin_key:
        return True
    # Admin JWT path
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split()[1]
        payload = decode_access_token(token)
        if payload and payload.get("scope") == "admin":
            return True
    raise HTTPException(status_code=401, detail="Admin credentials required")


@app.get("/admin/users")
async def admin_list_users(
    q: Optional[str] = None,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        ql = f"%{q.lower()}%"
        from sqlalchemy import func as safunc
        from sqlalchemy import or_

        # Match by id if q is numeric, else name/email search
        if q.isdigit():
            query = query.filter(
                or_(
                    User.id == int(q),
                    safunc.lower(User.email).like(ql),
                    safunc.lower(User.name).like(ql),
                )
            )
        else:
            query = query.filter(
                or_(safunc.lower(User.email).like(ql), safunc.lower(User.name).like(ql))
            )
    users = query.order_by(User.created_at.desc()).all()
    return [UserResponse.from_orm(u) for u in users]


@app.get("/admin/sessions")
async def admin_list_sessions(
    limit: int = 500, _: None = Depends(require_admin), db: Session = Depends(get_db)
):
    rows = (
        db.query(TrackingSession)
        .order_by(TrackingSession.ended_at_utc.desc())
        .limit(limit)
        .all()
    )
    return [TrackingSessionResponse.from_orm(r) for r in rows]


# Admin: blink samples for a user (with optional date range)
@app.get("/admin/users/{user_id}/blinks")
async def admin_get_user_blinks(
    user_id: int,
    limit: int = 500,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(BlinkSample).filter(BlinkSample.user_id == user_id)
    if start_date:
        query = query.filter(BlinkSample.captured_at_utc >= start_date)
    if end_date:
        query = query.filter(BlinkSample.captured_at_utc <= end_date)
    samples = (
        query.order_by(BlinkSample.captured_at_utc.desc()).limit(min(limit, 2000)).all()
    )
    return [BlinkSampleResponse.from_orm(s) for s in samples]


# Admin: blink summary for a user (reuses aggregation similar to /v1/blinks/summary)
@app.get("/admin/users/{user_id}/blinks/summary")
async def admin_get_user_blink_summary(
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func

    # Blink samples aggregation
    sample_q = db.query(BlinkSample).filter(BlinkSample.user_id == user_id)
    if start_date:
        sample_q = sample_q.filter(BlinkSample.captured_at_utc >= start_date)
    if end_date:
        sample_q = sample_q.filter(BlinkSample.captured_at_utc <= end_date)
    sample_summary = sample_q.with_entities(
        func.sum(BlinkSample.blink_count).label("total_blinks"),
        func.avg(BlinkSample.blink_count).label("avg_blinks"),
        func.count(BlinkSample.id).label("sample_count"),
        func.avg(BlinkSample.cpu_percent).label("avg_cpu"),
        func.avg(BlinkSample.memory_mb).label("avg_memory"),
    ).first()

    # Tracking sessions aggregation
    session_q = db.query(TrackingSession).filter(TrackingSession.user_id == user_id)
    if start_date:
        session_q = session_q.filter(TrackingSession.started_at_utc >= start_date)
    if end_date:
        session_q = session_q.filter(TrackingSession.ended_at_utc <= end_date)
    session_summary = session_q.with_entities(
        func.sum(TrackingSession.total_blinks).label("total_blinks"),
        func.count(TrackingSession.id).label("session_count"),
        func.avg(TrackingSession.avg_cpu_percent).label("avg_cpu"),
        func.avg(TrackingSession.avg_memory_mb).label("avg_memory"),
    ).first()

    total_blinks = (
        (sample_summary.total_blinks or 0) or (session_summary.total_blinks or 0) or 0
    )
    sample_count = sample_summary.sample_count or 0
    session_count = session_summary.session_count or 0

    if sample_count > 0:
        avg_per_sample = round(sample_summary.avg_blinks or 0, 2)
        avg_cpu = round(sample_summary.avg_cpu or 0, 2)
        avg_mem = round(sample_summary.avg_memory or 0, 2)
    else:
        if session_count > 0:
            avg_per_sample = round(
                (session_summary.total_blinks or 0) / session_count, 2
            )
        else:
            avg_per_sample = 0
        avg_cpu = round(session_summary.avg_cpu or 0, 2)
        avg_mem = round(session_summary.avg_memory or 0, 2)

    return {
        "user_id": user_id,
        "source": "blink_samples" if sample_count > 0 else "tracking_sessions",
        "total_blinks": total_blinks,
        "average_blinks_per_sample": avg_per_sample,
        "total_samples": sample_count if sample_count > 0 else session_count,
        "average_cpu_percent": avg_cpu,
        "average_memory_mb": avg_mem,
        "period": {"start_date": start_date, "end_date": end_date},
    }


# New: Admin - get specific user and that user's sessions
@app.get("/admin/users/{user_id}")
async def admin_get_user(
    user_id: int, _: None = Depends(require_admin), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)


@app.get("/admin/users/{user_id}/sessions")
async def admin_get_user_sessions(
    user_id: int,
    limit: int = 200,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(TrackingSession)
        .filter(TrackingSession.user_id == user_id)
        .order_by(TrackingSession.ended_at_utc.desc())
        .limit(limit)
        .all()
    )
    return [TrackingSessionResponse.from_orm(r) for r in rows]


@app.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int, _: None = Depends(require_admin), db: Session = Depends(get_db)
):
    """Delete a user and all associated data (blink samples, sessions, passwords, OTPs)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Prevent accidental deletion of admin (unless explicitly allowed)
    admin_emails = {
        e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    }
    if user.email.lower() in admin_emails and os.getenv(
        "ALLOW_ADMIN_ACCOUNT_DELETION", "false"
    ).lower() not in ("1", "true", "yes"):
        raise HTTPException(
            status_code=400,
            detail="Deletion of admin account blocked (set ALLOW_ADMIN_ACCOUNT_DELETION=true to override)",
        )
    email = user.email
    blink_deleted = (
        db.query(BlinkSample).filter(BlinkSample.user_id == user_id).delete()
    )
    sess_deleted = (
        db.query(TrackingSession).filter(TrackingSession.user_id == user_id).delete()
    )
    usess_deleted = (
        db.query(UserSession).filter(UserSession.user_id == user_id).delete()
    )
    pwd_deleted = (
        db.query(UserPassword).filter(UserPassword.user_id == user_id).delete()
    )
    otp_deleted = db.query(EmailOTP).filter(EmailOTP.email == email).delete()
    db.delete(user)
    db.commit()
    return {
        "message": "User deleted",
        "user_id": user_id,
        "email": email,
        "deleted": {
            "blink_samples": blink_deleted,
            "tracking_sessions": sess_deleted,
            "user_sessions": usess_deleted,
            "password_rows": pwd_deleted,
            "otp_rows": otp_deleted,
        },
    }


@app.delete("/admin/users/by-email")
async def admin_delete_user_by_email(
    email: str, _: None = Depends(require_admin), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await admin_delete_user(user.id, db=db)  # reuse logic


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))


@app.delete("/v1/me")
async def delete_me(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Allow an authenticated user to delete their own account and associated data."""
    # Block self-deletion for admin unless override flag set
    admin_emails = {
        e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    }
    if current_user.email.lower() in admin_emails and os.getenv(
        "ALLOW_ADMIN_ACCOUNT_DELETION", "false"
    ).lower() not in ("1", "true", "yes"):
        raise HTTPException(
            status_code=400,
            detail="Admin accounts cannot self-delete (set ALLOW_ADMIN_ACCOUNT_DELETION=true to override)",
        )
    uid = current_user.id
    email = current_user.email
    db.query(BlinkSample).filter(BlinkSample.user_id == uid).delete()
    db.query(TrackingSession).filter(TrackingSession.user_id == uid).delete()
    db.query(UserSession).filter(UserSession.user_id == uid).delete()
    db.query(UserPassword).filter(UserPassword.user_id == uid).delete()
    db.query(EmailOTP).filter(EmailOTP.email == email).delete()
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted", "user_id": uid, "email": email}


# Mount static web dashboard at /dashboard (Next.js static export)
try:
    root_dir = Path(__file__).resolve().parents[1]
    next_export_dir = root_dir / "dashboard" / "out"
    if next_export_dir.exists():
        app.mount(
            "/dashboard",
            StaticFiles(directory=str(next_export_dir), html=True),
            name="dashboard",
        )
except Exception:
    # Non-fatal if mounting fails
    pass

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
