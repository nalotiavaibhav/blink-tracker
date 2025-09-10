# Building WaW Desktop Application EXE

This guide explains how to build a standalone Windows executable (.exe) for the Wellness at Work desktop application that connects to your backend server.

## Prerequisites

1. **Python Environment**
   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows PowerShell
   # or
   .venv\Scripts\activate.bat    # Windows Command Prompt
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Backend Server**
   - Your WaW backend server must be running and accessible
   - Note the backend URL (e.g., `http://localhost:8000` or `https://api.yourcompany.com`)

## Quick Build

### Method 1: Using the Enhanced Build Script (Recommended)

```powershell
# For local development backend
.\build_desktop_exe.ps1

# For production backend
.\build_desktop_exe.ps1 -BackendUrl "https://api.yourcompany.com"

# For single-file executable
.\build_desktop_exe.ps1 -BackendUrl "https://api.yourcompany.com" -SingleFile
```

### Method 2: Using PyInstaller Directly

```powershell
# Create app configuration
echo '{"apiBase": "https://api.yourcompany.com"}' > app_config.json

# Build with PyInstaller
pyinstaller WellnessAtWork.spec
```

## Build Script Options

The `build_desktop_exe.ps1` script supports several parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-BackendUrl` | Backend server URL | `http://localhost:8000` |
| `-SingleFile` | Create single .exe file | `false` (directory) |
| `-AppName` | Application name | `WellnessAtWork` |
| `-AppVersion` | Version number | `1.0.0` |

### Examples

```powershell
# Local development
.\build_desktop_exe.ps1

# Production with custom name
.\build_desktop_exe.ps1 -BackendUrl "https://waw-api.company.com" -AppName "CompanyWaW" -AppVersion "2.1.0"

# Single file for distribution
.\build_desktop_exe.ps1 -BackendUrl "https://api.company.com" -SingleFile
```

## Configuration

### Backend URL Configuration

The desktop application needs to know where your backend server is running. You can configure this in several ways:

1. **Build-time Configuration (Recommended)**
   ```powershell
   .\build_desktop_exe.ps1 -BackendUrl "https://your-backend-url.com"
   ```

2. **app_config.json File**
   ```json
   {
     "apiBase": "https://your-backend-url.com",
     "appVersion": "1.0.0"
   }
   ```

3. **Environment Variables**
   ```bash
   set API_BASE_URL=https://your-backend-url.com
   ```

### Backend Server Requirements

Your backend server must:

- Be running the WaW backend application (FastAPI)
- Be accessible from the client machines
- Support HTTPS for production deployments
- Have CORS configured to allow desktop client requests

### Example Backend URLs

```
Development:    http://localhost:8000
Production:     https://api.yourcompany.com
Docker:         http://localhost:8010
AWS:           https://your-app.amazonaws.com
```

## Output

### Directory Build (Default)
```
dist/
└── WellnessAtWork/
    ├── WellnessAtWork.exe    # Main executable
    ├── assets/               # Application assets
    ├── app_config.json       # Configuration file
    └── [various DLLs and dependencies]
```

### Single File Build
```
dist/
└── WellnessAtWork.exe        # Standalone executable
```

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   ```bash
   # Ensure all dependencies are installed
   pip install -r requirements.txt
   
   # Check virtual environment is activated
   where python
   ```

2. **Backend connection fails**
   - Verify backend URL is correct and accessible
   - Check firewall/network settings
   - Ensure backend server is running

3. **Missing DLLs**
   ```bash
   # Install Visual C++ Redistributable
   # Or use --collect-all flag in PyInstaller
   ```

4. **Large file size**
   ```bash
   # Use single file build with UPX compression
   .\build_desktop_exe.ps1 -SingleFile
   ```

### Windows SmartScreen Warning

When running the .exe for the first time, Windows may show a SmartScreen warning:

1. Click "More info"
2. Click "Run anyway"

This is normal for unsigned executables.

## Testing the Build

1. **Run the executable**
   ```
   dist\WellnessAtWork\WellnessAtWork.exe
   ```

2. **Verify backend connection**
   - Application should show login screen
   - Test login with valid credentials
   - Check that data syncs to backend

3. **Test core functionality**
   - Eye tracking should start/stop
   - Data should appear in "My Data" tab
   - Performance metrics should update

## Deployment

### For End Users

1. **Distribute the executable**
   - Send the entire `dist/WellnessAtWork/` folder, or
   - Send the single `WellnessAtWork.exe` file

2. **User Instructions**
   ```
   1. Download and extract the application
   2. Run WellnessAtWork.exe
   3. Log in with your credentials
   4. Allow camera access when prompted
   5. Click "Start Tracking" to begin
   ```

### For IT Deployment

1. **Silent installation**
   - Copy to `C:\Program Files\WellnessAtWork\`
   - Create desktop shortcuts
   - Configure enterprise backend URL

2. **Group Policy**
   - Deploy via GPO software installation
   - Configure firewall rules for backend access

## Advanced Configuration

### Custom Icons

```powershell
# Generate application icon
python tools/generate_icon.py

# Or replace assets/app.ico with your icon
```

### Environment-Specific Builds

```powershell
# Development
.\build_desktop_exe.ps1 -BackendUrl "http://localhost:8000" -AppName "WaW-Dev"

# Staging  
.\build_desktop_exe.ps1 -BackendUrl "https://staging-api.company.com" -AppName "WaW-Staging"

# Production
.\build_desktop_exe.ps1 -BackendUrl "https://api.company.com" -AppName "WellnessAtWork"
```

### Build Automation

Create a batch script for automated builds:

```batch
@echo off
echo Building WaW Desktop Application...

call .venv\Scripts\activate.bat

powershell -ExecutionPolicy Bypass -File build_desktop_exe.ps1 -BackendUrl "%BACKEND_URL%" -SingleFile

echo Build complete!
pause
```

## Security Considerations

1. **HTTPS in Production**
   - Always use HTTPS for production backend URLs
   - Obtain proper SSL certificates

2. **Code Signing**
   - Consider signing the executable for enterprise deployment
   - Reduces Windows SmartScreen warnings

3. **Backend Authentication**
   - Ensure backend has proper authentication
   - Use strong passwords and MFA where possible

## Support

For issues with:
- **Building**: Check Python environment and dependencies
- **Backend Connection**: Verify URL and server status  
- **Functionality**: Check camera permissions and firewall settings

## Files Created

After running the build script, these files are created/modified:

- `app_config.json` - Backend URL configuration (temporary)
- `dist/` - Output directory with executable
- `build/` - PyInstaller build cache
- `WellnessAtWork.spec` - PyInstaller specification file
