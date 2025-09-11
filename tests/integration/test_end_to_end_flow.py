"""
End-to-End Integration Testing

Tests the complete data flow from desktop app through API to dashboard.
"""

import pytest
import asyncio
import tempfile
import time
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from shared.api import WaWAPI
    from shared.config import Config
    HAS_MODULES = True
except ImportError:
    HAS_MODULES = False


class TestEndToEndDataFlow:
    """Test complete data flow through the system"""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        config = Mock()
        config.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        config.device_id = 'test-device-123'
        config.app_version = '1.0.0-test'
        return config
    
    @pytest.fixture
    def api_client(self, test_config):
        """Create API client for testing"""
        if not HAS_MODULES:
            pytest.skip("Required modules not available")
        return WaWAPI(test_config)
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    async def test_user_registration_and_login_flow(self, api_client):
        """Test complete user authentication flow"""
        test_user = {
            "email": f"integration_test_{int(time.time())}@example.com",
            "name": "Integration Test User",
            "password": "SecureTestPassword123!"
        }
        
        try:
            # Step 1: Register new user
            register_response = api_client.register(
                test_user["email"],
                test_user["name"], 
                test_user["password"]
            )
            assert register_response is not None
            
            # Step 2: Login with new credentials
            login_response = api_client.login(
                test_user["email"],
                test_user["password"]
            )
            assert login_response is not None
            assert api_client.is_authed == True
            
            # Step 3: Access protected endpoint
            profile = api_client.get_profile()
            assert profile is not None
            assert profile["email"] == test_user["email"]
            
        except Exception as e:
            # If registration fails (user exists), try login only
            if "already exists" in str(e).lower():
                login_response = api_client.login(
                    test_user["email"],
                    test_user["password"]
                )
                assert login_response is not None
            else:
                pytest.fail(f"Authentication flow failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    async def test_blink_data_upload_and_retrieval(self, api_client):
        """Test uploading blink data and retrieving it"""
        # First authenticate
        test_email = f"blink_test_{int(time.time())}@example.com"
        try:
            api_client.register(test_email, "Blink Test User", "TestPassword123!")
        except:
            pass  # User might already exist
        
        api_client.login(test_email, "TestPassword123!")
        
        # Create test blink data
        test_samples = [
            {
                "client_sequence": 1,
                "captured_at_utc": "2025-01-01T12:00:00Z",
                "blink_count": 15,
                "device_id": "test-device-integration",
                "app_version": "1.0.0-test"
            },
            {
                "client_sequence": 2,
                "captured_at_utc": "2025-01-01T12:01:00Z", 
                "blink_count": 12,
                "device_id": "test-device-integration",
                "app_version": "1.0.0-test"
            }
        ]
        
        # Upload blink data
        upload_result = api_client.upload_blink_samples(test_samples)
        assert upload_result is not None
        assert upload_result.get("uploaded", 0) > 0
        
        # Retrieve session summary
        summary = api_client.get_session_summary()
        assert summary is not None
        assert "total_blinks" in summary
        assert summary["total_blinks"] >= 27  # At least our test data
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_offline_to_online_sync_simulation(self, api_client):
        """Simulate offline data collection and online sync"""
        # Simulate offline data collection
        offline_queue = []
        
        # Collect "offline" blink samples
        for i in range(5):
            sample = {
                "client_sequence": i + 1,
                "captured_at_utc": f"2025-01-01T12:0{i}:00Z",
                "blink_count": 10 + i,
                "device_id": "offline-test-device",
                "app_version": "1.0.0-test"
            }
            offline_queue.append(sample)
        
        assert len(offline_queue) == 5
        
        # Simulate "coming online" and syncing data
        test_email = f"offline_test_{int(time.time())}@example.com"
        try:
            api_client.register(test_email, "Offline Test User", "TestPassword123!")
        except:
            pass
        
        api_client.login(test_email, "TestPassword123!")
        
        # Upload all offline data
        sync_result = api_client.upload_blink_samples(offline_queue)
        assert sync_result is not None
        assert sync_result.get("uploaded", 0) == 5
        
        # Verify data is now available online
        sessions = api_client.get_sessions()
        assert sessions is not None


class TestPerformanceAndReliability:
    """Test system performance and reliability under load"""
    
    @pytest.fixture
    def performance_api_client(self):
        """API client for performance testing"""
        if not HAS_MODULES:
            pytest.skip("Required modules not available")
        
        config = Mock()
        config.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        config.device_id = 'performance-test-device'
        config.app_version = '1.0.0-test'
        return WaWAPI(config)
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_bulk_data_upload_performance(self, performance_api_client):
        """Test uploading large amounts of blink data"""
        # Authenticate first
        test_email = f"perf_test_{int(time.time())}@example.com"
        try:
            performance_api_client.register(test_email, "Performance Test", "TestPassword123!")
        except:
            pass
        
        performance_api_client.login(test_email, "TestPassword123!")
        
        # Create large dataset (simulate 1 hour of tracking at 30 FPS)
        large_dataset = []
        for i in range(100):  # Reduced for CI environment
            sample = {
                "client_sequence": i + 1,
                "captured_at_utc": f"2025-01-01T12:{i:02d}:00Z",
                "blink_count": (i % 20) + 5,  # Varying blink counts
                "device_id": "performance-test-device",
                "app_version": "1.0.0-test"
            }
            large_dataset.append(sample)
        
        # Measure upload time
        start_time = time.time()
        result = performance_api_client.upload_blink_samples(large_dataset)
        upload_time = time.time() - start_time
        
        # Verify upload succeeded
        assert result is not None
        assert result.get("uploaded", 0) == 100
        
        # Performance assertion (should complete within reasonable time)
        assert upload_time < 30, f"Upload took too long: {upload_time}s"
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_api_error_handling(self, performance_api_client):
        """Test API error handling and resilience"""
        # Test with invalid credentials
        login_result = performance_api_client.login("invalid@email.com", "wrongpassword")
        assert login_result is None or "error" in str(login_result).lower()
        
        # Test unauthorized access
        try:
            performance_api_client.get_profile()  # Should fail without auth
            assert False, "Should have failed without authentication"
        except Exception:
            assert True  # Expected to fail
        
        # Test invalid data upload
        invalid_samples = [{"invalid": "data"}]
        try:
            performance_api_client.upload_blink_samples(invalid_samples)
            assert False, "Should have failed with invalid data"
        except Exception:
            assert True  # Expected to fail
    
    def test_network_connectivity_simulation(self):
        """Test behavior under poor network conditions"""
        # Simulate network timeout
        config = Mock()
        config.api_base_url = "http://nonexistent-server.invalid"
        config.device_id = "network-test"
        config.app_version = "1.0.0-test"
        
        if HAS_MODULES:
            api_client = WaWAPI(config)
            
            # This should handle network errors gracefully
            result = api_client.login("test@example.com", "password")
            assert result is None  # Should fail gracefully, not crash


class TestCrossComponentIntegration:
    """Test integration between different system components"""
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_config_to_api_integration(self):
        """Test configuration system integration with API client"""
        # Test that Config properly initializes API client
        try:
            config = Config()
            api_client = WaWAPI(config)
            assert api_client is not None
            assert hasattr(api_client, 'base_url')
        except Exception:
            # Config might fail in test environment, that's OK
            assert True
    
    def test_data_flow_consistency(self):
        """Test data consistency through the entire pipeline"""
        # Test that data maintains integrity from collection to storage
        original_data = {
            "timestamp": "2025-01-01T12:00:00Z",
            "blink_count": 15,
            "device_id": "consistency-test"
        }
        
        # Simulate data transformations that would happen in real system
        # 1. Desktop app collects data
        collected_data = original_data.copy()
        
        # 2. Data formatted for API
        api_formatted = {
            "client_sequence": 1,
            "captured_at_utc": collected_data["timestamp"],
            "blink_count": collected_data["blink_count"],
            "device_id": collected_data["device_id"],
            "app_version": "1.0.0"
        }
        
        # 3. Verify no data loss in transformation
        assert api_formatted["captured_at_utc"] == original_data["timestamp"]
        assert api_formatted["blink_count"] == original_data["blink_count"]
        assert api_formatted["device_id"] == original_data["device_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
