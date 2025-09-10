<#
Simple Production Build Script - No Console Window
#>

param (
    [string]$BackendUrl = "http://localhost:8000",
    [switch]$SingleFile = $false
)

$ErrorActionPreference = 'Stop'

Write-Host "Building WaW Desktop App (No Console)"
Write-Host "Backend URL: $BackendUrl"
Write-Host "Single File: $SingleFile"

# Create config
$config = @{
    apiBase = $BackendUrl
    appVersion = "1.0.0"
    buildTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}

$configJson = $config | ConvertTo-Json
Set-Content -Path "app_config.json" -Value $configJson -Encoding UTF8

Write-Host "Running PyInstaller..."

# Build command
$cmd = @(
    'pyinstaller'
    '--noconfirm'
    '--windowed'
    '--name'
    'WellnessAtWork'
    '--paths'
    '.'
    '--add-data'
    'assets;assets'
    '--add-data'
    'app_config.json;.'
    '--add-data'
    'desktop;desktop'
    '--add-data'
    'shared;shared'
    '--add-data'
    'backend;backend'
    '--hidden-import'
    'desktop'
    '--hidden-import'
    'desktop.eye_tracker'
    '--hidden-import'
    'shared.config'
    '--hidden-import'
    'shared.api'
    '--hidden-import'
    'shared.db'
    '--hidden-import'
    'backend.models'
    '--hidden-import'
    'cv2'
    '--hidden-import'
    'mediapipe'
    '--hidden-import'
    'psutil'
    '--hidden-import'
    'PyQt6'
    '--hidden-import'
    'requests'
    '--collect-all'
    'mediapipe'
    '--collect-all'
    'cv2'
)

if ($SingleFile) {
    $cmd += '--onefile'
    Write-Host "Building single file..."
} else {
    Write-Host "Building directory..."
}

if (Test-Path "assets/app.ico") {
    $cmd += '--icon'
    $cmd += 'assets/app.ico'
}

$cmd += 'desktop/main.py'

# Execute build
& $cmd[0] $cmd[1..$cmd.Length]

# Cleanup
Remove-Item -Path "app_config.json" -ErrorAction SilentlyContinue

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "BUILD SUCCESSFUL!"
    if ($SingleFile) {
        Write-Host "Executable: dist\WellnessAtWork.exe"
    } else {
        Write-Host "Executable: dist\WellnessAtWork\WellnessAtWork.exe"
    }
    Write-Host "No console window will appear."
} else {
    Write-Host "Build failed!"
}
