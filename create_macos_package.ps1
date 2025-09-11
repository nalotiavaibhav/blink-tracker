# Create macOS Build Package
param([string]$BackendUrl = "https://waw-backend-a28q.onrender.com")

Write-Host "Creating macOS Build Package..." -ForegroundColor Blue

# Create build directory
$BuildDir = "macos_build_package"
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
New-Item -ItemType Directory -Path $BuildDir | Out-Null

# Copy essential directories
$Dirs = @("desktop", "shared", "backend", "assets")
foreach ($dir in $Dirs) {
    if (Test-Path $dir) {
        Copy-Item -Recurse -Path $dir -Destination "$BuildDir/$dir"
        Write-Host "Copied $dir/" -ForegroundColor Green
    }
}

# Copy essential files  
$Files = @("requirements.txt", "requirements.backend.txt", "build_macos_app.sh", "convert_icon_for_macos.py")
foreach ($file in $Files) {
    if (Test-Path $file) {
        Copy-Item -Path $file -Destination "$BuildDir/$file"
        Write-Host "Copied $file" -ForegroundColor Green
    }
}

# Create app config
$Config = @{
    api_base_url = $BackendUrl
    app_version = "1.0.0"  
    device_id = $env:COMPUTERNAME
}
$Config | ConvertTo-Json | Set-Content -Path "$BuildDir/app_config.json"
Write-Host "Created app_config.json" -ForegroundColor Green

# Create instructions file
"# macOS Build Instructions

## Prerequisites (on MacBook)
1. Install Homebrew: https://brew.sh
2. Install Python: brew install python@3.11  
3. Install create-dmg: brew install create-dmg

## Build Steps
1. Copy this folder to your MacBook
2. Open Terminal and navigate to this folder
3. Run: chmod +x build_macos_app.sh
4. Run: ./build_macos_app.sh

## What Gets Created
- WellnessAtWork.app (application bundle)
- WellnessAtWork-1.0.0.dmg (installer package)

## Testing
1. Double-click the DMG file to mount it
2. Drag WellnessAtWork.app to Applications folder
3. Launch from Applications (may need right-click -> Open first time)

Backend URL: $BackendUrl
Created: $(Get-Date)
" | Out-File -FilePath "$BuildDir/INSTRUCTIONS.txt" -Encoding UTF8

Write-Host "Created INSTRUCTIONS.txt" -ForegroundColor Green

Write-Host ""
Write-Host "Package Location: $BuildDir/" -ForegroundColor Yellow
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Copy '$BuildDir' folder to your MacBook" -ForegroundColor White  
Write-Host "2. Follow INSTRUCTIONS.txt on macOS" -ForegroundColor White
Write-Host ""
Write-Host "macOS build package ready!" -ForegroundColor Green
