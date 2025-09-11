"""
WaW Desktop Application - Main Window
Integrates eye tracking with PyQt6 GUI and backend sync
"""

import sys
import uuid
import json
import os
import warnings
from pathlib import Path
import psutil
import time
from datetime import datetime
from typing import Dict

# Suppress PyQt6 deprecation warnings about sipPyTypeDict()
# These are harmless warnings from PyQt6 library internals
warnings.filterwarnings("ignore", message=".*sipPyTypeDict.*", category=DeprecationWarning)

# Ensure project root on sys.path so `backend` and `shared` can be imported
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QGroupBox,
    QGridLayout, QStatusBar, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QComboBox, QMenuBar, QMenu, QTabWidget, QTableWidget, QTableWidgetItem,
    QCheckBox
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

from desktop.eye_tracker import EyeTracker
from shared.db import get_or_create_default_user
from shared.config import CONFIG
from shared.api import ApiClient
# from shared.google_oauth import get_google_id_token_interactive  # (Temporarily disabled) Google sign-in currently not functioning; UI removed.


def set_app_icon(widget):
    """Set the application icon for a QWidget (window or dialog)."""
    try:
        icon_candidates = [
            project_root / 'assets' / 'app.ico',
            project_root / 'assets' / 'favicon.ico', 
            project_root / 'assets' / 'android-chrome-192x192.png',
        ]
        for candidate in icon_candidates:
            if candidate.exists():
                widget.setWindowIcon(QIcon(str(candidate)))
                break
    except Exception:
        pass


def get_user_friendly_error(exception, base_url=""):
    """Convert technical API errors into user-friendly messages."""
    error_msg = str(exception).lower()
    
    # Handle common connection errors
    if any(phrase in error_msg for phrase in ['connection', 'refused', 'timeout', 'unreachable', 'port']):
        if 'render' in base_url.lower():
            return "Server is starting up (may take 30-60 seconds)..."
        else:
            return "Cannot connect to server. Please check your internet connection."
    elif 'unauthorized' in error_msg or 'invalid' in error_msg or '401' in error_msg:
        return "Invalid credentials"
    elif '404' in error_msg:
        return "Server not found. Please check the server URL."
    elif '500' in error_msg or 'internal' in error_msg:
        return "Server error. Please try again later."
    elif 'timeout' in error_msg:
        return "Server took too long to respond. Please try again."
    elif '409' in error_msg or 'conflict' in error_msg:
        return "Email already registered. Please login instead."
    elif '422' in error_msg or 'validation' in error_msg:
        return "Invalid data provided. Please check your inputs."
    else:
        return "Operation failed. Please try again."


class PerformanceMonitor(QThread):
    """Thread to monitor blink-tracker application performance metrics."""
    performance_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.process = psutil.Process()

    def run(self):
        self.is_running = True
        while self.is_running:
            try:
                mem = self.process.memory_info()
                memory_mb = mem.rss / (1024 * 1024)
                cpu_percent = self.process.cpu_percent(interval=1.0)
                system_memory = psutil.virtual_memory()
                memory_percent = (mem.rss / system_memory.total) * 100
                self.performance_updated.emit({
                    "cpu_percent": cpu_percent,
                    "memory_used_mb": memory_mb,
                    "memory_percent": memory_percent,
                    "num_threads": self.process.num_threads(),
                    "timestamp": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                print(f"Performance monitoring error: {e}")
            self.msleep(5000)

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class WaWMainWindow(QMainWindow):
    """Main application window for WaW Desktop App."""

    def __init__(self, initial_auth=None):
        super().__init__()
        self.eye_tracker = None
        self.performance_monitor = PerformanceMonitor()
        self.current_user = None
        self.blink_data_buffer = []
        self.last_sync_time = None
        self._session_cpu_sum = 0.0
        self._session_mem_sum = 0.0
        self._session_metric_count = 0
        self._client_session_id = None
        self._session_counter_date = None
        self._session_counter = 0

        self.init_ui()
        self.init_menu_bar()
        self.performance_monitor.performance_updated.connect(self.update_performance_display)
        self.performance_monitor.start()
        self.init_sync_timer()
        self.load_user_session()
        self.api = None  # type: ignore
        self.start_stop_btn.setEnabled(False)

        if not initial_auth:
            try:
                saved = load_saved_auth()
                if saved:
                    base_url, token, user = saved
                    api = ApiClient(base_url)
                    api.set_token(token)
                    if api.validate_token():
                        self.api = api
                        self.eye_tracker = EyeTracker(callback=self.on_blink_data)
                        self.start_stop_btn.setEnabled(True)
                        self.sync_status_label.setText(f"Online as {user.get('email','')}")
                        self.sync_status_label.setStyleSheet("color: green;")
                        self.status_bar.showMessage("Auto login successful")
                        try:
                            if hasattr(self, 'delete_account_btn'):
                                self.delete_account_btn.setEnabled(True)
                                self.update_delete_button_style()
                        except Exception:
                            pass
                        try:
                            self.load_my_sessions()
                        except Exception:
                            pass
                    else:
                        delete_saved_auth()
            except Exception:
                pass

        if initial_auth:
            base_url, token, user = initial_auth
            self.api = ApiClient(base_url)
            self.api.set_token(token)
            if self.api.validate_token():
                self.eye_tracker = EyeTracker(callback=self.on_blink_data)
                self.start_stop_btn.setEnabled(True)
                self.sync_status_label.setText(f"Online as {user.get('email','')}")
                self.sync_status_label.setStyleSheet("color: green;")
                self.status_bar.showMessage("Login successful")
                try:
                    if hasattr(self, 'delete_account_btn'):
                        self.delete_account_btn.setEnabled(True)
                        self.update_delete_button_style()
                except Exception:
                    pass
                try:
                    self.load_my_sessions()
                except Exception:
                    pass
            else:
                reason = getattr(self.api, 'last_token_error', None) or 'unknown'
                self.status_bar.showMessage(f"Session invalid ({reason}); please re-login from Start Tracking")

    def init_ui(self):
        """Build UI with compact tracking layout inside tab; keep everything in method scope."""
        self.setWindowTitle("Wellness at Work - Eye Tracker")
        self.resize(880, 620)

        # Set application icon
        set_app_icon(self)
        
        # Additional Windows taskbar icon setup
        try:
            import ctypes
            # Force taskbar icon refresh by setting window attributes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowTextW(hwnd, "Wellness at Work - Eye Tracker")
        except Exception:
            pass

        # Theme preference
        self.settings_file = Path("desktop_settings.json")
        self.current_theme = self.load_theme_preference()

        # Central widget & layout
        central = QWidget()
        self.setCentralWidget(central)
        root_v = QVBoxLayout(central)
        root_v.setContentsMargins(14, 12, 14, 12)
        root_v.setSpacing(8)

        self.title_label = QLabel("blink-tracker")
        self.title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_v.addWidget(self.title_label)

        # Tabs (theme-aware styling applied in theme stylesheets)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root_v.addWidget(self.tabs)

        # Tracking tab with grid
        tracking_tab = QWidget()
        track_grid = QGridLayout(tracking_tab)
        track_grid.setContentsMargins(12, 10, 12, 10)
        track_grid.setHorizontalSpacing(12)
        track_grid.setVerticalSpacing(8)

        tracking_group = self.create_tracking_section()
        perf_group = self.create_performance_section()
        sync_group = self.create_sync_section()
        theme_group = self.create_theme_section()
        controls_widget = self.create_control_section()

        track_grid.addWidget(tracking_group, 0, 0)
        track_grid.addWidget(perf_group, 0, 1)
        track_grid.addWidget(sync_group, 1, 0)
        track_grid.addWidget(theme_group, 1, 1)
        track_grid.addWidget(controls_widget, 2, 0, 1, 2)
        track_grid.setRowStretch(3, 1)
        self.tabs.addTab(tracking_tab, "Tracking")

        # My Data tab
        self.my_data_tab = QWidget()
        my_layout = QVBoxLayout(self.my_data_tab)
        my_layout.setContentsMargins(12, 10, 12, 10)
        my_layout.setSpacing(6)
        self.sessions_header = QLabel("My Sessions")
        self.sessions_header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        my_layout.addWidget(self.sessions_header)
        self.refresh_mydata_btn = QPushButton("Refresh")
        self.refresh_mydata_btn.clicked.connect(self.load_my_sessions)
        self.refresh_mydata_btn.setFixedHeight(32)
        # Actions row (Refresh + Delete My Data)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.addWidget(self.refresh_mydata_btn)
        self.delete_account_btn = QPushButton("Delete My Data")
        self.delete_account_btn.setToolTip("Permanently delete your account and all associated data")
        self.delete_account_btn.setFixedHeight(32)
        self.delete_account_btn.clicked.connect(self.delete_my_account)
        self.delete_account_btn.setEnabled(False)  # Enabled after successful auth
        actions_row.addWidget(self.delete_account_btn)
        actions_row.addStretch(1)
        my_layout.addLayout(actions_row)
        self.sessions_table = QTableWidget(0, 4)
        self.sessions_table.setHorizontalHeaderLabels(["Ended At", "Session ID", "Blinks", "Energy"])
        my_layout.addWidget(self.sessions_table)
        self.tabs.addTab(self.my_data_tab, "My Data")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to start tracking")

        # Apply theme now that key widgets exist
        self.apply_theme(self.current_theme)

        # Center window
        self.center_on_screen()

    def init_menu_bar(self):
        """Initialize menu bar with theme selection."""
        menubar = self.menuBar()
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Theme submenu
        theme_menu = view_menu.addMenu("Theme")
        
        # Light theme action
        light_action = theme_menu.addAction("Light Theme")
        light_action.triggered.connect(lambda: self.change_theme("light"))
        
        # Dark theme action
        dark_action = theme_menu.addAction("Dark Theme")
        dark_action.triggered.connect(lambda: self.change_theme("dark"))

    def change_theme(self, theme_name):
        """Change the application theme."""
        self.current_theme = theme_name
        self.apply_theme(theme_name)
        self.save_theme_preference(theme_name)
        self.update_theme_dependent_styles()
        if hasattr(self, 'theme_combo'):
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText(theme_name.title())
            self.theme_combo.blockSignals(False)
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Theme changed to {theme_name.title()}")

    def load_theme_preference(self):
        """Load saved theme preference."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    return settings.get('theme', 'light')
        except Exception as e:
            print(f"Error loading theme preference: {e}")
        return 'light'  # Default

    def save_theme_preference(self, theme_name):
        """Save theme preference to file."""
        try:
            settings = {}
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            
            settings['theme'] = theme_name
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving theme preference: {e}")

    def apply_theme(self, theme_name):
        """Apply the selected theme to the application."""
        if theme_name == "dark":
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
        self.update_theme_dependent_styles()

    def apply_dark_theme(self):
        """Apply dark theme with unified background color (#181b20)."""
        palette = QPalette()
        unified_bg = QColor(24, 27, 32)  # #181b20
        palette.setColor(QPalette.ColorRole.Window, unified_bg)
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, unified_bg)
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 44, 50))
        palette.setColor(QPalette.ColorRole.Text, QColor(230, 232, 235))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, unified_bg)
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(230, 232, 235))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(13, 71, 161))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(82, 148, 226))
        self.setPalette(palette)
        self.apply_dark_widget_styles()
        self.update()
        self.repaint()

    def apply_dark_widget_styles(self):
        """Apply specific styles for dark theme widgets."""
        dark_style = """
        /* Unified dark theme to match login dialog */
        QMainWindow, QWidget { background-color: #181b20; color: #e6e8eb; }
        QLabel { color: #d0d4d8; }
        QLabel#statusLabel { color: #7d8691; }
    QTabWidget::pane { border:1px solid #2d3136; border-radius:6px; background:#181b20; }
    QTabBar::tab { background:#181b20; padding:6px 12px; border:1px solid #2d3136; border-bottom:none; border-top-left-radius:6px; border-top-right-radius:6px; color:#b9c2cc; }
    QTabBar::tab:selected { background:#121519; color:#ffffff; }
    QTabBar::tab:hover { color:#ffffff; }
        QGroupBox { 
            font-weight: 600; 
            border: 1px solid #2d3136; 
            border-radius: 10px; 
            margin-top: 18px; 
            padding: 10px; 
            background: #181b20; /* same as window for flat look */
            color: #e6e8eb; 
        }
        QGroupBox::title { 
            subcontrol-origin: margin; 
            left: 14px; 
            padding: 0 6px; 
            background: transparent; 
            color: #8aa4c1; 
            font-size: 12px; 
            font-weight: 600; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
        }
        QProgressBar { 
            border: 1px solid #2d3136; 
            border-radius: 6px; 
            text-align: center; 
            background-color: #20252b; 
            color: #e6e8eb; 
            height: 18px; 
        }
        QProgressBar::chunk { 
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0d47a1, stop:1 #0b3c91); 
            border-radius: 5px; 
        }
        QComboBox { 
            border: 1px solid #2d3136; 
            border-radius: 6px; 
            padding: 4px 24px 4px 8px; 
            background: #181b20; 
            color: #e6e8eb; 
        }
        QComboBox:hover { border-color: #295fa6; }
        QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 18px; border-left: 1px solid #2d3136; }
        QPushButton { 
            border: 1px solid #2d3136; 
            border-radius: 8px; 
            padding: 8px 16px; 
            background: #181b20; 
            color: #e6e8eb; 
            font-weight: 500; 
        }
        QPushButton:hover { background: #20252b; border-color: #295fa6; }
        QPushButton:pressed { background: #13171b; }
        QPushButton#primaryButton { 
            border: none; 
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0d47a1, stop:1 #0b3c91); 
            color: #ffffff; 
            font-weight: 600; 
        }
        QPushButton#primaryButton:hover { background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #1560c6, stop:1 #104f9f); }
        QPushButton#primaryButton:pressed { background: #0b3c91; }
        QTableWidget { background: #181b20; gridline-color: #2d3136; color: #e6e8eb; selection-background-color: #0d47a1; }
        QHeaderView::section { background: #121519; color: #b9c2cc; border: 1px solid #2d3136; padding: 4px; }
        QStatusBar { background: #181b20; color: #b9c2cc; }
        QScrollBar:vertical { background: #121519; width: 12px; margin: 0; }
        QScrollBar::handle:vertical { background: #2d3136; min-height: 24px; border-radius: 6px; }
        QScrollBar::handle:vertical:hover { background: #3a4249; }
        QScrollBar::add-line, QScrollBar::sub-line { height:0; }
        """
        self.setStyleSheet(dark_style)

        # Promote key buttons to primary look
        try:
            if hasattr(self, 'start_stop_btn'):
                self.start_stop_btn.setObjectName("primaryButton")
        except Exception:
            pass
        # Title color
        self.update_theme_dependent_styles()

    def apply_light_widget_styles(self):
        """Apply specific styles for light theme to avoid invisible text after dark mode."""
        light_style = """
        QMainWindow, QWidget { background-color: #f5f6f8; color: #222629; }
        QLabel { color: #222629; }
        QLabel#statusLabel { color: #555f66; }
    QTabWidget::pane { border:1px solid #d0d4d9; border-radius:6px; background:#f5f6f8; }
    QTabBar::tab { background:#f5f6f8; padding:6px 12px; border:1px solid #d0d4d9; border-bottom:none; border-top-left-radius:6px; border-top-right-radius:6px; color:#40505e; }
    QTabBar::tab:selected { background:#ffffff; color:#1e2327; }
    QTabBar::tab:hover { color:#1976d2; }
        QGroupBox {
            font-weight: 600;
            border: 1px solid #d0d4d9;
            border-radius: 10px;
            margin-top: 18px;
            padding: 10px;
            /* Unified background with window for flat look */
            background: #f5f6f8;
            color: #1e2327;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 6px;
            background: transparent;
            color: #3c5064;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        QProgressBar {
            border: 1px solid #c5c9ce;
            border-radius: 6px;
            text-align: center;
            background: #eef0f2;
            color: #1e2327;
            height: 18px;
        }
        QProgressBar::chunk {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #1976d2, stop:1 #1565c0);
            border-radius: 5px;
        }
        QComboBox {
            border: 1px solid #c5c9ce;
            border-radius: 6px;
            padding: 4px 24px 4px 8px;
            background: #ffffff;
            color: #1e2327;
        }
        QComboBox:hover { border-color: #1976d2; }
        QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 18px; border-left: 1px solid #c5c9ce; }
        QPushButton {
            border: 1px solid #c5c9ce;
            border-radius: 8px;
            padding: 8px 16px;
            background: #ffffff;
            color: #1e2327;
            font-weight: 500;
        }
        QPushButton:hover { background: #f0f2f4; border-color: #1976d2; }
        QPushButton:pressed { background: #e5e7ea; }
        QPushButton#primaryButton {
            border: none;
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #1976d2, stop:1 #1565c0);
            color: #ffffff;
            font-weight: 600;
        }
        QPushButton#primaryButton:hover { background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #1e82e4, stop:1 #1870cc); }
        QPushButton#primaryButton:pressed { background: #1565c0; }
    /* Table unified with overall background */
    QTableWidget { background: #f5f6f8; gridline-color: #d0d4d9; color: #222629; selection-background-color: #1976d2; }
        QHeaderView::section { background: #f0f2f4; color: #40505e; border: 1px solid #d0d4d9; padding: 4px; }
        QStatusBar { background: #ffffff; color: #40505e; }
        QScrollBar:vertical { background: #eef0f2; width: 12px; margin: 0; }
        QScrollBar::handle:vertical { background: #c5c9ce; min-height: 24px; border-radius: 6px; }
        QScrollBar::handle:vertical:hover { background: #b5b9be; }
        QScrollBar::add-line, QScrollBar::sub-line { height:0; }
        """
        self.setStyleSheet(light_style)
        try:
            if hasattr(self, 'start_stop_btn'):
                self.start_stop_btn.setObjectName("primaryButton")
        except Exception:
            pass
        self.update_theme_dependent_styles()

    def apply_light_theme(self):
        """Apply light/grayscale theme."""
        # Apply palette tuned for light theme
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 246, 248))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(34, 38, 41))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 242, 244))
        palette.setColor(QPalette.ColorRole.Text, QColor(34, 38, 41))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(34, 38, 41))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(25, 118, 210))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        # Apply light stylesheet
        self.apply_light_widget_styles()

    def update_theme_dependent_styles(self):
        """Adjust inline-styled widgets to current theme (avoids invisible text)."""
        try:
            if hasattr(self, 'title_label'):
                if self.current_theme == 'dark':
                    self.title_label.setStyleSheet("color:#ffffff; letter-spacing:1px;")
                else:
                    self.title_label.setStyleSheet("color:#1e2327; letter-spacing:1px;")
            if hasattr(self, 'sessions_header'):
                if self.current_theme == 'dark':
                    self.sessions_header.setStyleSheet("color:#ffffff;")
                else:
                    self.sessions_header.setStyleSheet("color:#1e2327;")
            if hasattr(self, 'delete_account_btn'):
                self.update_delete_button_style()
        except Exception:
            pass

    def create_tracking_section(self):
        tracking_group = QGroupBox("Eye Blink Tracking")
        tracking_layout = QGridLayout(tracking_group)
        self.blink_count_label = QLabel("0")
        self.blink_count_label.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.blink_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tracking_layout.addWidget(QLabel("Total Blinks:"), 0, 0)
        tracking_layout.addWidget(self.blink_count_label, 0, 1)
        self.session_id_label = QLabel("-")
        tracking_layout.addWidget(QLabel("Session ID:"), 0, 2)
        tracking_layout.addWidget(self.session_id_label, 0, 3)
        self.session_duration_label = QLabel("00:00:00")
        self.session_duration_label.setFont(QFont("Arial", 14))
        tracking_layout.addWidget(QLabel("Session Duration:"), 1, 0)
        tracking_layout.addWidget(self.session_duration_label, 1, 1)
        self.last_blink_label = QLabel("No blinks yet")
        tracking_layout.addWidget(QLabel("Last Blink:"), 2, 0)
        tracking_layout.addWidget(self.last_blink_label, 2, 1)
        self.tracking_status_label = QLabel("Stopped")
        self.tracking_status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        tracking_layout.addWidget(QLabel("Status:"), 3, 0)
        tracking_layout.addWidget(self.tracking_status_label, 3, 1)
        return tracking_group

    def create_performance_section(self):
        perf_group = QGroupBox("Application Performance")
        perf_layout = QGridLayout(perf_group)
        
        perf_layout.addWidget(QLabel("CPU Usage:"), 0, 0)
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setMaximum(100)
        self.cpu_label = QLabel("0%")
        perf_layout.addWidget(self.cpu_progress, 0, 1)
        perf_layout.addWidget(self.cpu_label, 0, 2)
        
        perf_layout.addWidget(QLabel("Memory Usage:"), 1, 0)
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)  # Will show percentage
        self.memory_label = QLabel("0 MB")
        perf_layout.addWidget(self.memory_progress, 1, 1)
        perf_layout.addWidget(self.memory_label, 1, 2)
        
        perf_layout.addWidget(QLabel("Threads:"), 2, 0)
        self.threads_label = QLabel("0")
        perf_layout.addWidget(self.threads_label, 2, 1)
        return perf_group

    def create_sync_section(self):
        sync_group = QGroupBox("Cloud Sync")
        sync_layout = QGridLayout(sync_group)
        self.sync_status_label = QLabel("Offline Mode")
        sync_layout.addWidget(QLabel("Status:"), 0, 0)
        sync_layout.addWidget(self.sync_status_label, 0, 1)
        self.last_sync_label = QLabel("Never")
        sync_layout.addWidget(QLabel("Last Sync:"), 1, 0)
        sync_layout.addWidget(self.last_sync_label, 1, 1)
        self.pending_records_label = QLabel("0")
        sync_layout.addWidget(QLabel("Pending Records:"), 2, 0)
        sync_layout.addWidget(self.pending_records_label, 2, 1)
        return sync_group

    def create_theme_section(self):
        """Build appearance (theme) selector group and return it."""
        theme_group = QGroupBox("Appearance")
        theme_layout = QHBoxLayout(theme_group)
        theme_layout.setContentsMargins(8, 6, 8, 6)
        theme_layout.setSpacing(8)

        label = QLabel("Theme:")
        theme_layout.addWidget(label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(self.current_theme.title())
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        self.theme_combo.setMinimumWidth(120)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        return theme_group

    def on_theme_changed(self, theme_text):
        """Handle theme change from dropdown."""
        theme_name = theme_text.lower()
        if theme_name != self.current_theme:  # Only change if different
            self.change_theme(theme_name)

    def create_control_section(self):
        """Create bottom control bar with tracking, sync, and logout."""
        container = QWidget()
        control_layout = QHBoxLayout(container)
        control_layout.setContentsMargins(0, 4, 0, 0)
        control_layout.setSpacing(10)
        # Start/Stop tracking
        self.start_stop_btn = QPushButton("Start Tracking")
        self.start_stop_btn.clicked.connect(self.toggle_tracking)
        self.start_stop_btn.setMinimumHeight(40)
        control_layout.addWidget(self.start_stop_btn)
        # Manual sync (status refresh only)
        self.sync_btn = QPushButton("Sync Now")
        self.sync_btn.clicked.connect(self.sync_data)
        self.sync_btn.setMinimumHeight(40)
        control_layout.addWidget(self.sync_btn)
        control_layout.addStretch(1)
        # Logout
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setMinimumHeight(40)
        self.logout_btn.clicked.connect(self.logout)
        control_layout.addWidget(self.logout_btn)
        return container

    def show_login_dialog(self):
        """Open a login dialog for (re)authentication. Silent if cancelled."""
        dlg = LoginDialog(
            default_base_url=CONFIG.api_base_url,
            parent=self,
            theme=getattr(self, 'current_theme', 'light')
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            base_url, token, user = dlg.get_result()
            self.api = ApiClient(base_url)
            self.api.set_token(token)
            if self.api.validate_token():
                if not self.eye_tracker:
                    self.eye_tracker = EyeTracker(callback=self.on_blink_data)
                self.start_stop_btn.setEnabled(True)
                self.sync_status_label.setText(f"Online as {user.get('email','')}")
                self.sync_status_label.setStyleSheet("color: green;")
                self.status_bar.showMessage("Login successful")
                try:
                    save_auth(base_url, token, user)
                except Exception:
                    pass
                try:
                    if hasattr(self, 'delete_account_btn'):
                        self.delete_account_btn.setEnabled(True)
                        self.update_delete_button_style()
                except Exception:
                    pass
                try:
                    self.load_my_sessions()
                except Exception:
                    pass
            else:
                self.status_bar.showMessage("Token invalid after login attempt")

    def init_sync_timer(self):
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_data)
        self.sync_timer.start(30000)

    def toggle_tracking(self):
        if self.eye_tracker and self.eye_tracker.is_running:
            self.stop_tracking()
        else:
            self.start_tracking()

    def start_tracking(self):
        if not self.eye_tracker:
            self.status_bar.showMessage("Eye tracker not initialized - please restart application")
            return
            
        if (self.api and self.api.is_authed) and self.eye_tracker.start_tracking():
            # Sequential session id: N_YYYYMMDD where N resets each day and continues after existing entries
            today_str = datetime.now().strftime("%Y%m%d")
            if self._session_counter_date != today_str:
                # New day: reset and infer existing max from table (if loaded)
                self._session_counter_date = today_str
                self._session_counter = 0
                try:
                    if hasattr(self, 'sessions_table'):
                        rows = self.sessions_table.rowCount()
                        for r in range(rows):
                            item = self.sessions_table.item(r, 1)
                            if not item:
                                continue
                            txt = (item.text() or '').strip()
                            if txt.endswith('_' + today_str):
                                try:
                                    n = int(txt.split('_', 1)[0])
                                    if n > self._session_counter:
                                        self._session_counter = n
                                except Exception:
                                    pass
                except Exception:
                    pass
            self._session_counter += 1
            self._client_session_id = f"{self._session_counter}_{today_str}"
            self._session_cpu_sum = 0.0
            self._session_mem_sum = 0.0
            self._session_metric_count = 0
            self.session_id_label.setText(self._client_session_id)
            self.start_stop_btn.setText("Stop Tracking")
            self.tracking_status_label.setText("Active")
            self.tracking_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.status_bar.showMessage("Eye tracking started")
            self.ui_update_timer = QTimer()
            self.ui_update_timer.timeout.connect(self.update_tracking_display)
            self.ui_update_timer.start(1000)
        else:
            if not (self.api and self.api.is_authed):
                self.status_bar.showMessage("Please login first (Start Tracking disabled)")
                self.show_login_dialog()
            else:
                self.status_bar.showMessage("Failed to start eye tracking - check camera access")

    def stop_tracking(self):
        # Build and upload one session summary before stopping/resetting
        ended_at = datetime.utcnow()
        stats = self.eye_tracker.get_current_stats() if self.eye_tracker else {"blink_count": 0, "session_start": None}
        started_at_iso = stats.get("session_start")
        total_blinks = int(stats.get("blink_count") or 0)
        try:
            avg_cpu = (self._session_cpu_sum / self._session_metric_count) if self._session_metric_count else None
            avg_mem = (self._session_mem_sum / self._session_metric_count) if self._session_metric_count else None
            def classify_energy(cpu, mem):
                if cpu is None and mem is None:
                    return None
                cpu_v = cpu or 0
                mem_v = mem or 0
                if cpu_v >= 70 or mem_v >= 4000:
                    return "High"
                if cpu_v >= 40 or mem_v >= 2000:
                    return "Medium"
                return "Low"
            energy = classify_energy(avg_cpu, avg_mem)
            if self.api and self.api.is_authed and started_at_iso:
                payload = [{
                    "client_session_id": self._client_session_id or uuid.uuid4().hex[:16],
                    "started_at_utc": started_at_iso,
                    "ended_at_utc": ended_at.isoformat(),
                    "total_blinks": total_blinks,
                    "device_id": CONFIG.device_id,
                    "app_version": CONFIG.app_version,
                    "avg_cpu_percent": avg_cpu,
                    "avg_memory_mb": avg_mem,
                    "energy_impact": energy,
                }]
                try:
                    # Ensure token still valid; if not, attempt re-login once
                    if not self.api.validate_token():
                        relog = QMessageBox.question(
                            self,
                            "Re-authentication Required",
                            "Session upload requires a fresh login. Re-login now?",
                        )
                        if relog == QMessageBox.StandardButton.Yes:
                            self.show_login_dialog()
                        else:
                            raise RuntimeError("User declined re-auth; session kept local.")
                    if self.api and self.api.is_authed:
                        self.api.upload_sessions(payload)
                        self.sync_status_label.setText("Session uploaded")
                        self.sync_status_label.setStyleSheet("color: green;")
                except Exception as e:
                    # Non-fatal: stay local-only if offline
                    self.sync_status_label.setText("Upload failed (session cached only)")
                    self.sync_status_label.setStyleSheet("color: orange;")
                    print(f"Session upload failed: {e}")
        finally:
            # Stop tracking and reset session state
            if self.eye_tracker:
                self.eye_tracker.stop_tracking()
                try:
                    self.eye_tracker.reset_session()
                except Exception:
                    pass
            self._client_session_id = None
            self._session_cpu_sum = 0.0
            self._session_mem_sum = 0.0
            self._session_metric_count = 0
        self.start_stop_btn.setText("Start Tracking")
        self.tracking_status_label.setText("Stopped")
        self.tracking_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.status_bar.showMessage("Eye tracking stopped")
        if hasattr(self, "ui_update_timer"):
            self.ui_update_timer.stop()
        # Update UI counters to reflect reset state
        self.blink_count_label.setText("0")
        self.session_duration_label.setText("00:00:00")
        self.last_blink_label.setText("No blinks yet")
        self.session_id_label.setText("-")

    def logout(self):
        # Stop tracking if active
        try:
            if self.eye_tracker and self.eye_tracker.is_running:
                self.eye_tracker.stop_tracking()
        except Exception:
            pass
        # Clear persisted auth and close this window
        delete_saved_auth()
        self.api = None
        app = QApplication.instance()
        # Close current main window
        self.close()
        # Launch fresh login dialog (standalone) to restart flow
        login = LoginDialog(
            default_base_url=CONFIG.api_base_url,
            theme=getattr(self, 'current_theme', 'light')
        )
        if login.exec() == QDialog.DialogCode.Accepted:
            base_url, token, user = login.get_result()
            try:
                save_auth(base_url, token, user)
            except Exception:
                pass
            new_window = WaWMainWindow(initial_auth=(base_url, token, user))
            # Keep a reference on the app to avoid GC
            setattr(app, "_main_window", new_window)
            new_window.show()
        else:
            # User cancelled login -> quit app
            app.quit()

    def on_blink_data(self, data: Dict):
        self.blink_data_buffer.append(data)
        if not self.current_user:
            self.current_user = get_or_create_default_user()
    # Intentionally stop storing per-second samples; we'll upload only one summary per session
    # Kept buffer for potential in-memory use or future UI features.

    def update_tracking_display(self):
        if self.eye_tracker and self.eye_tracker.is_running:
            stats = self.eye_tracker.get_current_stats()
            self.blink_count_label.setText(str(stats["blink_count"]))
            duration = int(stats["session_duration"])
            h, rem = divmod(duration, 3600)
            m, s = divmod(rem, 60)
            self.session_duration_label.setText(f"{h:02d}:{m:02d}:{s:02d}")
            if stats["last_blink_time"]:
                # Parse stored UTC ISO timestamp and convert to local system timezone
                try:
                    last_blink_utc = datetime.fromisoformat(stats["last_blink_time"].replace("Z", "+00:00"))
                    if last_blink_utc.tzinfo is None:
                        # Assume UTC if tzinfo missing
                        from datetime import timezone
                        last_blink_utc = last_blink_utc.replace(tzinfo=timezone.utc)
                    # Convert to local timezone (no arg -> local)
                    last_blink_local = last_blink_utc.astimezone()
                    self.last_blink_label.setText(last_blink_local.strftime("%H:%M:%S"))
                except Exception:
                    # Fallback: show raw
                    self.last_blink_label.setText("--:--:--")

    def update_performance_display(self, perf_data: Dict):
        # Update CPU usage for this application
        cpu_percent = min(100, max(0, int(perf_data["cpu_percent"])))  # Clamp to 0-100
        self.cpu_progress.setValue(cpu_percent)
        self.cpu_label.setText(f"{cpu_percent}%")
        
        # Update Memory usage for this application
        memory_percent = min(100, max(0, int(perf_data["memory_percent"])))
        memory_mb = round(perf_data["memory_used_mb"], 1)
        self.memory_progress.setValue(memory_percent)
        self.memory_label.setText(f"{memory_mb} MB ({memory_percent:.1f}%)")
        
        # Update thread count
        num_threads = perf_data.get("num_threads", 0)
        self.threads_label.setText(str(num_threads))
        
        # Accumulate session metrics while tracking
        if self.eye_tracker and self.eye_tracker.is_running:
            self._session_cpu_sum += float(perf_data.get("cpu_percent") or 0.0)
            self._session_mem_sum += float(perf_data.get("memory_used_mb") or 0.0)
            self._session_metric_count += 1

    def load_my_sessions(self):
        if not (self.api and self.api.is_authed):
            return
        data = self.api.get_sessions(limit=50)
        self.sessions_table.setRowCount(0)
        for row in data:
            r = self.sessions_table.rowCount()
            self.sessions_table.insertRow(r)
            ended = row.get("ended_at_utc") or row.get("ended_at")
            self.sessions_table.setItem(r, 0, QTableWidgetItem(str(ended)))
            self.sessions_table.setItem(r, 1, QTableWidgetItem(row.get("client_session_id","-")))
            self.sessions_table.setItem(r, 2, QTableWidgetItem(str(row.get("total_blinks", 0))))
            self.sessions_table.setItem(r, 3, QTableWidgetItem(str(row.get("energy_impact") or "-")))

    def update_delete_button_style(self):
        """Apply theme-aware danger styling to delete account button."""
        try:
            if not hasattr(self, 'delete_account_btn'):
                return
            if self.current_theme == 'dark':
                self.delete_account_btn.setStyleSheet(
                    """
                    QPushButton { background:#2a1212; border:1px solid #612b2b; color:#ffb3b3; border-radius:8px; }
                    QPushButton:hover { background:#3a1818; border-color:#7a3a3a; }
                    QPushButton:pressed { background:#210d0d; }
                    QPushButton:disabled { background:#201516; color:#7d5d5d; border:1px solid #3a2626; }
                    """
                )
            else:
                self.delete_account_btn.setStyleSheet(
                    """
                    QPushButton { background:#ffe8e8; border:1px solid #d48787; color:#821e1e; border-radius:8px; }
                    QPushButton:hover { background:#ffd9d9; border-color:#c06060; }
                    QPushButton:pressed { background:#ffcccc; }
                    QPushButton:disabled { background:#f3e0e0; color:#b59a9a; border:1px solid #e2c5c5; }
                    """
                )
        except Exception:
            pass

    def delete_my_account(self):
        """Allow user to permanently delete their account and all data via backend self-delete endpoint."""
        if not (self.api and self.api.is_authed):
            self.status_bar.showMessage("Not authenticated; login first to delete account")
            return
        confirm = QMessageBox.question(
            self,
            "Delete My Data",
            "This will permanently delete your account and ALL associated data (sessions, blink samples).\nThis cannot be undone.\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        # Attempt deletion
        try:
            self.delete_account_btn.setEnabled(False)
            self.status_bar.showMessage("Deleting account…")
            # Stop tracking first
            try:
                if self.eye_tracker and self.eye_tracker.is_running:
                    self.eye_tracker.stop_tracking()
            except Exception:
                pass
            self.api.delete_my_account()
        except Exception as e:
            QMessageBox.critical(self, "Delete Failed", f"Could not delete account: {e}")
            self.delete_account_btn.setEnabled(True)
            self.status_bar.showMessage("Delete failed")
            return
        # Success: clear persisted auth, inform user, close app
        try:
            delete_saved_auth()
        except Exception:
            pass
        QMessageBox.information(self, "Account Deleted", "Your account and data have been deleted. The application will now exit.")
        QApplication.instance().quit()

    def sync_data(self):
        # With per-session uploads, samples are sent automatically on Stop Tracking.
        # This button now just refreshes status timestamps and indicates current auth state.
        self.last_sync_time = datetime.now()
        self.last_sync_label.setText(self.last_sync_time.strftime("%H:%M:%S"))
        if self.api and self.api.is_authed:
            self.sync_status_label.setText("Ready (sessions sync on stop)")
            self.sync_status_label.setStyleSheet("color: green;")
        else:
            self.sync_status_label.setText("Offline (session will be local-only)")
            self.sync_status_label.setStyleSheet("color: orange;")

    def show_settings(self):
        self.status_bar.showMessage("Settings dialog - coming soon!")

    def load_user_session(self):
        try:
            self.current_user = get_or_create_default_user()
        except Exception as e:
            print(f"Session load error: {e}")

    def closeEvent(self, event):
        if self.eye_tracker:
            self.eye_tracker.stop_tracking()
        if self.performance_monitor:
            self.performance_monitor.stop()
        event.accept()

    # --- Utility ---------------------------------------------------------
    def center_on_screen(self):
        """Center the main window on the primary screen."""
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(screen.center())
            self.move(frame.topLeft())
        except Exception:
            pass


class LoginDialog(QDialog):
    """Modern re-styled login dialog.

    Google sign-in temporarily disabled; related code kept commented for future restoration.
    Target design based on provided screenshot (dark background, stacked inputs, single primary button).
    """

    def __init__(self, default_base_url: str, parent=None, theme: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Login to WaW")
        self._token = None
        self._user = None
        self._base_url = default_base_url
        self.parent_window = parent
        self.setMinimumWidth(340)
        self._theme = (theme or self._load_theme_preference()).lower()

        # Set application icon
        set_app_icon(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 26, 32, 24)
        root.setSpacing(16)

        # Inputs
        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("E-mail")
        self.email_input.returnPressed.connect(lambda: self.pass_input.setFocus())
        self.pass_input = QLineEdit(self)
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.returnPressed.connect(self._on_login)
        root.addWidget(self.email_input)
        root.addWidget(self.pass_input)

        # Show password
        self.show_pass_cb = QCheckBox("Show password", self)
        self.show_pass_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_pass_cb.toggled.connect(self._toggle_password_visibility)
        root.addWidget(self.show_pass_cb)

        # Primary button
        self.login_btn = QPushButton("Sign In", self)
        self.login_btn.setObjectName("primaryButton")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setMinimumHeight(44)
        root.addWidget(self.login_btn)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        # Links
        links_container = QWidget(self)
        links_layout = QVBoxLayout(links_container)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(10)
        self.signup_label = QLabel("<span style='color:#aaa;'>Don't have an account?</span> <a href='signup' style='text-decoration:none; font-weight:600; color:#ffffff;'>Create an account</a>")
        self.signup_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.signup_label.setOpenExternalLinks(False)
        self.signup_label.linkActivated.connect(self._open_signup)
        self.forgot_label = QLabel("<a href='forgot' style='text-decoration:none; font-weight:600; color:#ffffff;'>Forgot password?</a>")
        self.forgot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.forgot_label.setOpenExternalLinks(False)
        self.forgot_label.linkActivated.connect(self._open_forgot)
        links_layout.addWidget(self.signup_label)
        links_layout.addWidget(self.forgot_label)
        root.addWidget(links_container)
        root.addStretch(1)

        # Actions
        self.login_btn.clicked.connect(self._on_login)
        self._apply_custom_style()
        QTimer.singleShot(0, self.center_on_screen)

    def _apply_custom_style(self):
        """Apply style (dark or light) and primary gradient button based on theme."""
        if self._theme == 'dark':
            style = """
            QDialog { background-color: #0f1114; }
            QLineEdit {\n                background: #181b20;\n                border: 1px solid #2d3136;\n                border-radius: 8px;\n                padding: 9px 12px;\n                color: #e6e8eb;\n                font-size: 13px;\n            }\n            QLineEdit:focus { border: 1px solid #295fa6; outline: none; }\n            QPushButton#primaryButton {\n                border: none; border-radius: 8px; font-weight: 600; font-size: 14px; color: #ffffff;\n                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0d47a1, stop:1 #0b3c91);\n            }\n            QPushButton#primaryButton:hover { background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #1560c6, stop:1 #104f9f); }\n            QPushButton#primaryButton:pressed { background: #0b3c91; }\n            QLabel#statusLabel { color: #7d8691; font-size: 11px; padding-left: 2px; }\n            QLabel { font-size: 12px; color:#d0d4d8; }\n            QLabel:hover { color: #dfe3e6; }\n            QCheckBox { color:#c5ccd3; background: transparent; spacing:6px; }\n            QCheckBox::indicator { width:16px; height:16px; border:1px solid #2d3136; border-radius:4px; background:#181b20; }\n            QCheckBox::indicator:hover { border-color:#295fa6; }\n            QCheckBox::indicator:checked { background: qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:1, stop:0 #0d47a1, stop:1 #0b3c91); border:1px solid #0d47a1; }\n            a { color: #ffffff; }\n            a:hover { text-decoration: underline; }\n            """
        else:
            style = """
            QDialog { background-color: #f5f6f8; }
            QLineEdit {\n                background: #ffffff; border: 1px solid #c5c9ce; border-radius: 8px; padding: 9px 12px; color: #222629; font-size: 13px;\n            }\n            QLineEdit:focus { border: 1px solid #1976d2; outline: none; }\n            QPushButton#primaryButton {\n                border: none; border-radius: 8px; font-weight: 600; font-size: 14px; color: #ffffff;\n                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #1976d2, stop:1 #1565c0);\n            }\n            QPushButton#primaryButton:hover { background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #1e82e4, stop:1 #1870cc); }\n            QPushButton#primaryButton:pressed { background: #1565c0; }\n            QLabel#statusLabel { color: #555f66; font-size: 11px; padding-left: 2px; }\n            QLabel { font-size: 12px; color:#222629; }\n            QCheckBox { color:#222629; background: transparent; spacing:6px; }\n            QCheckBox::indicator { width:16px; height:16px; border:1px solid #c5c9ce; border-radius:4px; background:#ffffff; }\n            QCheckBox::indicator:hover { border-color:#1976d2; }\n            QCheckBox::indicator:checked { background: qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:1, stop:0 #1976d2, stop:1 #1565c0); border:1px solid #1976d2; }\n            a { color: #1565c0; }\n            a:hover { text-decoration: underline; }\n            """
        self.setStyleSheet(style)
        # Adjust link label colors / HTML per theme
        try:
            if hasattr(self, 'signup_label') and hasattr(self, 'forgot_label'):
                if self._theme == 'light':
                    self.signup_label.setText("<span style='color:#555f66;'>Don't have an account?</span> <a href='signup' style='text-decoration:none; font-weight:600; color:#1565c0;'>Create an account</a>")
                    self.forgot_label.setText("<a href='forgot' style='text-decoration:none; font-weight:600; color:#1565c0;'>Forgot password?</a>")
                else:
                    self.signup_label.setText("<span style='color:#aaa;'>Don't have an account?</span> <a href='signup' style='text-decoration:none; font-weight:600; color:#ffffff;'>Create an account</a>")
                    self.forgot_label.setText("<a href='forgot' style='text-decoration:none; font-weight:600; color:#ffffff;'>Forgot password?</a>")
        except Exception:
            pass

    def _toggle_password_visibility(self, checked: bool):
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)

    def _on_login(self):
        email = self.email_input.text().strip()
        password = self.pass_input.text()
        base_url = (self._base_url or '').strip().rstrip('/')
        if not email or not password or not base_url:
            self.status_label.setText("All fields are required")
            return
        self.login_btn.setEnabled(False)
        self.status_label.setText("Connecting to server...")
        
        try:
            api = ApiClient(base_url)
            result = api.login(email=email, password=password)
            self._token = result.access_token
            self._user = result.user
            self._base_url = base_url
            self.status_label.setText("Login successful!")
            QTimer.singleShot(500, self.accept)  # Brief success message before closing
        except Exception as e:
            friendly_error = get_user_friendly_error(e, base_url)
            
            # Special handling for Render cold starts
            if 'render' in base_url.lower() and 'starting up' in friendly_error:
                self.status_label.setText(friendly_error)
                # Retry after a delay for Render cold starts
                QTimer.singleShot(3000, lambda: self._retry_login_after_wakeup(email, password, base_url))
                return
            
            self.status_label.setText(friendly_error)
            self.login_btn.setEnabled(True)

    def _retry_login_after_wakeup(self, email: str, password: str, base_url: str):
        """Retry login after server wake-up delay for Render cold starts."""
        self.status_label.setText("Retrying login...")
        try:
            api = ApiClient(base_url)
            result = api.login(email=email, password=password)
            self._token = result.access_token
            self._user = result.user
            self._base_url = base_url
            self.status_label.setText("Login successful!")
            QTimer.singleShot(500, self.accept)
        except Exception as e:
            friendly_error = get_user_friendly_error(e, base_url)
            if 'invalid credentials' in friendly_error.lower():
                self.status_label.setText("Invalid email or password")
            else:
                self.status_label.setText("Server still starting up. Please wait a moment and try again.")
            self.login_btn.setEnabled(True)

    # def _on_google(self):
    #     """Disabled Google sign-in placeholder. Restore when backend/client ready."""
    #     self.status_label.setText("Google sign-in currently disabled")

    def get_result(self):
        return self._base_url, self._token, self._user

    def _open_signup(self, *_):  # linkActivated passes href
        dlg = SignupDialog(default_base_url=self._base_url, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            base_url, token, user = dlg.get_result()
            self._base_url, self._token, self._user = base_url, token, user
            self.accept()

    def _open_forgot(self, *_):
        dlg = ForgotPasswordDialog(default_base_url=self._base_url, parent=self)
        dlg.exec()

    def center_on_screen(self):
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            self.adjustSize()
            frame = self.frameGeometry()
            frame.moveCenter(screen.center())
            self.move(frame.topLeft())
        except Exception:
            pass

    def _load_theme_preference(self):
        try:
            settings_path = Path("desktop_settings.json")
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                    return data.get('theme', 'light')
        except Exception:
            pass
        return 'light'


## AdvancedSettingsDialog removed


class SignupDialog(QDialog):
    def __init__(self, default_base_url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign Up")
        self._base_url = default_base_url
        self._token = None
        self._user = None
        self.setMinimumWidth(380)
        # Theme
        self._theme = self._load_theme_preference().lower()

        # Set application icon
        set_app_icon(self)

        layout = QFormLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        header = QLabel("Create Your Account")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        sub = QLabel("Enter email, verify OTP, set password")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#777; font-size:11px;")
        layout.addRow(header)
        layout.addRow(sub)

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Enter your email address")
        self.otp_input = QLineEdit(self)
        self.otp_input.setPlaceholderText("Enter OTP")
        self.otp_input.setMaxLength(6)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Set a password (min 8 chars)")
        self.password_confirm_input = QLineEdit(self)
        self.password_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_confirm_input.setPlaceholderText("Confirm password")
        self.show_pass_cb = QCheckBox("Show passwords", self)
        self.show_pass_cb.toggled.connect(self._toggle_pw_visibility)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color:#888;")

        self.send_btn = QPushButton("Send OTP", self)
        self.verify_btn = QPushButton("Verify & Register", self)
        self.cancel_btn = QPushButton("Cancel", self)
        # Make all buttons primary style per request
        for b in (self.send_btn, self.verify_btn, self.cancel_btn):
            b.setObjectName("primaryButton")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(30)
            b.setMinimumWidth(88)
        # Slightly wider for longer label
        self.verify_btn.setMinimumWidth(130)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setContentsMargins(0, 2, 0, 0)
        btn_row.addWidget(self.send_btn)
        btn_row.addWidget(self.verify_btn)
        btn_row.addWidget(self.cancel_btn)

        layout.addRow("Email", self.email_input)
        layout.addRow("OTP", self.otp_input)
        layout.addRow("Password", self.password_input)
        layout.addRow("Confirm Password", self.password_confirm_input)
        layout.addRow(self.show_pass_cb)
        layout.addRow(btn_row)
        layout.addRow(self.status_label)

        self.send_btn.clicked.connect(self._send)
        self.verify_btn.clicked.connect(self._verify)
        self.cancel_btn.clicked.connect(self.reject)

        self._apply_custom_style()

    def _toggle_pw_visibility(self, checked: bool):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.password_input.setEchoMode(mode)
        self.password_confirm_input.setEchoMode(mode)

    def _send(self):
        email = self.email_input.text().strip()
        base_url = (self._base_url or '').strip().rstrip('/')
        if not email or not base_url:
            self.status_label.setText("Enter email and server URL")
            return
        try:
            api = ApiClient(base_url)
            res = api.send_otp(email)
            debug_code = res.get('debug_code')
            if debug_code:
                self.status_label.setText(f"OTP sent (dev mode). Code: {debug_code}")
            else:
                self.status_label.setText("OTP sent to your email")
        except Exception as e:
            friendly_error = get_user_friendly_error(e, base_url)
            if 'already registered' in friendly_error:
                self.status_label.setText(friendly_error)
            else:
                self.status_label.setText(f"Failed to send OTP: {friendly_error}")

    def _verify(self):
        email = self.email_input.text().strip()
        code = self.otp_input.text().strip()
        base_url = (self._base_url or '').strip().rstrip('/')
        if not email or not code or not base_url:
            self.status_label.setText("Enter email, OTP, and server URL")
            return
        try:
            pw = self.password_input.text().strip()
            pw2 = self.password_confirm_input.text().strip()
            if pw or pw2:
                if len(pw) < 8:
                    self.status_label.setText("Password must be at least 8 characters")
                    return
                if pw != pw2:
                    self.status_label.setText("Passwords do not match")
                    return
            import requests
            api_body_pwd = pw if pw and pw == pw2 and len(pw) >= 8 else None
            resp = requests.post(
                f"{base_url}/v1/auth/verify-otp",
                json={"email": email, "code": code, "password": api_body_pwd},
                timeout=15,
            )
            if resp.status_code == 422 and api_body_pwd is not None:
                # Retry without password for legacy backend
                resp2 = requests.post(
                    f"{base_url}/v1/auth/verify-otp",
                    json={"email": email, "code": code},
                    timeout=15,
                )
                resp2.raise_for_status()
                data = resp2.json()
                if api_body_pwd:
                    tmp_api = ApiClient(base_url)
                    tmp_api.set_token(data["access_token"])
                    tmp_api.set_password(api_body_pwd)
                data_final = data
            else:
                resp.raise_for_status()
                data_final = resp.json()
            self._token = data_final["access_token"]
            self._user = data_final["user"]
            self.accept()
        except Exception as e:
            friendly_error = get_user_friendly_error(e, base_url)
            self.status_label.setText(f"Verification failed: {friendly_error}")

    # --- Theming helpers (Signup) ---
    def _apply_custom_style(self):
        if self._theme == 'dark':
            style = """
            QDialog { background:#0f1114; }
            QLabel { color:#d0d4d8; }
            QLineEdit { background:#181b20; border:1px solid #2d3136; border-radius:8px; padding:7px 10px; color:#e6e8eb; }
            QLineEdit:focus { border:1px solid #295fa6; }
            QPushButton#primaryButton { border:none; border-radius:7px; font-weight:600; font-size:12px; padding:4px 10px; color:#ffffff; height:30px; background:qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:0, stop:0 #0d47a1, stop:1 #0b3c91); }
            QPushButton#primaryButton:hover { background:qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:0, stop:0 #1560c6, stop:1 #104f9f); }
            QPushButton#primaryButton:pressed { background:#0b3c91; }
            QLabel[style*='color:#777'] { color:#7d8691 !important; }
            """
        else:
            style = """
            QDialog { background:#f5f6f8; }
            QLabel { color:#222629; }
            QLineEdit { background:#ffffff; border:1px solid #c5c9ce; border-radius:8px; padding:7px 10px; color:#222629; }
            QLineEdit:focus { border:1px solid #1976d2; }
            QPushButton#primaryButton { border:none; border-radius:7px; font-weight:600; font-size:12px; padding:4px 10px; color:#ffffff; height:30px; background:qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:0, stop:0 #1976d2, stop:1 #1565c0); }
            QPushButton#primaryButton:hover { background:qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:0, stop:0 #1e82e4, stop:1 #1870cc); }
            QPushButton#primaryButton:pressed { background:#1565c0; }
            QLabel[style*='color:#777'] { color:#555f66 !important; }
            """
        self.setStyleSheet(style)

    def _load_theme_preference(self):
        try:
            settings_path = Path("desktop_settings.json")
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                    return data.get('theme', 'light')
        except Exception:
            pass
        return 'light'

    def get_result(self):
        return self._base_url, self._token, self._user


class ForgotPasswordDialog(QDialog):
    def __init__(self, default_base_url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password")
        self._base_url = default_base_url
        self._email = None
        self.setMinimumWidth(360)
        self._theme = self._load_theme_preference().lower()

        # Set application icon
        set_app_icon(self)

        layout = QFormLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        header = QLabel("Reset Your Password")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        sub = QLabel("Request code, then set new password")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#777; font-size:11px;")
        layout.addRow(header)
        layout.addRow(sub)

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Registered email")
        self.code_input = QLineEdit(self)
        self.code_input.setPlaceholderText("Reset code")
        self.code_input.setMaxLength(6)
        self.new_pass_input = QLineEdit(self)
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_input.setPlaceholderText("New password (min 8 chars)")
        self.new_pass_confirm = QLineEdit(self)
        self.new_pass_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_confirm.setPlaceholderText("Confirm new password")

        self.status_label = QLabel("")

        self.request_btn = QPushButton("Send Code", self)
        self.reset_btn = QPushButton("Reset Password", self)
        self.reset_btn.setEnabled(False)
        self.close_btn = QPushButton("Close", self)
        for b in (self.request_btn, self.reset_btn, self.close_btn):
            b.setObjectName("primaryButton")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(30)
            b.setMinimumWidth(88)
        self.reset_btn.setMinimumWidth(120)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setContentsMargins(0, 2, 0, 0)
        btn_row.addWidget(self.request_btn)
        btn_row.addWidget(self.reset_btn)
        btn_row.addWidget(self.close_btn)

        layout.addRow("Email", self.email_input)
        layout.addRow("Code", self.code_input)
        layout.addRow("New Password", self.new_pass_input)
        layout.addRow("Confirm", self.new_pass_confirm)
        layout.addRow(btn_row)
        layout.addRow(self.status_label)

        self.request_btn.clicked.connect(self._send_code)
        self.reset_btn.clicked.connect(self._reset_password)
        self.close_btn.clicked.connect(self.reject)
        self._apply_custom_style()

    def _send_code(self):
        email = self.email_input.text().strip()
        base_url = (self._base_url or '').strip().rstrip('/')
        if not email or not base_url:
            self.status_label.setText("Enter email and server URL")
            return
        try:
            api = ApiClient(base_url)
            res = api.request_password_reset(email)
            dbg = res.get('debug_code')
            if dbg:
                self.status_label.setText(f"Code sent (dev={dbg})")
            else:
                self.status_label.setText("Code sent if email exists")
            self._email = email
            self.reset_btn.setEnabled(True)
            self.request_btn.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"Failed: {e}")

    def _reset_password(self):
        code = self.code_input.text().strip()
        pw = self.new_pass_input.text().strip()
        pw2 = self.new_pass_confirm.text().strip()
        base_url = (self._base_url or '').strip().rstrip('/')
        if not self._email or not code or not pw:
            self.status_label.setText("Fill all fields")
            return
        if len(pw) < 8:
            self.status_label.setText("Password too short")
            return
        if pw != pw2:
            self.status_label.setText("Passwords mismatch")
            return
        try:
            api = ApiClient(base_url)
            api.confirm_password_reset(self._email, code, pw)
            self.status_label.setText("Password reset. You can login now.")
            self.reset_btn.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"Reset failed: {e}")

    # --- Theming helpers (Forgot Password) ---
    def _apply_custom_style(self):
        if self._theme == 'dark':
            style = """
            QDialog { background:#0f1114; }
            QLabel { color:#d0d4d8; }
            QLineEdit { background:#181b20; border:1px solid #2d3136; border-radius:8px; padding:7px 10px; color:#e6e8eb; }
            QLineEdit:focus { border:1px solid #295fa6; }
            QPushButton#primaryButton { border:none; border-radius:7px; font-weight:600; font-size:12px; padding:4px 10px; color:#ffffff; height:30px; background:qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:0, stop:0 #0d47a1, stop:1 #0b3c91); }
            QPushButton#primaryButton:hover { background:qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:0, stop:0 #1560c6, stop:1 #104f9f); }
            QPushButton#primaryButton:pressed { background:#0b3c91; }
            QLabel[style*='color:#777'] { color:#7d8691 !important; }
            """
        else:
            style = """
            QDialog { background:#f5f6f8; }
            QLabel { color:#222629; }
            QLineEdit { background:#ffffff; border:1px solid #c5c9ce; border-radius:8px; padding:7px 10px; color:#222629; }
            QLineEdit:focus { border:1px solid #1976d2; }
            QPushButton#primaryButton { border:none; border-radius:7px; font-weight:600; font-size:12px; padding:4px 10px; color:#ffffff; height:30px; background:qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:0, stop:0 #1976d2, stop:1 #1565c0); }
            QPushButton#primaryButton:hover { background:qlineargradient(spread:pad, x1:0,y1:0,x2:1,y2:0, stop:0 #1e82e4, stop:1 #1870cc); }
            QPushButton#primaryButton:pressed { background:#1565c0; }
            QLabel[style*='color:#777'] { color:#555f66 !important; }
            """
        self.setStyleSheet(style)

    def _load_theme_preference(self):
        try:
            settings_path = Path("desktop_settings.json")
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                    return data.get('theme', 'light')
        except Exception:
            pass
        return 'light'


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Wellness at Work")
    app.setApplicationVersion(CONFIG.app_version)
    
    # Fix for Windows taskbar icon
    try:
        import ctypes
        from ctypes import wintypes
        # Tell Windows this is a distinct app (not python.exe)
        myappid = 'wellness.at.work.eyetracker.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        # Additional Windows taskbar fixes
        if hasattr(ctypes.windll, 'shell32'):
            # Force taskbar to refresh
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    
    # Set application icon
    app_icon = None
    try:
        icon_candidates = [
            project_root / 'assets' / 'app.ico',
            project_root / 'assets' / 'favicon.ico', 
            project_root / 'assets' / 'android-chrome-192x192.png',
        ]
        for candidate in icon_candidates:
            if candidate.exists():
                app_icon = QIcon(str(candidate))
                app.setWindowIcon(app_icon)
                break
    except Exception:
        pass

    # Attempt saved auth first
    initial_auth = None
    try:
        saved = load_saved_auth()
        if saved:
            base_url, token, user = saved
            api = ApiClient(base_url)
            api.set_token(token)
            if api.validate_token():
                initial_auth = (base_url, token, user)
            else:
                delete_saved_auth()
    except Exception:
        pass

    if not initial_auth:
        login = LoginDialog(default_base_url=CONFIG.api_base_url)
        if login.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        base_url, token, user = login.get_result()
        try:
            save_auth(base_url, token, user)
        except Exception:
            pass
        initial_auth = (base_url, token, user)

    window = WaWMainWindow(initial_auth=initial_auth)
    
    # Ensure taskbar icon is set
    if app_icon:
        window.setWindowIcon(app_icon)
    
    window.show()
    
    # Force taskbar icon update after window is shown
    def update_taskbar_icon():
        try:
            if app_icon:
                # Multiple attempts to set the icon
                window.setWindowIcon(app_icon)
                app.setWindowIcon(app_icon)
                
                # Try to force Windows taskbar refresh
                import ctypes
                import ctypes.wintypes
                hwnd = int(window.winId())
                
                # Constants for icon messages
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                
                # Try to load and set icon via Windows API
                icon_path = str(project_root / 'assets' / 'app.ico')
                if Path(icon_path).exists():
                    # Load icon using Windows API
                    hicon = ctypes.windll.user32.LoadImageW(
                        0, icon_path, 1, 0, 0, 0x00000010 | 0x00008000
                    )
                    if hicon:
                        # Set both small and large icons
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
                        
        except Exception as e:
            print(f"Icon update error: {e}")  # Debug info
    
    # Update icon after a brief delay to ensure window is fully initialized
    QTimer.singleShot(500, update_taskbar_icon)
    
    sys.exit(app.exec())

# --- Auth persistence helpers ---
AUTH_FILE = Path("desktop_auth.json")

def save_auth(base_url: str, token: str, user: dict):
    data = {
        "base_url": base_url,
        "token": token,
        "user": user,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(AUTH_FILE, 'w') as f:
        json.dump(data, f)

def load_saved_auth():
    if AUTH_FILE.exists():
        try:
            with open(AUTH_FILE, 'r') as f:
                data = json.load(f)
            return data.get("base_url"), data.get("token"), data.get("user") or {}
        except Exception:
            return None
    return None

def delete_saved_auth():
    try:
        if AUTH_FILE.exists():
            AUTH_FILE.unlink()
    except Exception:
        pass

if __name__ == "__main__":
    main()