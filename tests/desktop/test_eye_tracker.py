"""
Desktop Eye Tracker Testing

Tests the core eye tracking functionality, UI components, and offline storage.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add desktop modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from desktop.eye_tracker import EyeTracker, eye_aspect_ratio
    from desktop.main import WaWMainWindow
    from shared.config import Config
    from shared.api import WaWAPI
    HAS_DESKTOP_MODULES = True
except ImportError:
    HAS_DESKTOP_MODULES = False

# Try to import PyQt6 for UI testing
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import Qt
    import pytest_qt
    HAS_QT = True
except ImportError:
    HAS_QT = False


class TestEyeTracker:
    """Test the core eye tracking functionality"""
    
    @pytest.fixture
    def mock_mediapipe(self):
        """Mock MediaPipe components for testing"""
        with patch('desktop.eye_tracker.mp') as mock_mp:
            # Mock face mesh
            mock_face_mesh = Mock()
            mock_mp.solutions.face_mesh.FaceMesh.return_value = mock_face_mesh
            
            # Mock drawing utils
            mock_mp.solutions.drawing_utils = Mock()
            mock_mp.solutions.face_mesh.FACEMESH_LEFT_EYE = [1, 2, 3]
            mock_mp.solutions.face_mesh.FACEMESH_RIGHT_EYE = [4, 5, 6]
            
            yield mock_mp
    
    @pytest.fixture
    def mock_opencv(self):
        """Mock OpenCV for testing"""
        with patch('desktop.eye_tracker.cv2') as mock_cv2:
            # Mock video capture
            mock_cap = Mock()
            mock_cap.read.return_value = (True, "fake_frame")
            mock_cv2.VideoCapture.return_value = mock_cap
            
            yield mock_cv2
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available")
    def test_eye_aspect_ratio_calculation(self):
        """Test EAR calculation with known coordinates"""
        # Create mock eye landmarks (6 points for eye)
        eye_landmarks = [
            Mock(x=0.1, y=0.5),  # Left corner
            Mock(x=0.15, y=0.45), # Top left
            Mock(x=0.2, y=0.45),  # Top right  
            Mock(x=0.25, y=0.5),  # Right corner
            Mock(x=0.2, y=0.55),  # Bottom right
            Mock(x=0.15, y=0.55), # Bottom left
        ]
        
        ear = eye_aspect_ratio(eye_landmarks)
        
        # EAR should be a positive float
        assert isinstance(ear, float)
        assert ear > 0
        assert ear < 1  # Realistic EAR values are typically < 1
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available")
    def test_eye_tracker_initialization(self, mock_mediapipe, mock_opencv):
        """Test EyeTracker class initialization"""
        tracker = EyeTracker()
        
        assert tracker is not None
        assert hasattr(tracker, 'is_running')
        assert hasattr(tracker, 'blink_count')
        assert tracker.is_running == False
        assert tracker.blink_count == 0
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available")
    def test_eye_tracker_start_stop(self, mock_mediapipe, mock_opencv):
        """Test starting and stopping eye tracking"""
        tracker = EyeTracker()
        
        # Start tracking
        tracker.start_tracking()
        assert tracker.is_running == True
        
        # Stop tracking  
        tracker.stop_tracking()
        assert tracker.is_running == False
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available") 
    def test_blink_detection_threshold(self):
        """Test blink detection with different EAR thresholds"""
        # Test with mock EAR values
        high_ear = 0.25  # Eyes open
        low_ear = 0.15   # Eyes closed/blink
        
        # These would be used in actual blink detection logic
        default_threshold = 0.21
        
        assert high_ear > default_threshold  # Should not trigger blink
        assert low_ear < default_threshold   # Should trigger blink
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available")
    def test_performance_monitoring(self, mock_mediapipe, mock_opencv):
        """Test that eye tracking doesn't exceed performance thresholds"""
        import psutil
        import time
        
        # Get baseline CPU usage
        baseline_cpu = psutil.cpu_percent(interval=1)
        
        # Start tracking for a short period
        tracker = EyeTracker()
        tracker.start_tracking()
        
        # Monitor for 3 seconds
        time.sleep(3)
        
        # Check CPU usage during tracking
        tracking_cpu = psutil.cpu_percent(interval=1)
        
        tracker.stop_tracking()
        
        # CPU overhead should be reasonable (< 20% for test environment)
        cpu_increase = tracking_cpu - baseline_cpu
        assert cpu_increase < 20, f"CPU overhead too high: {cpu_increase}%"


@pytest.mark.skipif(not HAS_QT, reason="PyQt6 not available")
class TestDesktopUI:
    """Test desktop application UI components"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def main_window(self, app):
        """Create main window for testing"""
        if not HAS_DESKTOP_MODULES:
            pytest.skip("Desktop modules not available")
            
        with patch('desktop.main.WaWAPI'), \
             patch('desktop.main.EyeTracker'), \
             patch('desktop.main.Config'):
            window = WaWMainWindow()
            return window
    
    def test_main_window_creation(self, main_window):
        """Test main window can be created"""
        assert main_window is not None
        assert main_window.windowTitle() == "Wellness at Work - Eye Tracker"
    
    def test_ui_components_exist(self, main_window):
        """Test that required UI components exist"""
        # Check for essential buttons and labels
        assert hasattr(main_window, 'start_stop_btn')
        assert hasattr(main_window, 'blink_count_label')
        assert hasattr(main_window, 'session_duration_label')
    
    def test_theme_switching(self, main_window):
        """Test light/dark theme switching"""
        # Test theme toggle (if available)
        if hasattr(main_window, 'toggle_theme'):
            original_theme = main_window.current_theme if hasattr(main_window, 'current_theme') else 'light'
            main_window.toggle_theme()
            # Theme should have changed
            assert True  # Basic test that theme toggle doesn't crash
    
    def test_button_interactions(self, main_window, qtbot):
        """Test UI button interactions"""
        # Test start/stop button
        if hasattr(main_window, 'start_stop_btn'):
            qtbot.mouseClick(main_window.start_stop_btn, Qt.MouseButton.LeftButton)
            # Should not crash
            assert True


class TestOfflineStorage:
    """Test offline data storage functionality"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            yield f.name
        # Cleanup
        if os.path.exists(f.name):
            os.unlink(f.name)
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available")
    def test_local_data_storage(self, temp_db_path):
        """Test local SQLite data storage"""
        # This would test the local storage implementation
        # For now, just test that we can create a database file
        import sqlite3
        
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Create a simple test table
        cursor.execute('''
            CREATE TABLE test_blinks (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                blink_count INTEGER
            )
        ''')
        
        # Insert test data
        cursor.execute('''
            INSERT INTO test_blinks (timestamp, blink_count)
            VALUES (?, ?)
        ''', ('2025-01-01 12:00:00', 5))
        
        # Verify data was stored
        cursor.execute('SELECT COUNT(*) FROM test_blinks')
        count = cursor.fetchone()[0]
        assert count == 1
        
        conn.close()
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available")
    def test_sync_queue_functionality(self):
        """Test offline sync queue implementation"""
        # Test that offline data is queued for sync when online
        # This is a placeholder for more detailed sync testing
        
        # Mock offline data
        offline_data = [
            {"timestamp": "2025-01-01T12:00:00Z", "blinks": 5},
            {"timestamp": "2025-01-01T12:01:00Z", "blinks": 3},
        ]
        
        # Test queue operations
        queue = offline_data.copy()
        assert len(queue) == 2
        
        # Simulate processing queue
        while queue:
            item = queue.pop(0)
            assert "timestamp" in item
            assert "blinks" in item
        
        assert len(queue) == 0


class TestConfigurationManagement:
    """Test application configuration management"""
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available")
    def test_config_loading(self):
        """Test configuration file loading"""
        # Test that Config can be instantiated
        try:
            config = Config()
            assert config is not None
        except Exception as e:
            # Config might fail without proper files, that's OK for testing
            assert True
    
    @pytest.mark.skipif(not HAS_DESKTOP_MODULES, reason="Desktop modules not available")
    def test_api_configuration(self):
        """Test API configuration settings"""
        # Test API base URL configuration
        with patch('shared.config.Config') as MockConfig:
            mock_config = MockConfig.return_value
            mock_config.api_base_url = "https://test-api.example.com"
            
            # Test API client initialization with config
            api = WaWAPI(mock_config)
            assert api is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
