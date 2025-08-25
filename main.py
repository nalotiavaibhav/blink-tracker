"""
Wellness at Work (WaW) Eye Tracker - Main Entry Point
Based on PRD specifications

This file serves as the main entry point for development and testing.
For production, use:
- backend/main.py for FastAPI server
- desktop/app.py for PyQt6 application  
- web-dashboard/ for Next.js dashboard
"""

from backend.models import init_database, User, BlinkSample
from datetime import datetime

def test_database_setup():
    """Test database connectivity and models"""
    print("🔧 Testing database setup...")
    
    # Initialize database
    engine, SessionMaker = init_database()
    session = SessionMaker()
    
    # Test user creation
    test_user = User(
        email="demo@waw.com",
        name="Demo User",
        consent=True
    )
    
    session.add(test_user)
    session.commit()
    session.refresh(test_user)
    
    print(f"✅ Created test user: {test_user}")
    
    # Test blink sample creation
    sample = BlinkSample(
        user_id=test_user.id,
        client_sequence=1,
        captured_at_utc=datetime.utcnow(),
        blink_count=20,
        device_id="dev-laptop-001",
        app_version="1.0.0",
        cpu_percent=15.5,
        memory_mb=256.0,
        energy_impact="Low"
    )
    
    session.add(sample)
    session.commit()
    
    print(f"✅ Created blink sample: {sample}")
    
    # Query test
    all_samples = session.query(BlinkSample).filter(BlinkSample.user_id == test_user.id).all()
    print(f"✅ Found {len(all_samples)} samples for user")
    
    session.close()
    print("🎉 Database test completed successfully!")

def start_backend_server():
    """Start FastAPI backend server"""
    import subprocess
    import sys
    
    print("🚀 Starting FastAPI backend server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API docs available at: http://localhost:8000/docs")
    
    # Run the backend server
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "backend.main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test-db":
            test_database_setup()
        elif command == "server":
            start_backend_server()
        else:
            print("Usage: python main.py [test-db|server]")
    else:
        print("🏗️ Wellness at Work (WaW) Eye Tracker")
        print("=" * 50)
        print("Available commands:")
        print("  python main.py test-db  - Test database setup")
        print("  python main.py server   - Start FastAPI backend")
        print()
        print("📋 Project Structure:")
        print("  backend/     - FastAPI backend server")
        print("  desktop/     - PyQt6 desktop application")  
        print("  web-dashboard/ - Next.js web dashboard")
        print("  shared/      - Shared utilities")
        print()
        print("📖 See README.md for complete setup instructions")