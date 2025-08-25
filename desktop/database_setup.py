"""
Database setup utility for desktop application
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models import SessionLocal, User, BlinkSample, init_database
from datetime import datetime

def setup_database():
    """Initialize database and create default user if needed"""
    try:
        # Test database connection
        with SessionLocal() as db:
            # Check if we have any users
            user_count = db.query(User).count()
            print(f"Database connected successfully. Found {user_count} users.")
            
            if user_count == 0:
                # Create default user
                default_user = User(
                    email="local@example.com",
                    name="Local User",
                    consent=True
                )
                db.add(default_user)
                db.commit()
                db.refresh(default_user)
                print(f"Created default user: {default_user}")
            
            return True
    except Exception as e:
        print(f"Database setup error: {e}")
        return False

if __name__ == "__main__":
    success = setup_database()
    if success:
        print("✅ Database setup completed successfully!")
    else:
        print("❌ Database setup failed!")
