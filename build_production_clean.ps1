<#
Production Build Script for WaW Desktop Application (No Console)
This script builds a clean production version without console window.
#>

param (
    [string]$BackendUrl = "http://localhost:8000",
    [switch]$SingleFile = $false,
    [string]$AppName = "WellnessAtWork"
)

$ErrorActionPreference = 'Stop'

Write-Host "========================================================"
Write-Host "Building WaW Desktop App - Production Version"
Write-Host "========================================================"
Write-Host "Backend URL: $BackendUrl"
Write-Host "Single File: $SingleFile"
Write-Host "App Name: $AppName"
Write-Host "This version will NOT show console window"
Write-Host "========================================================"

# Create app_config.json
$config = @{
    apiBase = $BackendUrl
    appVersion = "1.0.0"
    buildTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}
$configJson = $config | ConvertTo-Json -Depth 3
Set-Content -Path "app_config.json" -Value $configJson -Encoding UTF8

Write-Host "==> Building production executable (no console)"

# Base arguments
$args = @(
    '--noconfirm',
    '--name', $AppName,
    '--windowed'
)

# Single file or directory
if ($SingleFile) {
    $args += '--onefile'
    Write-Host "    Building single-file executable"
} else {
    Write-Host "    Building directory distribution"
}

# Icon
if (Test-Path "assets/app.ico") {
    $args += '--icon', 'assets/app.ico'
}

# Add all data and modules
$args += @(
    '--paths', '.',
    '--add-data', 'assets;assets',
    '--add-data', 'app_config.json;.',
    '--add-data', 'desktop;desktop',
    '--add-data', 'shared;shared',
    '--add-data', 'backend;backend'
)

# Hidden imports for all modules
$hiddenImports = @(
    'desktop',
    'desktop.main',
    'desktop.eye_tracker',
    'shared',
    'shared.config',
    'shared.api',
    'shared.db',
    'shared.google_oauth',
    'backend',
    'backend.models',
    'backend.main',
    'backend.emailer',
    'cv2',
    'mediapipe',
    'psutil',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'requests',
    'sqlite3',
    'dotenv',
    'pathlib',
    'json',
    'datetime',
    'uuid',
    'typing',
    'dataclasses'
)

foreach ($import in $hiddenImports) {
    $args += '--hidden-import', $import
}

# Collect packages
$args += @(
    '--collect-all', 'mediapipe',
    '--collect-all', 'cv2'
)

# Exclude unnecessary modules
$args += @(
    '--exclude-module', 'tests',
    '--exclude-module', 'pytest',
    '--exclude-module', 'unittest',
    '--exclude-module', 'tkinter'
)

# Entry point
$args += 'desktop/main.py'

try {
    Write-Host "==> Running PyInstaller..."
    & pyinstaller @args

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================================"
        Write-Host "PRODUCTION BUILD SUCCESSFUL!"
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
        Write-Host "✓ No console window will appear"
        Write-Host "✓ Application starts directly in GUI mode" 
        Write-Host "✓ Backend URL: $BackendUrl"
        Write-Host ""
        Write-Host "To test the application:"
        if ($SingleFile) {
            Write-Host "  .\dist\$AppName.exe"
        } else {
            Write-Host "  .\dist\$AppName\$AppName.exe"
        }
        Write-Host "========================================================"
    } else {
        Write-Error "Build failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Error "Build error: $($_.Exception.Message)"
} finally {
    Remove-Item -Path "app_config.json" -ErrorAction SilentlyContinue
}
