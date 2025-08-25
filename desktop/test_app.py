"""
Simple test for WaW Desktop Application - without camera
Tests basic functionality, database connection, and UI
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from backend.models import SessionLocal, User, BlinkSample

class SimpleTestWindow(QMainWindow):
    """Simple test window for WaW Desktop App."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.test_database()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("WaW Test - Database & UI")
        self.setGeometry(100, 100, 600, 400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🚀 WaW Desktop Test")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Status display
        self.status_label = QLabel("Testing database connection...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Database info
        self.db_info_label = QLabel("")
        self.db_info_label.setWordWrap(True)
        layout.addWidget(self.db_info_label)
        
        # Test button
        test_btn = QPushButton("Run Database Test")
        test_btn.clicked.connect(self.test_database)
        layout.addWidget(test_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def test_database(self):
        """Test database functionality."""
        try:
            with SessionLocal() as db:
                # Count users and samples
                user_count = db.query(User).count()
                sample_count = db.query(BlinkSample).count()
                
                # Get first user
                first_user = db.query(User).first()
                
                self.status_label.setText("✅ Database connection successful!")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                
                info = f"""Database Status:
• Users in database: {user_count}
• Blink samples: {sample_count}
• First user: {first_user.name if first_user else 'None'} ({first_user.email if first_user else 'N/A'})
• Database file: waw_local.db
• SQLAlchemy version: Working ✅
• PyQt6 GUI: Working ✅
"""
                self.db_info_label.setText(info)
                
        except Exception as e:
            self.status_label.setText(f"❌ Database error: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.db_info_label.setText(f"Error details: {str(e)}")

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("WaW Test")
    
    # Create and show test window
    window = SimpleTestWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
