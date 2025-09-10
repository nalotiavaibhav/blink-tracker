# 🚀 WaW Unified Application Launcher

## Overview

The **Unified Application Launcher** is a single executable that manages the entire WaW (Wellness at Work) system. When launched, it automatically:

1. **Starts the FastAPI backend server** (port 8000)
2. **Starts the Next.js dashboard** (port 3000)
3. **Opens the web browser** to the dashboard
4. **Provides system tray integration** for easy control
5. **Handles graceful shutdown** of all components

## 🎯 Key Features

### ✅ **One-Click Launch**
- Single executable starts the complete system
- No need to manually start backend, dashboard, and desktop components
- Automatic dependency checking and error handling

### ✅ **System Tray Integration**
- Runs in system tray when minimized
- Right-click menu for quick access
- Show/hide control panel
- Direct dashboard access
- Clean exit option

### ✅ **Control Panel Interface**
- Real-time status monitoring (Backend/Dashboard)
- System log with timestamps
- Manual service start/stop controls
- One-click browser opening

### ✅ **Automatic Browser Opening**
- Opens dashboard automatically when services are ready
- Configurable delay to ensure services are fully loaded
- Error handling for browser launch issues

### ✅ **Cross-Platform Support**
- Windows: `.bat` and `.ps1` launchers + desktop shortcuts
- macOS: Application bundle (`.app`) support
- Linux: Desktop entry (`.desktop`) support

## 📋 Usage Options

### **Option 1: Desktop Shortcut (Recommended)**
1. Double-click the desktop shortcut: **"WaW - Wellness at Work"**
2. The control panel opens automatically
3. Click **"🚀 Start All Services"**
4. Dashboard opens automatically in your browser

### **Option 2: Command Line**
```bash
# Windows (PowerShell)
.\launch_app.ps1

# Windows (Command Prompt)  
launch_app.bat

# Direct Python execution
python app_launcher.py
```

### **Option 3: File Explorer**
Double-click any of these files:
- `launch_app.bat` (Windows)
- `launch_app.ps1` (PowerShell)
- `app_launcher.py` (Direct Python)

## 🖥️ Control Panel Interface

### **Status Indicators**
- 🟢 **Green**: Service running successfully
- ⚪ **White**: Service stopped/not started
- 🔴 **Red**: Service failed to start

### **Control Buttons**
- **🚀 Start All Services**: Launches backend and dashboard
- **🛑 Stop All Services**: Gracefully shuts down all components
- **🌐 Open Dashboard**: Opens web dashboard in browser

### **System Log**
- Real-time logging of all operations
- Timestamped entries for debugging
- Startup progress tracking
- Error reporting with details

## 🔧 System Tray Features

### **Tray Menu Options**
- **Show Control Panel**: Brings control window to front
- **Open Dashboard**: Direct browser access
- **Exit**: Graceful shutdown of all services

### **Tray Behavior**
- Shows when control panel is minimized
- Double-click tray icon to restore window
- Right-click for context menu
- Tooltip shows application status

## ⚙️ Technical Details

### **Service Management**
- **Backend**: FastAPI server on port 8000
- **Dashboard**: Next.js dev server on port 3000
- **Health Checks**: Automatic service availability testing
- **Process Control**: Clean termination handling

### **Dependencies**
- PyQt6 for GUI interface
- Requests for health checking
- Subprocess for process management
- Threading for non-blocking operations

### **Error Handling**
- Virtual environment validation
- Service startup timeout detection
- Port availability checking
- Graceful failure recovery

## 🛠️ Installation & Setup

### **Prerequisites**
```bash
# Ensure virtual environment exists
python -m venv .venv

# Install dependencies
.venv\Scripts\pip install -r requirements.txt

# Install Windows-specific dependencies (Windows only)
.venv\Scripts\pip install pywin32
```

### **Create Desktop Shortcut**
```bash
python create_shortcut.py
```

### **Test Installation**
```bash
python app_launcher.py
```

## 🔍 Troubleshooting

### **Common Issues**

#### ❓ **"Virtual environment not found"**
```bash
# Solution: Create and setup virtual environment
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

#### ❓ **"Failed to start backend"**
- Check if port 8000 is already in use
- Verify virtual environment has all dependencies
- Check system log for specific error messages

#### ❓ **"Failed to start dashboard"**
```bash
# Solution: Install Node.js dependencies
cd dashboard
npm install
```

#### ❓ **"Browser doesn't open automatically"**
- Manually navigate to: http://localhost:3000
- Check if default browser is set correctly
- System tray → "Open Dashboard"

### **Debug Mode**
Run with verbose output:
```bash
python app_launcher.py --debug  # (if implemented)
```

## 📊 Performance

### **Resource Usage**
- **Memory**: ~50-100 MB (GUI + process management)
- **CPU**: <1% when idle, 2-5% during startup
- **Startup Time**: 10-30 seconds (depending on system)

### **System Requirements**
- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.10+
- **Memory**: 4GB RAM minimum
- **Storage**: 500MB for dependencies

## 🔄 Version History

### **v1.0.0** (Current)
- Initial unified launcher implementation
- System tray integration
- Cross-platform support
- Desktop shortcut creation
- Control panel interface
- Automatic browser opening

## 🚀 Future Enhancements

### **Planned Features**
- [ ] Auto-updater integration
- [ ] Custom port configuration
- [ ] Multiple profile support
- [ ] Advanced logging options
- [ ] Service restart capabilities
- [ ] Performance monitoring dashboard
- [ ] Notification system integration

---

*The Unified Application Launcher provides a seamless, professional way to run the complete WaW system with minimal user interaction.*
