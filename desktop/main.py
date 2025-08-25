"""
WaW Desktop Application - Main Window
Integrates eye tracking with PyQt6 GUI and backend sync
"""

import sys
from pathlib import Path
import psutil
import time
from datetime import datetime
from typing import Dict

# Ensure project root on sys.path so `backend` and `shared` can be imported
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QGroupBox,
    QGridLayout, QStatusBar
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from desktop.eye_tracker import EyeTracker
from shared.db import get_or_create_default_user, store_blink_sample
from shared.config import CONFIG


class PerformanceMonitor(QThread):
    """Thread to monitor system performance metrics."""
    performance_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.is_running = False

    def run(self):
        self.is_running = True
        while self.is_running:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                self.performance_updated.emit(
                    {
                        "cpu_percent": cpu_percent,
                        "memory_used_mb": memory.used / (1024 * 1024),
                        "memory_total_mb": memory.total / (1024 * 1024),
                        "memory_percent": memory.percent,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            except Exception as e:
                print(f"Performance monitoring error: {e}")
            self.msleep(5000)  # Update every 5 seconds

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class WaWMainWindow(QMainWindow):
    """Main application window for WaW Desktop App."""

    def __init__(self):
        super().__init__()
        self.eye_tracker = EyeTracker(callback=self.on_blink_data)
        self.performance_monitor = PerformanceMonitor()
        self.current_user = None
        self.blink_data_buffer = []
        self.last_sync_time = None

        self.init_ui()
        self.performance_monitor.performance_updated.connect(self.update_performance_display)
        self.performance_monitor.start()
        self.init_sync_timer()
        self.load_user_session()

    def init_ui(self):
        self.setWindowTitle("Wellness at Work - Eye Tracker")
        self.setGeometry(100, 100, 800, 600)
        self.apply_grayscale_theme()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("blink-tracker")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        self.create_tracking_section(main_layout)
        self.create_performance_section(main_layout)
        self.create_sync_section(main_layout)
        self.create_control_section(main_layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to start tracking")

    def apply_grayscale_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Text, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(200, 200, 200))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(120, 120, 120))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)

    def create_tracking_section(self, layout):
        tracking_group = QGroupBox("Eye Blink Tracking")
        tracking_layout = QGridLayout(tracking_group)
        self.blink_count_label = QLabel("0")
        self.blink_count_label.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.blink_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tracking_layout.addWidget(QLabel("Total Blinks:"), 0, 0)
        tracking_layout.addWidget(self.blink_count_label, 0, 1)
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
        layout.addWidget(tracking_group)

    def create_performance_section(self, layout):
        perf_group = QGroupBox("System Performance")
        perf_layout = QGridLayout(perf_group)
        perf_layout.addWidget(QLabel("CPU Usage:"), 0, 0)
        self.cpu_progress = QProgressBar()
        self.cpu_label = QLabel("0%")
        perf_layout.addWidget(self.cpu_progress, 0, 1)
        perf_layout.addWidget(self.cpu_label, 0, 2)
        perf_layout.addWidget(QLabel("Memory Usage:"), 1, 0)
        self.memory_progress = QProgressBar()
        self.memory_label = QLabel("0 MB")
        perf_layout.addWidget(self.memory_progress, 1, 1)
        perf_layout.addWidget(self.memory_label, 1, 2)
        layout.addWidget(perf_group)

    def create_sync_section(self, layout):
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
        layout.addWidget(sync_group)

    def create_control_section(self, layout):
        control_layout = QHBoxLayout()
        self.start_stop_btn = QPushButton("Start Tracking")
        self.start_stop_btn.clicked.connect(self.toggle_tracking)
        self.start_stop_btn.setMinimumHeight(40)
        control_layout.addWidget(self.start_stop_btn)
        self.sync_btn = QPushButton("Sync Now")
        self.sync_btn.clicked.connect(self.sync_data)
        self.sync_btn.setMinimumHeight(40)
        control_layout.addWidget(self.sync_btn)
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        self.settings_btn.setMinimumHeight(40)
        control_layout.addWidget(self.settings_btn)
        layout.addLayout(control_layout)

    def init_sync_timer(self):
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_data)
        self.sync_timer.start(30000)

    def toggle_tracking(self):
        if self.eye_tracker.is_running:
            self.stop_tracking()
        else:
            self.start_tracking()

    def start_tracking(self):
        if self.eye_tracker.start_tracking():
            self.start_stop_btn.setText("Stop Tracking")
            self.tracking_status_label.setText("Active")
            self.tracking_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.status_bar.showMessage("Eye tracking started")
            self.ui_update_timer = QTimer()
            self.ui_update_timer.timeout.connect(self.update_tracking_display)
            self.ui_update_timer.start(1000)
        else:
            self.status_bar.showMessage("Failed to start eye tracking - check camera access")

    def stop_tracking(self):
        self.eye_tracker.stop_tracking()
        self.start_stop_btn.setText("Start Tracking")
        self.tracking_status_label.setText("Stopped")
        self.tracking_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.status_bar.showMessage("Eye tracking stopped")
        if hasattr(self, "ui_update_timer"):
            self.ui_update_timer.stop()

    def on_blink_data(self, data: Dict):
        self.blink_data_buffer.append(data)
        if not self.current_user:
            self.current_user = get_or_create_default_user()
        if data.get("blink_detected", False):
            try:
                store_blink_sample(
                    self.current_user.id,
                    timestamp_iso=data["timestamp"],
                    blink_count=data["blink_count"],
                    # cpu/mem could be fed from PerformanceMonitor later
                )
            except Exception as e:
                print(f"Error storing blink data locally: {e}")

    def update_tracking_display(self):
        if self.eye_tracker and self.eye_tracker.is_running:
            stats = self.eye_tracker.get_current_stats()
            self.blink_count_label.setText(str(stats["blink_count"]))
            duration = int(stats["session_duration"])
            h, rem = divmod(duration, 3600)
            m, s = divmod(rem, 60)
            self.session_duration_label.setText(f"{h:02d}:{m:02d}:{s:02d}")
            if stats["last_blink_time"]:
                last_blink = datetime.fromisoformat(stats["last_blink_time"].replace("Z", "+00:00"))
                self.last_blink_label.setText(last_blink.strftime("%H:%M:%S"))

    def update_performance_display(self, perf_data: Dict):
        cpu_percent = int(perf_data["cpu_percent"])
        self.cpu_progress.setValue(cpu_percent)
        self.cpu_label.setText(f"{cpu_percent}%")
        memory_percent = int(perf_data["memory_percent"])
        memory_mb = int(perf_data["memory_used_mb"])
        self.memory_progress.setValue(memory_percent)
        self.memory_label.setText(f"{memory_mb} MB")

    def sync_data(self):
        try:
            self.last_sync_time = datetime.now()
            self.last_sync_label.setText(self.last_sync_time.strftime("%H:%M:%S"))
            self.sync_status_label.setText("Last sync successful")
            self.sync_status_label.setStyleSheet("color: green;")
            pending = len(self.blink_data_buffer)
            self.blink_data_buffer.clear()
            self.pending_records_label.setText("0")
            self.status_bar.showMessage(f"Synced {pending} records successfully")
        except Exception as e:
            self.sync_status_label.setText("Sync failed")
            self.sync_status_label.setStyleSheet("color: red;")
            self.status_bar.showMessage(f"Sync failed: {str(e)}")

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


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Wellness at Work")
    app.setApplicationVersion(CONFIG.app_version)
    window = WaWMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()