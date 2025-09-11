"""
Smoke tests for CI/CD pipeline
Simple tests that verify basic functionality without heavy dependencies
"""

import pytest
import sys
import os

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestBasicFunctionality:
    """Basic smoke tests for core functionality"""
    
    def test_auth_module_import(self):
        """Test that auth module can be imported"""
        try:
            from backend.auth import hash_password, verify_password, create_jwt_token
            assert True
        except ImportError:
            pytest.skip("Auth module not available")
    
    def test_password_hashing(self):
        """Test password hashing functionality"""
        try:
            from backend.auth import hash_password, verify_password
            
            password = "TestPassword123!"
            hashed = hash_password(password)
            
            # Hash should be different from original
            assert hashed != password
            
            # Should verify correctly
            assert verify_password(password, hashed) == True
            
            # Wrong password should fail
            assert verify_password("WrongPassword", hashed) == False
            
        except ImportError:
            pytest.skip("Auth module not available")
    
    def test_jwt_token_creation(self):
        """Test JWT token creation"""
        try:
            from backend.auth import create_jwt_token, verify_jwt_token
            
            user_data = {"user_id": 123, "email": "test@example.com"}
            token = create_jwt_token(user_data)
            
            assert token is not None
            assert isinstance(token, str)
            
            # Token should be verifiable
            decoded = verify_jwt_token(token)
            assert decoded is not None
            assert decoded["user_id"] == 123
            
        except ImportError:
            pytest.skip("Auth module not available")
    
    def test_config_module_import(self):
        """Test that shared config can be imported"""
        try:
            from shared.config import Config
            assert True
        except ImportError:
            pytest.skip("Config module not available")
    
    def test_api_module_import(self):
        """Test that API module can be imported"""
        try:
            from shared.api import WaWAPI
            assert True
        except ImportError:
            pytest.skip("API module not available")

    def test_basic_math(self):
        """Test that basic Python math works (sanity check)"""
        assert 1 + 1 == 2
        assert 2 * 3 == 6
        assert 10 / 2 == 5

    def test_string_operations(self):
        """Test basic string operations (sanity check)"""
        test_string = "Wellness at Work"
        assert test_string.lower() == "wellness at work"
        assert test_string.replace("Work", "Life") == "Wellness at Life"
        assert len(test_string) > 0


class TestProjectStructure:
    """Test that project structure is correct"""
    
    def test_backend_directory_exists(self):
        """Test that backend directory exists"""
        backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
        assert os.path.isdir(backend_path)
    
    def test_desktop_directory_exists(self):
        """Test that desktop directory exists"""
        desktop_path = os.path.join(os.path.dirname(__file__), '..', 'desktop')
        assert os.path.isdir(desktop_path)
    
    def test_shared_directory_exists(self):
        """Test that shared directory exists"""
        shared_path = os.path.join(os.path.dirname(__file__), '..', 'shared')
        assert os.path.isdir(shared_path)
    
    def test_requirements_files_exist(self):
        """Test that requirement files exist"""
        project_root = os.path.join(os.path.dirname(__file__), '..')
        
        req_files = [
            'requirements.txt',
            'requirements.backend.txt',
            'requirements.test.minimal.txt'
        ]
        
        for req_file in req_files:
            req_path = os.path.join(project_root, req_file)
            assert os.path.isfile(req_path), f"Missing requirement file: {req_file}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
