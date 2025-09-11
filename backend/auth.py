# Authentication module for Wellness at Work backend
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "wellness_at_work_secret_key_2024")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_data: Dict[str, Any]) -> str:
    """Create a JWT token for a user"""
    payload = {
        **user_data,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def create_user(email: str, name: str, password: str) -> Dict[str, Any]:
    """Create a new user (placeholder implementation)"""
    return {
        "id": 1,
        "email": email,
        "name": name,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow().isoformat()
    }
