"""
Debug startup script for WaW Desktop Application
Use this to test the application components individually and identify startup issues.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    try:
        import PyQt6
        print("✓ PyQt6 imported successfully")
    except ImportError as e:
        print(f"✗ PyQt6 import failed: {e}")
        return False
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("✓ PyQt6.QtWidgets imported successfully")
    except ImportError as e:
        print(f"✗ PyQt6.QtWidgets import failed: {e}")
        return False
    
    try:
        import cv2
        print("✓ OpenCV imported successfully")
    except ImportError as e:
        print(f"✗ OpenCV import failed: {e}")
        return False
    
    try:
        import mediapipe
        print("✓ MediaPipe imported successfully")
    except ImportError as e:
        print(f"✗ MediaPipe import failed: {e}")
        return False
    
    try:
        import psutil
        print("✓ psutil imported successfully")
    except ImportError as e:
        print(f"✗ psutil import failed: {e}")
        return False
    
    try:
        import requests
        print("✓ requests imported successfully")
    except ImportError as e:
        print(f"✗ requests import failed: {e}")
        return False
    
    try:
        from shared.config import CONFIG
        print(f"✓ Config imported successfully - Backend URL: {CONFIG.api_base_url}")
    except ImportError as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from shared.api import ApiClient
        print("✓ API client imported successfully")
    except ImportError as e:
        print(f"✗ API client import failed: {e}")
        return False
    
    try:
        from desktop.eye_tracker import EyeTracker
        print("✓ Eye tracker imported successfully")
    except ImportError as e:
        print(f"✗ Eye tracker import failed: {e}")
        return False
    
    return True

def test_camera():
    """Test camera access"""
    print("\nTesting camera access...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print("✓ Camera access successful")
                cap.release()
                return True
            else:
                print("✗ Camera opened but cannot read frames")
                cap.release()
                return False
        else:
            print("✗ Cannot open camera")
            return False
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False

def test_backend_connection():
    """Test backend connectivity"""
    print("\nTesting backend connection...")
    try:
        from shared.config import CONFIG
        from shared.api import ApiClient
        
        api = ApiClient(CONFIG.api_base_url)
        print(f"Testing connection to: {CONFIG.api_base_url}")
        
        # Try to reach health endpoint
        import requests
        response = requests.get(f"{CONFIG.api_base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Backend health check successful")
            return True
        else:
            print(f"✗ Backend returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to backend (connection refused)")
        return False
    except requests.exceptions.Timeout:
        print("✗ Backend connection timeout")
        return False
    except Exception as e:
        print(f"✗ Backend test failed: {e}")
        return False

def test_qt_application():
    """Test Qt application creation"""
    print("\nTesting Qt application...")
    try:
        from PyQt6.QtWidgets import QApplication
        import sys
        
        app = QApplication(sys.argv)
        print("✓ Qt application created successfully")
        app.quit()
        return True
    except Exception as e:
        print(f"✗ Qt application test failed: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("=" * 60)
    print("WaW Desktop Application Startup Diagnostics")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Camera Tests", test_camera),
        ("Backend Connection", test_backend_connection),
        ("Qt Application", test_qt_application),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Application should start successfully")
        print("If the app still doesn't start, try running:")
        print("  python desktop/main.py")
    else:
        print("✗ SOME TESTS FAILED - Fix issues above before running application")
        
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        input("\nPress Enter to exit...")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDiagnostics interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during diagnostics: {e}")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
