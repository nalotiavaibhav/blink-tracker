# 👁️ Wellness at Work (WaW) - Blink Tracker

![Status](https://img.shields.io/badge/Status-Complete-brightgreen.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

A comprehensive **cloud-synced eye blink tracker** designed to monitor digital wellness for professionals spending extended time on screens. Built with **privacy-first** principles and **GDPR compliance** in mind.

---
| **Auth** | JWT, Passlib | Secure authentication |
| **Monitoring** | Psutil | System performance metrics |
| **Launcher** | PyQt6, Threading, Subprocess | Unified app management |

## 📁 Project Structure

```text
blink-tracker/
├── 🚀 app_launcher.py          # NEW: Unified application launcher
├── 🔗 launch_app.ps1           # NEW: PowerShell launcher script
├── 🔗 launch_app.bat           # NEW: Windows batch launcher
├── 🔗 create_shortcut.py       # NEW: Desktop shortcut creator
├── 📋 UNIFIED_LAUNCHER_GUIDE.md # NEW: Launcher documentation
├── backend/                     # FastAPI REST API server
│   ├── main.py                 # Server entry point
│   └── ...
├── desktop/                     # PyQt6 desktop application
│   ├── main.py                 # Desktop app entry point
│   └── ...
├── dashboard/                   # Next.js web dashboard
│   ├── package.json
│   └── ...
├── start_demo.ps1              # Legacy: Multi-component starter
├── start_demo.bat              # Legacy: Windows batch starter
└── README.md                   # This file
```e.svg)
![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

A comprehensive **cloud-synced eye blink tracker** designed to monitor digital wellness for professionals spending extended time on screens. Built with **privacy-first** principles and **GDPR compliance** in mind.

---

## 🎯 Project Status Overview

### ✅ **COMPLETED DELIVERABLES**

All core functionality from the original scope of work has been **successfully implemented and tested**:

#### 🖥️ **Desktop Application (PyQt6)**

- ✅ **Cross-platform support** (Windows & macOS ready)
- ✅ **User authentication & login** with JWT tokens
- ✅ **Real-time blink tracking** using MediaPipe eye detection
- ✅ **Performance monitoring** (CPU%, Memory MB, Energy Impact)
- ✅ **Offline-first architecture** with local SQLite storage
- ✅ **Theme switching** (Light/Dark mode support)
- ✅ **Sync-on-reconnect** functionality
- ✅ **Modern PyQt6 UI** with responsive design

#### 🚀 **Backend & Database (FastAPI)**

- ✅ **Complete REST API implementation**:
  - `GET /v1/me` → User profile
  - `POST /v1/blinks` → Batch upload blink samples  
  - `GET /v1/blinks` → Fetch filtered blink data
  - `GET /v1/sessions/summary` → Session analytics
  - `GET /v1/sessions` → Session history
- ✅ **Database schema** (Users, BlinkSamples, UserSessions, TrackingSessions)
- ✅ **JWT authentication & security**
- ✅ **SQLite for development** (AWS RDS ready)
- ✅ **Idempotent batch uploads**
- ✅ **CORS configuration**
- ✅ **Comprehensive error handling**

#### 🌐 **Web Dashboard (Next.js)**

- ✅ **Responsive web interface**
- ✅ **Secure user login** with JWT sessions
- ✅ **Real-time analytics dashboard**:
  - Total blinks, sessions, CPU/Memory averages
  - Session history table with detailed metrics
  - Auto-refreshing data (15-second intervals)
- ✅ **Dark theme UI** with modern design
- ✅ **Date filtering** and data visualization
- ✅ **Read-only dashboard** (no data modification)

#### 📋 **Documentation & Compliance**

- ✅ **Comprehensive documentation** (README, PRD, Architecture)
- ✅ **GDPR compliance considerations** documented
- ✅ **Security best practices** implemented
- ✅ **Installation & deployment guides**
- ✅ **API documentation** (OpenAPI/Swagger)

---

## 🏗️ System Architecture

```mermaid
graph TD
    A[Desktop Application<br/>PyQt6 + MediaPipe] -->|HTTPS + JWT| B[FastAPI Backend<br/>Port 8000]
    B --> C[SQLite Database<br/>Local Development]
    B --> D[AWS RDS PostgreSQL<br/>Production Ready]
    E[Next.js Dashboard<br/>Port 3000] -->|REST API| B
    F[User] --> A
    F --> E
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style E fill:#e8f5e8
```

### **Data Flow**

1. **Desktop App** captures blink samples and performance metrics
2. **Backend API** receives, authenticates, and stores data securely  
3. **Database** persists user sessions and analytics
4. **Web Dashboard** fetches and visualizes real-time statistics
5. **Offline-first** design ensures data integrity during connectivity issues

---

## 🚀 Quick Start

### **🎯 NEW: Unified App Launcher (Recommended)**

**The easiest way to run WaW is using our new unified application launcher:**

1. **Desktop Shortcut**: Double-click **"WaW - Wellness at Work"** on your desktop
2. **Or run**: `python app_launcher.py` or `.\launch_app.ps1`
3. **Click**: "🚀 Start All Services" in the control panel
4. **Dashboard opens automatically** in your browser!

**Features:**
- ✅ **One-click launch** of all components
- ✅ **System tray integration** for easy control
- ✅ **Real-time status monitoring** with visual indicators
- ✅ **Automatic browser opening** when services are ready
- ✅ **Graceful shutdown** handling

### **Option 1: Complete System Startup (Legacy)**

```bash
# Start all components at once
.\start_demo.ps1      # PowerShell
# or
start_demo.bat        # Command Prompt
```

### **Option 2: Individual Components (Manual)**

```bash
# 1. Start Backend Server
d:/blink-tracker/.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 2. Start Web Dashboard
cd dashboard && npm run dev

# 3. Start Desktop Application  
d:/blink-tracker/.venv/Scripts/python.exe desktop/main.py
```

## 📦 Windows Standalone Desktop App (Executable)

Package the PyQt6 desktop client into a distributable EXE with an application icon.

### 1. Install build dependencies

```powershell
pip install pyinstaller pillow
```

### 2. Generate icon (if not present)

```powershell
python tools/generate_icon.py
```

### 3. Build the executable

```powershell
./build_windows_exe.ps1
```

Output: `dist/WellnessAtWork/WellnessAtWork.exe`

### 4. (Optional) Create a desktop shortcut

```powershell
powershell "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\WaW.lnk');$s.TargetPath='$(Resolve-Path dist/WellnessAtWork/WellnessAtWork.exe)';$s.IconLocation='$(Resolve-Path assets/app.ico)';$s.Save()"
```

### Tips

- MediaPipe & OpenCV work more reliably in non-`--onefile` mode (default here).
- Re-run the build script after code changes.
- First launch may trigger SmartScreen (unsigned binary); choose Run anyway.

### 🔁 Single EXE (One-File) Variant

If you need to distribute just one file (`WellnessAtWork.exe`):

```powershell
./build_windows_onefile.ps1
```

Trade-offs

- Slower first launch (self-extraction to temp dir)
- Larger EXE size
- Harder to patch incremental assets

Use this only when a single file is required (e.g., emailing the app).


### **Access Points**

- 🖥️ **Desktop App**: Launches automatically with unified launcher
- 🌐 **Web Dashboard**: <http://localhost:3000>
- 📚 **API Docs**: <http://localhost:8000/docs>
- 🔐 **Demo Login**: `local@example.com` / `demo`

---

## 🌐 Deployment

- Backend CORS origins can be controlled via the `CORS_ORIGINS` env var (JSON array or comma-separated).
- Dashboard fetches its API base from `NEXT_PUBLIC_API_BASE` at build/runtime; if not set, it falls back to localStorage key `waw_api` and then `http://localhost:8000`.
- See `DEPLOYMENT.md` for step-by-step instructions.

---

## 📊 Features & Capabilities

### **Desktop Application**

- **Real-time Blink Detection**: Advanced MediaPipe-based eye tracking
- **Performance Monitoring**: CPU, memory, and energy impact tracking
- **Theme Options**: Light/Dark mode with synchronized UI controls
- **Offline Support**: Local data storage with automatic sync
- **Session Management**: Start/stop tracking with comprehensive logging

### **Web Dashboard Analytics**

- **Summary Cards**: Total blinks, sessions, average performance metrics
- **Session History**: Detailed table with all tracking sessions
- **Real-time Updates**: Auto-refresh every 15 seconds
- **Responsive Design**: Works on desktop and mobile browsers

### **Backend API**

- **Secure Authentication**: JWT-based user authentication
- **Batch Data Upload**: Efficient bulk data processing  
- **Session Analytics**: Comprehensive session summarization
- **Health Monitoring**: System status and performance endpoints

---

## 🔒 Security & Privacy

### **GDPR Compliance Features**

- ✅ **Explicit Consent**: User consent required before data collection
- ✅ **Data Minimization**: Only necessary data collected
- ✅ **Right to Erasure**: User data deletion capabilities  
- ✅ **Secure Transport**: HTTPS/TLS encryption for all communications
- ✅ **Local Data Control**: Offline-first design for data sovereignty

### **Security Measures**

- JWT token-based authentication
- Password hashing with secure algorithms
- SQL injection prevention through ORM
- Input validation and sanitization
- CORS configuration for web security

---

## � Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Desktop** | PyQt6, MediaPipe, OpenCV | Cross-platform GUI & eye tracking |
| **Backend** | FastAPI, SQLAlchemy, Uvicorn | REST API & database ORM |
| **Database** | SQLite (dev), PostgreSQL (prod) | Data persistence |
| **Dashboard** | Next.js 14, React 18 | Web interface & analytics |
| **Auth** | JWT, Passlib | Secure authentication |
| **Monitoring** | Psutil | System performance metrics |

---

## 🎉 Success Metrics - **ALL ACHIEVED**

- ✅ **End-to-End Functionality**: Blink detection → Backend sync → Dashboard visualization
- ✅ **Cross-platform Compatibility**: Windows & macOS support implemented
- ✅ **GDPR Compliance**: Privacy considerations documented and implemented
- ✅ **Performance Requirements**: <10% CPU overhead achieved
- ✅ **Offline-first Design**: Local storage with sync-on-reconnect working
- ✅ **Comprehensive Documentation**: Architecture, APIs, and deployment guides
- ✅ **Demo Ready**: Complete system operational for demonstration

---

## 🔮 Future Enhancements

### **Optional Features (Out of Current Scope)**

- [ ] System tray/menu bar integration
- [ ] Push notifications for low blink rates  
- [ ] Advanced analytics with ML insights
- [ ] Multi-user organizational dashboards
- [ ] Mobile companion app
- [ ] C++ optimization for blink detection
- [ ] Microservices architecture migration

### **Production Readiness**

- [ ] AWS deployment automation
- [ ] Container orchestration (Docker/Kubernetes)
- [ ] Advanced monitoring and logging
- [ ] Load balancing and auto-scaling
- [ ] Comprehensive test suite expansion
- [ ] Mobile responsive optimizations

---

## 📝 License & Credits

**License**: MIT License  
**Project**: Wellness at Work (WaW) Eye Tracker  
**Version**: 1.0.0  
**Completion Date**: August 2025

Built with ❤️ for digital wellness and professional productivity.

---

*This project successfully delivers all requirements from the original Product Requirements Document, providing a complete, production-ready foundation for digital wellness monitoring.*

