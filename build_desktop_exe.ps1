<#
Build Desktop Application EXE with Backend URL Configuration

This script builds a standalone Windows executable for the WaW Desktop Application
that connects to your specified backend server for data storage and sync.

Prerequisites:
  - Virtual environment activated with all dependencies installed
  - pip install pyinstaller pillow
  - Backend server running and accessible

Usage:
  # For local development backend
  powershell -ExecutionPolicy Bypass -File .\build_desktop_exe.ps1

  # For production backend
  powershell -ExecutionPolicy Bypass -File .\build_desktop_exe.ps1 -BackendUrl "https://your-backend-url.com"

  # Single file executable
  powershell -ExecutionPolicy Bypass -File .\build_desktop_exe.ps1 -BackendUrl "https://your-backend-url.com" -SingleFile

Output: 
  - Regular build: dist/WellnessAtWork/WellnessAtWork.exe
  - Single file build: dist/WellnessAtWork.exe
#>

param (
    [string]$BackendUrl = "https://waw-backend-a28q.onrender.com",
    [switch]$SingleFile = $false,
    [string]$AppName = "WellnessAtWork",
    [string]$AppVersion = "1.0.0"
)

$ErrorActionPreference = 'Stop'

Write-Host "========================================================"
Write-Host "Building WaW Desktop Application"
Write-Host "========================================================"
Write-Host "Backend URL: $BackendUrl"
Write-Host "Single File: $SingleFile"
Write-Host "App Name: $AppName"
Write-Host "App Version: $AppVersion"
Write-Host "========================================================"

# Validate backend URL format
if (-not ($BackendUrl -match "^https?://")) {
    Write-Error "Backend URL must start with http:// or https://"
    exit 1
}

# Create app_config.json for the build with backend URL
Write-Host "==> Creating app configuration with backend URL"
$config = @{
    apiBase = $BackendUrl
    appVersion = $AppVersion
    buildTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}
$configJson = $config | ConvertTo-Json -Depth 3
$configFile = "app_config.json"
Set-Content -Path $configFile -Value $configJson -Encoding UTF8
Write-Host "    Created app_config.json with backend URL: $BackendUrl"

# Generate icon if missing
Write-Host "==> Ensuring application icon exists"
if (-not (Test-Path "assets/app.ico")) {
    if (Test-Path "tools/generate_icon.py") {
        Write-Host "    Generating application icon..."
        python tools/generate_icon.py
    } else {
        Write-Warning "    Icon generator not found. Building without custom icon."
    }
}

# Find virtual environment site-packages
$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$venvSitePackages = Join-Path $scriptDir ".venv\Lib\site-packages"

if (-not (Test-Path $venvSitePackages)) {
    Write-Error "Virtual environment not found at '$venvSitePackages'. Please ensure you're in the project root and have activated the virtual environment."
    exit 1
}

Write-Host "==> Preparing PyInstaller configuration"

# Base PyInstaller arguments
$pyinstallerArgs = @(
    '--noconfirm'
    '--name', $AppName
    '--distpath', 'dist'
    '--workpath', 'build'
    '--specpath', '.'
)

# Single file or directory distribution
if ($SingleFile) {
    $pyinstallerArgs += '--onefile'
    Write-Host "    Building single-file executable"
} else {
    Write-Host "    Building directory distribution"
}

# Always use windowed mode (no console) for production builds
$pyinstallerArgs += '--windowed'

# Add icon if available
if (Test-Path "assets/app.ico") {
    $pyinstallerArgs += '--icon'
    $pyinstallerArgs += 'assets/app.ico'
    Write-Host "    Including application icon"
}

# Add data files
$pyinstallerArgs += '--add-data'
$pyinstallerArgs += 'assets;assets'
$pyinstallerArgs += '--add-data'
$pyinstallerArgs += 'app_config.json;.'
$pyinstallerArgs += '--add-data'
$pyinstallerArgs += 'desktop;desktop'
$pyinstallerArgs += '--add-data'
$pyinstallerArgs += 'shared;shared'
$pyinstallerArgs += '--add-data'
$pyinstallerArgs += 'backend;backend'

# Also copy main icon to root for easier Windows API access
if (Test-Path "assets/app.ico") {
    $pyinstallerArgs += '--add-data'
    $pyinstallerArgs += 'assets/app.ico;.'
}

# Hidden imports for required modules
$hiddenImports = @(
    'cv2',
    'mediapipe', 
    'psutil',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'requests',
    'json',
    'pathlib',
    'datetime',
    'uuid',
    'dotenv',
    'sqlite3',
    'matplotlib',
    'matplotlib.pyplot',
    'numpy',
    'sqlalchemy',
    'sqlalchemy.ext',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.orm',
    'sqlalchemy.sql',
    'sqlalchemy.engine',
    'desktop.eye_tracker',
    'shared.config',
    'shared.api',
    'shared.db',
    'backend.models'
)

foreach ($import in $hiddenImports) {
    $pyinstallerArgs += '--hidden-import'
    $pyinstallerArgs += $import
}

# Collect all necessary packages
$pyinstallerArgs += '--collect-all'
$pyinstallerArgs += 'mediapipe'
$pyinstallerArgs += '--collect-all'
$pyinstallerArgs += 'cv2'
$pyinstallerArgs += '--collect-all'
$pyinstallerArgs += 'matplotlib'
$pyinstallerArgs += '--collect-all'
$pyinstallerArgs += 'sqlalchemy'

# Find and include OpenSSL/cryptography binaries
Write-Host "==> Searching for required binaries"
$patterns = @('libcrypto*.dll', 'libssl*.dll', '*ssleay32*.dll', '*libeay32*.dll')
$found = @()

foreach ($pattern in $patterns) {
    $found += Get-ChildItem -Path $venvSitePackages -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue
}

# Check cryptography bindings directory
$cryptoBindings = Join-Path $venvSitePackages 'cryptography\hazmat\bindings'
if (Test-Path $cryptoBindings) {
    $cryptoFiles = Get-ChildItem -Path $cryptoBindings -File -Filter "*.pyd" -ErrorAction SilentlyContinue
    $found += $cryptoFiles
}

$found = $found | Sort-Object -Property Name -Unique

if ($found.Count -gt 0) {
    Write-Host "    Found $($found.Count) required binary files"
    foreach ($file in $found) {
        $pyinstallerArgs += '--add-binary'
        $pyinstallerArgs += "$($file.FullName);."
    }
} else {
    Write-Warning "    No OpenSSL/cryptography binaries found - TLS connections might not work"
}

# Exclude unnecessary modules to reduce size
$excludeModules = @(
    'tests',
    'pytest', 
    'unittest',
    'tkinter'
)

foreach ($module in $excludeModules) {
    $pyinstallerArgs += '--exclude-module'
    $pyinstallerArgs += $module
}

# Entry point
$pyinstallerArgs += 'desktop/main.py'

# Build the executable
Write-Host "==> Running PyInstaller (this may take several minutes)"
Write-Host "    Command: pyinstaller $($pyinstallerArgs -join ' ')"

try {
    & pyinstaller @pyinstallerArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================================"
        Write-Host "BUILD SUCCESSFUL!"
        Write-Host "========================================================"
        
        if ($SingleFile) {
            $outputPath = "dist\$AppName.exe"
            Write-Host "Single-file executable: $outputPath"
        } else {
            $outputPath = "dist\$AppName\$AppName.exe"
            Write-Host "Application directory: dist\$AppName\"
            Write-Host "Main executable: $outputPath"
        }
        
        if (Test-Path $outputPath) {
            $fileSize = (Get-Item $outputPath).Length / 1MB
            Write-Host "File size: $([math]::Round($fileSize, 2)) MB"
        }
        
        Write-Host ""
        Write-Host "Configuration:"
        Write-Host "  Backend URL: $BackendUrl"
        Write-Host "  App Version: $AppVersion"
        Write-Host ""
        Write-Host "The application will connect to your backend at $BackendUrl"
        Write-Host "for user authentication and data storage."
        Write-Host ""
        Write-Host "Note: If Windows SmartScreen appears, click 'More info' then 'Run anyway'"
        Write-Host "========================================================"
    } else {
        Write-Error "PyInstaller failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} catch {
    Write-Error "Build failed: $($_.Exception.Message)"
    exit 1
} finally {
    # Clean up temporary files
    Write-Host "==> Cleaning up temporary files"
    Remove-Item -Path $configFile -ErrorAction SilentlyContinue
    
    # Optionally clean up build artifacts
    # Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
    # Remove-Item -Path "*.spec" -Force -ErrorAction SilentlyContinue
}

Write-Host "==> Build process completed"
