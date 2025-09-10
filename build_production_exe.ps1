<#
Build a single-file (one EXE) Windows distribution of the WaW Desktop App for production.
This script packages the application to communicate with a specified backend URL.

Prerequisites:
  pip install pyinstaller pillow

Usage:
  powershell -ExecutionPolicy Bypass -File .\\build_production_exe.ps1 -backendUrl "https://your-backend-url.com"

Output: dist/WellnessAtWork.exe
#>
param (
    [string]$backendUrl = "http://localhost:8010"
)

$ErrorActionPreference = 'Stop'

Write-Host "==> Using backend URL: $backendUrl"

# Create a temporary app_config.json for the build
$config = @{
    apiBase = $backendUrl
    # Add other production config values here if needed
}
$configJson = $config | ConvertTo-Json
$configFile = "app_config.json"
Set-Content -Path $configFile -Value $configJson -Encoding UTF8

Write-Host "==> Ensuring icon exists"
if (-not (Test-Path assets/app.ico)) {
    python tools/generate_icon.py
}

# Find OpenSSL DLLs from the venv to avoid system conflicts
$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$venvSitePackages = Join-Path $scriptDir ".venv\Lib\site-packages"

if (-not (Test-Path $venvSitePackages)) {
  Write-Error "Could not find the .venv site-packages at '$venvSitePackages'. Make sure the script is in the project root and the venv is named .venv"
  exit 1
}

Write-Host "==> Searching for OpenSSL DLLs in '$venvSitePackages'..."
# look for common OpenSSL DLL name patterns
$patterns = @('libcrypto*.dll','libssl*.dll','*ssleay32*.dll','*libeay32*.dll','openssl*.dll')
$found = @()
foreach ($p in $patterns) {
  $found += Get-ChildItem -Path $venvSitePackages -Recurse -File -Filter $p -ErrorAction SilentlyContinue
}

# check cryptography wheel bindings dir as well (common location)
$cryptoBindings = Join-Path $venvSitePackages 'cryptography\hazmat\bindings'
if (Test-Path $cryptoBindings) {
  $found += Get-ChildItem -Path $cryptoBindings -File -ErrorAction SilentlyContinue
}

$found = $found | Sort-Object -Property Name -Unique
if ($found.Count -eq 0) {
  Write-Error "Could not find OpenSSL-related DLLs in venv site-packages. Build cannot continue."
  exit 1
}

# pick best matches for crypto and ssl
$libcrypto = $found | Where-Object { $_.Name -match 'crypto' } | Select-Object -First 1
$libssl = $found | Where-Object { $_.Name -match '(^libssl|ssl)' } | Select-Object -First 1

# fallback: if one of them wasn't found, try to use other entries
if (-not $libcrypto) { $libcrypto = $found | Select-Object -First 1 }
if (-not $libssl) { $libssl = $found | Where-Object { $_.FullName -ne $libcrypto.FullName } | Select-Object -First 1 }

Write-Host "==> Found OpenSSL candidates:"
if ($libcrypto) { Write-Host "    libcrypto: $($libcrypto.FullName)" }
if ($libssl)    { Write-Host "    libssl:    $($libssl.FullName)" }

# Optional: reduce size a bit by excluding test modules
$excludes = @(
  'tests',
  'pytest',
  'unittest'
) | ForEach-Object { '--exclude-module', $_ }

Write-Host "==> Building single-file executable (this can take several minutes)"
  try {
  $args = @(
    '--noconfirm',
    '--onefile',
    '--windowed',
    '--name', 'WellnessAtWork',
    # include icon only if it exists (avoid PyInstaller failure when missing)
  )

  if (Test-Path 'assets/app.ico') {
    $args += '--icon'; $args += 'assets/app.ico'
  } else {
    Write-Host "Warning: assets/app.ico not found — building without custom icon. To add one, run: python tools/generate_icon.py"
  }
    '--add-data', 'assets;assets',
    '--add-data', 'app_config.json;.'
  )

  # prepare binaries and data to include
  $binaries = @()
  $datas = @()

  if ($libcrypto) { $binaries += "$($libcrypto.FullName);." }
  if ($libssl)    { $binaries += "$($libssl.FullName);." }

  # Fallback: if OpenSSL DLLs not found, try bundling Qt6's DLLs and the qopensslbackend plugin
  if (-not $libcrypto -or -not $libssl) {
    Write-Host "==> OpenSSL DLLs not found; falling back to bundling Qt6 binaries and TLS plugin if available"
    $qtBin = Get-ChildItem -Path $venvSitePackages -Recurse -Directory | Where-Object { $_.FullName -match "PyQt6.*\\Qt6\\bin" } | Select-Object -First 1
    if ($qtBin) {
      $qtBinPath = $qtBin.FullName
      Write-Host "==> Including Qt6 bin DLLs from: $qtBinPath"
      $qtDlls = Get-ChildItem -Path $qtBinPath -Filter '*.dll' -File -ErrorAction SilentlyContinue
      foreach ($d in $qtDlls) { $binaries += "$($d.FullName);." }

      # include TLS plugin folder if present
      $tlsPlugin = Join-Path $qtBinPath "..\plugins\tls"
      $tlsPlugin = (Get-Item $tlsPlugin -ErrorAction SilentlyContinue).FullName 2>$null
      if ($tlsPlugin -and (Test-Path $tlsPlugin)) {
        Write-Host "==> Including TLS plugin: $tlsPlugin"
        # copy as data so the Qt plugin loader can find it
        $datas += "$tlsPlugin;PyQt6\Qt6\plugins\tls"
      }
    }
  }

  $args += @(
    '--hidden-import', 'cv2',
    '--hidden-import', 'mediapipe',
    '--hidden-import', 'psutil',
    '--hidden-import', 'PyQt6'
  )

  # add collect flags
  $args += '--collect-all'; $args += 'mediapipe'
  $args += '--collect-all'; $args += 'cv2'

  # append dynamically found data and binaries
  foreach ($d in $datas) { $args += '--add-data'; $args += $d }
  foreach ($b in $binaries) { $args += '--add-binary'; $args += $b }

  # append exclude modules
  $args += $excludes

  # finally the entry point
  $args += 'desktop/main.py'

  Write-Host "PyInstaller command args:`n  $($args -join ' `n  ')"
  & pyinstaller $args
}
finally {
  # Clean up the temporary config file
  Remove-Item -Path $configFile -ErrorAction SilentlyContinue
  Write-Host "==> Cleaned up temporary config file."
}

Write-Host "==> Single-file build complete: dist/WellnessAtWork.exe"
Write-Host "Tip: If SmartScreen warns, choose 'More info' -> 'Run anyway'."
