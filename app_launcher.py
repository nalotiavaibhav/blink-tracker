#!/usr/bin/env python3
"""
Wellness at Work (WaW) - Unified Application Launcher
====================================================

A unified launcher that starts the complete WaW system:
- FastAPI Backend Server (port 8000)
- Next.js Web Dashboard (port 3000)
- Automatic browser opening
- System tray integration
- Graceful shutdown handling

Usage: python app_launcher.py
"""

import sys
import os
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional, List
import psutil
import requests

try:
    from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                               QMessageBox, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QHBoxLayout)
    from PyQt6.QtCore import QTimer, pyqtSignal, QObject, QThread
    from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction
except ImportError:
    print("❌ PyQt6 not found. Installing required dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
    from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                               QMessageBox, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QHBoxLayout)
    from PyQt6.QtCore import QTimer, pyqtSignal, QObject, QThread
    from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction


class ProcessManager(QObject):
    """Manages backend, dashboard, and desktop processes"""
    
    status_updated = pyqtSignal(str, str)  # component, status
    log_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.backend_process: Optional[subprocess.Popen] = None
        self.dashboard_process: Optional[subprocess.Popen] = None
        self.desktop_process: Optional[subprocess.Popen] = None
        self.project_root = Path(__file__).parent
        self.python_exe = self.project_root / ".venv" / "Scripts" / "python.exe"
        
    def start_backend(self) -> bool:
        """Start the FastAPI backend server"""
        try:
            self.log_updated.emit("🚀 Starting FastAPI backend server...")
            
            if not self.python_exe.exists():
                self.log_updated.emit("❌ Python virtual environment not found!")
                return False
                
            # Start backend server
            cmd = [
                str(self.python_exe),
                "-m", "uvicorn", "backend.main:app",
                "--reload", "--host", "0.0.0.0", "--port", "8000"
            ]
            
            self.backend_process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # Wait for backend to be ready
            if self._wait_for_service("http://localhost:8000/docs", "Backend"):
                self.status_updated.emit("backend", "running")
                self.log_updated.emit("✅ FastAPI backend is running on http://localhost:8000")
                return True
            else:
                self.status_updated.emit("backend", "failed")
                return False
                
        except Exception as e:
            self.log_updated.emit(f"❌ Failed to start backend: {str(e)}")
            self.status_updated.emit("backend", "failed")
            return False
    
    def start_dashboard(self) -> bool:
        """Start the Next.js dashboard"""
        try:
            self.log_updated.emit("🌐 Starting Next.js dashboard...")
            
            dashboard_path = self.project_root / "dashboard"
            if not dashboard_path.exists():
                self.log_updated.emit("❌ Dashboard directory not found!")
                return False
            
            # Check if package.json exists
            package_json = dashboard_path / "package.json"
            if not package_json.exists():
                self.log_updated.emit("❌ package.json not found in dashboard directory!")
                return False
            
            # Check if node_modules exists
            node_modules = dashboard_path / "node_modules"
            if not node_modules.exists():
                self.log_updated.emit("📦 Installing dashboard dependencies...")
                install_process = subprocess.run(
                    ["npm", "install"],
                    cwd=str(dashboard_path),
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if install_process.returncode != 0:
                    self.log_updated.emit(f"❌ npm install failed with return code: {install_process.returncode}")
                    self.log_updated.emit(f"📋 npm install stderr: {install_process.stderr}")
                    self.log_updated.emit(f"📋 npm install stdout: {install_process.stdout}")
                    return False
                else:
                    self.log_updated.emit("✅ Dashboard dependencies installed successfully")
            
            # Start Next.js development server
            self.log_updated.emit(f"📁 Starting dashboard from: {dashboard_path}")
            
            # Use shell=True for Windows compatibility with npm
            self.dashboard_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(dashboard_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # Also capture any immediate startup errors
            self.log_updated.emit("⏳ Waiting for dashboard to start...")
            time.sleep(3)  # Give it a moment to start
            
            # Check if process is still running
            if self.dashboard_process.poll() is not None:
                # Process has already terminated, capture the output
                stdout, stderr = self.dashboard_process.communicate()
                self.log_updated.emit(f"❌ Dashboard process exited early:")
                self.log_updated.emit(f"📋 Stdout: {stdout}")
                if stderr:
                    self.log_updated.emit(f"📋 Stderr: {stderr}")
                self.status_updated.emit("dashboard", "failed")
                return False
            
            # Wait for dashboard to be ready
            if self._wait_for_service("http://localhost:3000", "Dashboard", timeout=60):
                self.status_updated.emit("dashboard", "running")
                self.log_updated.emit("✅ Next.js dashboard is running on http://localhost:3000")
                return True
            else:
                self.status_updated.emit("dashboard", "failed")
                return False
                
        except Exception as e:
            self.log_updated.emit(f"❌ Failed to start dashboard: {str(e)}")
            self.status_updated.emit("dashboard", "failed")
            return False
    
    def start_desktop(self) -> bool:
        """Start the PyQt6 desktop application"""
        try:
            self.log_updated.emit("🖥️ Starting desktop application...")
            
            if not self.python_exe.exists():
                self.log_updated.emit("❌ Python virtual environment not found!")
                return False
                
            desktop_script = self.project_root / "desktop" / "main.py"
            if not desktop_script.exists():
                self.log_updated.emit("❌ Desktop application script not found!")
                return False
                
            # Start desktop application
            cmd = [str(self.python_exe), str(desktop_script)]
            
            self.desktop_process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # Give desktop app time to start
            time.sleep(2)
            
            # Check if process is still running (not crashed immediately)
            if self.desktop_process.poll() is None:
                self.status_updated.emit("desktop", "running")
                self.log_updated.emit("✅ Desktop application is running")
                return True
            else:
                self.status_updated.emit("desktop", "failed")
                self.log_updated.emit("❌ Desktop application failed to start")
                return False
                
        except Exception as e:
            self.log_updated.emit(f"❌ Failed to start desktop application: {str(e)}")
            self.status_updated.emit("desktop", "failed")
            return False
    
    def _wait_for_service(self, url: str, service_name: str, timeout: int = 30) -> bool:
        """Wait for a service to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code < 500:  # Accept any non-server-error response
                    return True
            except requests.exceptions.RequestException:
                pass
            
            self.log_updated.emit(f"⏳ Waiting for {service_name} to start...")
            time.sleep(2)
        
        self.log_updated.emit(f"⏰ Timeout waiting for {service_name}")
        return False
    
    def stop_all(self):
        """Stop all running processes"""
        self.log_updated.emit("🛑 Shutting down all services...")
        
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
                self.log_updated.emit("✅ Backend server stopped")
            except:
                self.backend_process.kill()
                self.log_updated.emit("⚠️ Backend server force killed")
            finally:
                self.backend_process = None
                self.status_updated.emit("backend", "stopped")
        
        if self.dashboard_process:
            try:
                self.dashboard_process.terminate()
                self.dashboard_process.wait(timeout=5)
                self.log_updated.emit("✅ Dashboard server stopped")
            except:
                self.dashboard_process.kill()
                self.log_updated.emit("⚠️ Dashboard server force killed")
            finally:
                self.dashboard_process = None
                self.status_updated.emit("dashboard", "stopped")
        
        if self.desktop_process:
            try:
                self.desktop_process.terminate()
                self.desktop_process.wait(timeout=5)
                self.log_updated.emit("✅ Desktop application stopped")
            except:
                self.desktop_process.kill()
                self.log_updated.emit("⚠️ Desktop application force killed")
            finally:
                self.desktop_process = None
                self.status_updated.emit("desktop", "stopped")


class StartupWorker(QThread):
    """Worker thread for starting services"""
    
    finished = pyqtSignal(bool)
    
    def __init__(self, process_manager: ProcessManager):
        super().__init__()
        self.process_manager = process_manager
    
    def run(self):
        # Start backend first
        backend_success = self.process_manager.start_backend()
        if not backend_success:
            self.finished.emit(False)
            return
        
        # Start dashboard
        dashboard_success = self.process_manager.start_dashboard()
        if not dashboard_success:
            self.finished.emit(False)
            return
        
        # Start desktop application (optional - don't fail if this doesn't work)
        desktop_success = self.process_manager.start_desktop()
        if not desktop_success:
            self.process_manager.log_updated.emit("⚠️ Desktop application failed to start (continuing anyway)")
        
        # Success if backend and dashboard are running
        self.finished.emit(backend_success and dashboard_success)


class ControlWindow(QWidget):
    """Main control window for the application"""
    
    def __init__(self, process_manager: ProcessManager):
        super().__init__()
        self.process_manager = process_manager
        self.init_ui()
        
        # Connect signals
        self.process_manager.status_updated.connect(self.update_status)
        self.process_manager.log_updated.connect(self.add_log)
        
    def init_ui(self):
        self.setWindowTitle("🏥 WaW - Wellness at Work Control Panel")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("👁️ Wellness at Work (WaW)")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(header)
        
        subtitle = QLabel("Unified Application Launcher")
        subtitle.setFont(QFont("Arial", 10))
        layout.addWidget(subtitle)
        
        # Status section
        status_layout = QHBoxLayout()
        
        self.backend_status = QLabel("⚪ Backend: Stopped")
        self.dashboard_status = QLabel("⚪ Dashboard: Stopped")
        self.desktop_status = QLabel("⚪ Desktop: Stopped")
        
        status_layout.addWidget(self.backend_status)
        status_layout.addWidget(self.dashboard_status)
        status_layout.addWidget(self.desktop_status)
        layout.addLayout(status_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Start All Services")
        self.start_btn.clicked.connect(self.start_services)
        
        self.stop_btn = QPushButton("🛑 Stop All Services")
        self.stop_btn.clicked.connect(self.stop_services)
        self.stop_btn.setEnabled(False)
        
        self.browser_btn = QPushButton("🌐 Open Dashboard")
        self.browser_btn.clicked.connect(self.open_dashboard)
        self.browser_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.browser_btn)
        layout.addLayout(button_layout)
        
        # Log area
        log_label = QLabel("📋 System Log:")
        layout.addWidget(log_label)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(250)
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
        
        # Add initial log message
        self.add_log("🎯 WaW Application Launcher Ready")
        self.add_log("💡 Click 'Start All Services' to begin")
        
    def update_status(self, component: str, status: str):
        """Update component status display"""
        status_icons = {
            "running": "🟢",
            "stopped": "⚪", 
            "failed": "🔴"
        }
        
        icon = status_icons.get(status, "⚪")
        status_text = status.title()
        
        if component == "backend":
            self.backend_status.setText(f"{icon} Backend: {status_text}")
        elif component == "dashboard":
            self.dashboard_status.setText(f"{icon} Dashboard: {status_text}")
        elif component == "desktop":
            self.desktop_status.setText(f"{icon} Desktop: {status_text}")
            
        # Enable/disable buttons based on status
        all_running = ("🟢" in self.backend_status.text() and 
                      "🟢" in self.dashboard_status.text())
        
        self.start_btn.setEnabled(not all_running)
        self.stop_btn.setEnabled(all_running)
        self.browser_btn.setEnabled(all_running)
        
    def add_log(self, message: str):
        """Add message to log area"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")
        
    def start_services(self):
        """Start all services in background thread"""
        self.start_btn.setEnabled(False)
        self.add_log("🔄 Starting services...")
        
        self.startup_worker = StartupWorker(self.process_manager)
        self.startup_worker.finished.connect(self.on_startup_finished)
        self.startup_worker.start()
        
    def on_startup_finished(self, success: bool):
        """Handle startup completion"""
        if success:
            self.add_log("✅ All services started successfully!")
            # Automatically open dashboard
            QTimer.singleShot(2000, self.open_dashboard)  # Open after 2 seconds
        else:
            self.add_log("❌ Failed to start some services")
            self.start_btn.setEnabled(True)
            
    def stop_services(self):
        """Stop all services"""
        self.process_manager.stop_all()
        
    def open_dashboard(self):
        """Open the web dashboard in default browser"""
        try:
            webbrowser.open("http://localhost:3000")
            self.add_log("🌐 Opening dashboard in browser...")
        except Exception as e:
            self.add_log(f"❌ Failed to open browser: {str(e)}")
            
    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(
            self, "Confirm Exit",
            "Are you sure you want to exit?\n\nThis will stop all running services.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.process_manager.stop_all()
            event.accept()
        else:
            event.ignore()


class WaWApplication(QApplication):
    """Main application with system tray support"""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        self.process_manager = ProcessManager()
        self.control_window = ControlWindow(self.process_manager)
        
        # System tray setup
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.setup_system_tray()
        
        # Show control window
        self.control_window.show()
        
    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Control Panel", self)
        show_action.triggered.connect(self.show_control_panel)
        tray_menu.addAction(show_action)
        
        dashboard_action = QAction("Open Dashboard", self)
        dashboard_action.triggered.connect(self.control_window.open_dashboard)
        tray_menu.addAction(dashboard_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # Set tray icon (using a simple colored circle as placeholder)
        pixmap = QPixmap(16, 16)
        pixmap.fill(self.palette().color(self.palette().ColorRole.Highlight))
        self.tray_icon.setIcon(QIcon(pixmap))
        
        self.tray_icon.setToolTip("WaW - Wellness at Work")
        self.tray_icon.show()
        
        # Handle tray icon clicks
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
    def tray_icon_activated(self, reason):
        """Handle system tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_control_panel()
            
    def show_control_panel(self):
        """Show the control panel window"""
        self.control_window.show()
        self.control_window.raise_()
        self.control_window.activateWindow()
        
    def quit_application(self):
        """Quit the application"""
        self.process_manager.stop_all()
        self.quit()


def main():
    """Main application entry point"""
    app = WaWApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("WaW - Wellness at Work")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("WaW Team")
    
    # Handle application exit
    app.aboutToQuit.connect(app.process_manager.stop_all)
    
    print("🎯 Starting WaW - Wellness at Work Application Launcher")
    print("💡 The control panel will open shortly...")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
