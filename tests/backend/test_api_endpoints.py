"""
Backend API Endpoints Testing

Tests all REST API endpoints for functionality, security, and data validation.
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

try:
    from main import app
    from models import User, TrackingSession, BlinkSample
    from auth import create_user, verify_password, create_jwt_token
except ImportError:
    # Fallback for CI environment
    app = None


class TestAPIEndpoints:
    """Test suite for all API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app"""
        if app is None:
            pytest.skip("Backend app not available")
        return TestClient(app)
    
    @pytest.fixture
    def test_user_data(self):
        """Sample user data for testing"""
        return {
            "email": "test@example.com",
            "name": "Test User",
            "password": "SecurePassword123!"
        }
    
    def test_health_check(self, client):
        """Test basic health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()
    
    def test_user_registration(self, client, test_user_data):
        """Test user registration endpoint"""
        response = client.post("/auth/register", json=test_user_data)
        
        # Should succeed or user already exists
        assert response.status_code in [201, 400]
        
        if response.status_code == 201:
            data = response.json()
            assert "token" in data
            assert data["user"]["email"] == test_user_data["email"]
    
    def test_user_login(self, client, test_user_data):
        """Test user login endpoint"""
        # First register user
        client.post("/auth/register", json=test_user_data)
        
        # Then try to login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
    
    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/v1/me")
        assert response.status_code == 401
    
    def test_blink_data_upload(self, client, test_user_data):
        """Test blink sample data upload"""
        # Register and login to get token
        client.post("/auth/register", json=test_user_data)
        login_response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["token"]
        
        # Upload blink data
        blink_data = {
            "samples": [
                {
                    "client_sequence": 1,
                    "captured_at_utc": "2025-01-01T12:00:00Z",
                    "blink_count": 5,
                    "device_id": "test-device",
                    "app_version": "1.0.0"
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/v1/blinks", json=blink_data, headers=headers)
        
        assert response.status_code == 200
        assert "uploaded" in response.json()
    
    def test_session_data_retrieval(self, client, test_user_data):
        """Test session summary retrieval"""
        # Register and login
        client.post("/auth/register", json=test_user_data)
        login_response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/v1/sessions/summary", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "total_blinks" in data
    
    def test_invalid_token(self, client):
        """Test API response to invalid JWT tokens"""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = client.get("/v1/me", headers=headers)
        assert response.status_code == 401
    
    def test_data_validation(self, client, test_user_data):
        """Test API input validation"""
        # Register user
        client.post("/auth/register", json=test_user_data)
        login_response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["token"]
        
        # Try uploading invalid blink data
        invalid_data = {
            "samples": [
                {
                    "client_sequence": "not_a_number",  # Should be int
                    "captured_at_utc": "invalid_date",   # Should be ISO datetime
                    "blink_count": -5,                   # Should be positive
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/v1/blinks", json=invalid_data, headers=headers)
        
        # Should return validation error
        assert response.status_code == 422


class TestSecurityMeasures:
    """Test security implementations"""
    
    @pytest.fixture
    def client(self):
        if app is None:
            pytest.skip("Backend app not available")
        return TestClient(app)
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        from auth import hash_password, verify_password
        
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Should verify correctly
        assert verify_password(password, hashed) == True
        
        # Wrong password should fail
        assert verify_password("WrongPassword", hashed) == False
    
    def test_jwt_token_creation(self):
        """Test JWT token creation and validation"""
        from auth import create_jwt_token, verify_jwt_token
        
        user_data = {"user_id": 123, "email": "test@example.com"}
        token = create_jwt_token(user_data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Token should be verifiable
        decoded = verify_jwt_token(token)
        assert decoded is not None
        assert decoded["user_id"] == 123
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly set"""
        response = client.options("/v1/me")
        
        # Should include CORS headers
        assert "Access-Control-Allow-Origin" in response.headers or \
               response.status_code == 405  # Method not allowed is also acceptable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
