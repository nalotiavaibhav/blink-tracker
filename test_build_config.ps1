<#
Test Build Configuration for WaW Desktop Application

This script validates that the build environment is properly configured
before running the main build script.
#>

param (
    [string]$BackendUrl = "http://localhost:8000"
)

$ErrorActionPreference = 'Stop'

Write-Host "========================================================"
Write-Host "Testing WaW Desktop Application Build Configuration"
Write-Host "========================================================"

$allGood = $true

# Test 1: Check Python environment
Write-Host "==> Testing Python environment"
try {
    $pythonVersion = python --version 2>&1
    Write-Host "    Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "    ERROR: Python not found or not in PATH" -ForegroundColor Red
    $allGood = $false
}

# Test 2: Check virtual environment
Write-Host "==> Testing virtual environment"
if (Test-Path ".venv") {
    Write-Host "    Virtual environment: Found" -ForegroundColor Green
    
    # Check if activated
    $pythonPath = (Get-Command python).Source
    if ($pythonPath -like "*\.venv\*") {
        Write-Host "    Virtual environment: Activated" -ForegroundColor Green
    } else {
        Write-Host "    WARNING: Virtual environment not activated" -ForegroundColor Yellow
        Write-Host "    Run: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    }
} else {
    Write-Host "    ERROR: Virtual environment not found" -ForegroundColor Red
    $allGood = $false
}

# Test 3: Check required packages
Write-Host "==> Testing required packages"
$requiredPackages = @(
    'pyinstaller',
    'PyQt6', 
    'opencv-python',
    'mediapipe',
    'psutil',
    'requests',
    'fastapi',
    'sqlalchemy'
)

foreach ($package in $requiredPackages) {
    try {
        $result = pip show $package 2>$null
        if ($result) {
            Write-Host "    $package`: Installed" -ForegroundColor Green
        } else {
            Write-Host "    $package`: NOT INSTALLED" -ForegroundColor Red
            $allGood = $false
        }
    } catch {
        Write-Host "    $package`: ERROR checking" -ForegroundColor Red
        $allGood = $false
    }
}

# Test 4: Check project structure
Write-Host "==> Testing project structure"
$requiredPaths = @(
    'desktop\main.py',
    'desktop\eye_tracker.py', 
    'backend\main.py',
    'shared\config.py',
    'shared\api.py',
    'assets',
    'requirements.txt'
)

foreach ($path in $requiredPaths) {
    if (Test-Path $path) {
        Write-Host "    $path`: Found" -ForegroundColor Green
    } else {
        Write-Host "    $path`: MISSING" -ForegroundColor Red
        $allGood = $false
    }
}

# Test 5: Check backend URL
Write-Host "==> Testing backend URL"
if ($BackendUrl -match "^https?://") {
    Write-Host "    Backend URL format: Valid ($BackendUrl)" -ForegroundColor Green
    
    # Try to connect to backend
    try {
        $response = Invoke-WebRequest -Uri "$BackendUrl/health" -TimeoutSec 5 -UseBasicParsing 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "    Backend connectivity: OK" -ForegroundColor Green
        } else {
            Write-Host "    Backend connectivity: Failed (Status: $($response.StatusCode))" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    Backend connectivity: Failed (Cannot connect)" -ForegroundColor Yellow
        Write-Host "    Note: This is OK if backend is not running yet" -ForegroundColor Gray
    }
} else {
    Write-Host "    Backend URL format: INVALID" -ForegroundColor Red
    $allGood = $false
}

# Test 6: Check build tools
Write-Host "==> Testing build tools"
try {
    $pyinstallerVersion = pyinstaller --version 2>&1
    Write-Host "    PyInstaller: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "    PyInstaller: NOT FOUND" -ForegroundColor Red
    $allGood = $false
}

# Test 7: Check for icon files
Write-Host "==> Testing assets"
if (Test-Path "assets\app.ico") {
    Write-Host "    Application icon: Found" -ForegroundColor Green
} else {
    if (Test-Path "tools\generate_icon.py") {
        Write-Host "    Application icon: Missing (can be generated)" -ForegroundColor Yellow
    } else {
        Write-Host "    Application icon: Missing (no generator)" -ForegroundColor Yellow
    }
}

# Test 8: Check disk space
Write-Host "==> Testing system resources"
$drive = Get-WmiObject -Class Win32_LogicalDisk | Where-Object { $_.DeviceID -eq (Get-Location).Drive.Name }
$freeSpaceGB = [math]::Round($drive.FreeSpace / 1GB, 2)
if ($freeSpaceGB -gt 2) {
    Write-Host "    Disk space: $freeSpaceGB GB available" -ForegroundColor Green
} else {
    Write-Host "    Disk space: $freeSpaceGB GB available (LOW)" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================================"
if ($allGood) {
    Write-Host "BUILD CONFIGURATION: READY ✓" -ForegroundColor Green
    Write-Host "You can proceed with building the executable:" -ForegroundColor Green
    Write-Host ".\build_desktop_exe.ps1 -BackendUrl `"$BackendUrl`"" -ForegroundColor Green
} else {
    Write-Host "BUILD CONFIGURATION: ISSUES FOUND ✗" -ForegroundColor Red
    Write-Host "Please fix the issues above before building." -ForegroundColor Red
}
Write-Host "========================================================"

# Return exit code
if ($allGood) { exit 0 } else { exit 1 }
