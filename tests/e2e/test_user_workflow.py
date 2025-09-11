"""
End-to-End User Workflow Testing

Tests complete user journeys from registration to data visualization.
"""

import pytest
import time
import os
import sys
from unittest.mock import Mock, patch

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from shared.api import WaWAPI
    from shared.config import Config
    HAS_MODULES = True
except ImportError:
    HAS_MODULES = False


class TestCompleteUserJourney:
    """Test the complete user experience from start to finish"""
    
    @pytest.fixture
    def test_user_credentials(self):
        """Generate unique test user credentials"""
        timestamp = int(time.time())
        return {
            "email": f"e2e_user_{timestamp}@example.com",
            "name": f"E2E Test User {timestamp}",
            "password": "SecureE2EPassword123!"
        }
    
    @pytest.fixture
    def api_client(self):
        """Create API client for E2E testing"""
        if not HAS_MODULES:
            pytest.skip("Required modules not available")
        
        config = Mock()
        config.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        config.device_id = f'e2e-test-device-{int(time.time())}'
        config.app_version = '1.0.0-e2e'
        return WaWAPI(config)
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_new_user_onboarding_journey(self, api_client, test_user_credentials):
        """Test complete new user onboarding process"""
        
        # Step 1: New user registration
        print(f"🧪 Testing registration for: {test_user_credentials['email']}")
        
        try:
            register_result = api_client.register(
                test_user_credentials["email"],
                test_user_credentials["name"],
                test_user_credentials["password"]
            )
            assert register_result is not None, "Registration failed"
            print("✅ User registration successful")
            
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️ User already exists, proceeding with login")
            else:
                pytest.fail(f"Registration failed unexpectedly: {e}")
        
        # Step 2: First login
        login_result = api_client.login(
            test_user_credentials["email"],
            test_user_credentials["password"]
        )
        assert login_result is not None, "Login failed"
        assert api_client.is_authed == True, "Authentication state incorrect"
        print("✅ User login successful")
        
        # Step 3: Verify profile access
        profile = api_client.get_profile()
        assert profile is not None, "Profile retrieval failed"
        assert profile["email"] == test_user_credentials["email"], "Profile email mismatch"
        print("✅ Profile access verified")
        
        # Step 4: Check initial empty state
        summary = api_client.get_session_summary()
        assert summary is not None, "Session summary retrieval failed"
        initial_sessions = summary.get("total_sessions", 0)
        initial_blinks = summary.get("total_blinks", 0)
        print(f"✅ Initial state: {initial_sessions} sessions, {initial_blinks} blinks")
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_first_tracking_session_workflow(self, api_client, test_user_credentials):
        """Test a user's first eye tracking session"""
        
        # Login first
        api_client.login(
            test_user_credentials["email"],
            test_user_credentials["password"]
        )
        
        # Simulate first tracking session
        print("🧪 Testing first tracking session")
        
        # Step 1: Start tracking session (collect blink data)
        session_data = []
        for minute in range(5):  # 5-minute session
            sample = {
                "client_sequence": minute + 1,
                "captured_at_utc": f"2025-01-01T12:{minute:02d}:00Z",
                "blink_count": 15 + (minute * 2),  # Varying blink counts
                "device_id": api_client.config.device_id,
                "app_version": api_client.config.app_version
            }
            session_data.append(sample)
        
        # Step 2: Upload session data
        upload_result = api_client.upload_blink_samples(session_data)
        assert upload_result is not None, "Data upload failed"
        assert upload_result.get("uploaded", 0) == 5, "Not all samples uploaded"
        print("✅ Session data uploaded successfully")
        
        # Step 3: Verify data appears in summary
        updated_summary = api_client.get_session_summary()
        assert updated_summary is not None, "Updated summary retrieval failed"
        
        new_total_blinks = updated_summary.get("total_blinks", 0)
        assert new_total_blinks >= sum(s["blink_count"] for s in session_data), \
            "Blink count not updated correctly"
        print(f"✅ Summary updated: {new_total_blinks} total blinks")
        
        # Step 4: Check session history
        sessions = api_client.get_sessions()
        assert sessions is not None, "Session history retrieval failed"
        print(f"✅ Session history retrieved: {len(sessions)} sessions")
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_multiple_sessions_over_time(self, api_client, test_user_credentials):
        """Test user with multiple tracking sessions over time"""
        
        # Login
        api_client.login(
            test_user_credentials["email"],
            test_user_credentials["password"]
        )
        
        print("🧪 Testing multiple sessions workflow")
        
        # Simulate 3 different tracking sessions
        all_sessions_data = []
        
        for session_num in range(3):
            session_data = []
            base_hour = 10 + session_num  # Different times
            
            for minute in range(3):  # 3-minute sessions
                sample = {
                    "client_sequence": (session_num * 10) + minute + 1,
                    "captured_at_utc": f"2025-01-0{session_num + 1}T{base_hour}:{minute:02d}:00Z",
                    "blink_count": 10 + (session_num * 5) + minute,
                    "device_id": api_client.config.device_id,
                    "app_version": api_client.config.app_version
                }
                session_data.append(sample)
            
            # Upload each session
            upload_result = api_client.upload_blink_samples(session_data)
            assert upload_result is not None, f"Session {session_num + 1} upload failed"
            all_sessions_data.extend(session_data)
            
            print(f"✅ Session {session_num + 1} uploaded")
        
        # Verify all data is reflected in summary
        final_summary = api_client.get_session_summary()
        expected_total_blinks = sum(s["blink_count"] for s in all_sessions_data)
        actual_total_blinks = final_summary.get("total_blinks", 0)
        
        assert actual_total_blinks >= expected_total_blinks, \
            f"Expected at least {expected_total_blinks} blinks, got {actual_total_blinks}"
        
        print(f"✅ All sessions processed: {actual_total_blinks} total blinks")
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_user_data_retrieval_and_analysis(self, api_client, test_user_credentials):
        """Test user accessing and analyzing their data"""
        
        # Login
        api_client.login(
            test_user_credentials["email"],
            test_user_credentials["password"]
        )
        
        print("🧪 Testing data retrieval and analysis")
        
        # Step 1: Get comprehensive session summary
        summary = api_client.get_session_summary()
        assert summary is not None, "Summary retrieval failed"
        
        required_fields = ["total_sessions", "total_blinks", "avg_cpu_percent", "avg_memory_mb"]
        for field in required_fields:
            assert field in summary, f"Missing summary field: {field}"
        
        print("✅ Session summary contains all required fields")
        
        # Step 2: Get detailed session history
        sessions = api_client.get_sessions()
        assert sessions is not None, "Sessions retrieval failed"
        
        if len(sessions) > 0:
            # Verify session structure
            first_session = sessions[0]
            session_fields = ["id", "start_time", "end_time", "total_blinks"]
            for field in session_fields:
                assert field in first_session, f"Missing session field: {field}"
            
            print(f"✅ Session history verified: {len(sessions)} sessions")
        
        # Step 3: Test data filtering (if supported)
        try:
            # Get blink samples with date filtering
            recent_blinks = api_client.get_blink_samples(days=7)
            if recent_blinks is not None:
                print(f"✅ Filtered blink data retrieved: {len(recent_blinks)} samples")
        except Exception:
            print("ℹ️ Filtered blink retrieval not available")


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error scenarios in user workflows"""
    
    @pytest.fixture
    def api_client(self):
        """API client for edge case testing"""
        if not HAS_MODULES:
            pytest.skip("Required modules not available")
        
        config = Mock()
        config.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        config.device_id = 'edge-case-device'
        config.app_version = '1.0.0-test'
        return WaWAPI(config)
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_duplicate_registration_handling(self, api_client):
        """Test system response to duplicate user registration"""
        
        test_email = f"duplicate_test_{int(time.time())}@example.com"
        user_data = {
            "email": test_email,
            "name": "Duplicate Test User",
            "password": "TestPassword123!"
        }
        
        # First registration should succeed
        try:
            first_result = api_client.register(
                user_data["email"],
                user_data["name"],
                user_data["password"]
            )
            print("✅ First registration successful")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️ User already exists from previous test")
            else:
                pytest.fail(f"First registration failed: {e}")
        
        # Second registration should be handled gracefully
        try:
            second_result = api_client.register(
                user_data["email"],
                user_data["name"],
                user_data["password"]
            )
            # Should either succeed (idempotent) or fail gracefully
            print("ℹ️ Duplicate registration handled")
        except Exception as e:
            assert "already exists" in str(e).lower() or "duplicate" in str(e).lower(), \
                f"Unexpected error for duplicate registration: {e}"
            print("✅ Duplicate registration properly rejected")
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_invalid_login_attempts(self, api_client):
        """Test system response to invalid login attempts"""
        
        # Test with non-existent user
        result1 = api_client.login("nonexistent@example.com", "password")
        assert result1 is None or "error" in str(result1).lower(), \
            "Should reject non-existent user"
        print("✅ Non-existent user login properly rejected")
        
        # Test with wrong password (for existing user)
        test_email = f"wrong_password_test_{int(time.time())}@example.com"
        try:
            api_client.register(test_email, "Test User", "CorrectPassword123!")
        except:
            pass
        
        result2 = api_client.login(test_email, "WrongPassword123!")
        assert result2 is None or "error" in str(result2).lower(), \
            "Should reject wrong password"
        print("✅ Wrong password login properly rejected")
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_empty_data_upload(self, api_client):
        """Test uploading empty or invalid data"""
        
        # Login first
        test_email = f"empty_data_test_{int(time.time())}@example.com"
        try:
            api_client.register(test_email, "Empty Data Test", "TestPassword123!")
        except:
            pass
        api_client.login(test_email, "TestPassword123!")
        
        # Test empty data upload
        try:
            result1 = api_client.upload_blink_samples([])
            # Should handle empty data gracefully
            print("✅ Empty data upload handled gracefully")
        except Exception as e:
            print(f"ℹ️ Empty data upload error (acceptable): {e}")
        
        # Test invalid data structure
        try:
            invalid_data = [{"invalid": "structure"}]
            result2 = api_client.upload_blink_samples(invalid_data)
            print("⚠️ Invalid data was accepted (might need validation)")
        except Exception as e:
            print("✅ Invalid data properly rejected")


class TestDataConsistencyAndIntegrity:
    """Test data consistency across the entire system"""
    
    @pytest.mark.skipif(not HAS_MODULES, reason="Required modules not available")
    def test_data_persistence_across_sessions(self):
        """Test that user data persists across login sessions"""
        
        config = Mock()
        config.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        config.device_id = 'persistence-test-device'
        config.app_version = '1.0.0-test'
        
        api_client1 = WaWAPI(config)
        
        test_email = f"persistence_test_{int(time.time())}@example.com"
        test_password = "PersistenceTest123!"
        
        # Session 1: Register and upload data
        try:
            api_client1.register(test_email, "Persistence Test", test_password)
        except:
            pass
        
        api_client1.login(test_email, test_password)
        
        # Upload test data
        test_data = [{
            "client_sequence": 1,
            "captured_at_utc": "2025-01-01T12:00:00Z",
            "blink_count": 42,  # Unique number for verification
            "device_id": "persistence-test-device",
            "app_version": "1.0.0-test"
        }]
        
        upload_result = api_client1.upload_blink_samples(test_data)
        assert upload_result is not None, "Data upload failed"
        
        # Get initial summary
        summary1 = api_client1.get_session_summary()
        initial_blinks = summary1.get("total_blinks", 0)
        
        # Session 2: New API client instance (simulating app restart)
        api_client2 = WaWAPI(config)
        api_client2.login(test_email, test_password)
        
        # Verify data persists
        summary2 = api_client2.get_session_summary()
        persistent_blinks = summary2.get("total_blinks", 0)
        
        assert persistent_blinks >= initial_blinks, \
            "Data did not persist across sessions"
        
        print(f"✅ Data persistence verified: {persistent_blinks} blinks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
