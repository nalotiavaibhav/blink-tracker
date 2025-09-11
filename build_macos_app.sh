#!/bin/bash

# macOS Application Builder for Wellness at Work
# Creates .app bundle and DMG package for distribution

set -e  # Exit on any error

echo "🍎 Building Wellness at Work for macOS"
echo "======================================"

# Configuration
APP_NAME="WellnessAtWork"
VERSION="1.0.0"
BACKEND_URL="${1:-https://waw-backend-a28q.onrender.com}"
BUILD_DIR="build_macos"
DIST_DIR="dist_macos"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script must be run on macOS"
    echo "Current OS: $OSTYPE"
    exit 1
fi

print_status "Checking system requirements..."

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "not found")
if [[ "$python_version" == "not found" ]]; then
    print_error "Python 3 not found. Please install Python 3.8 or later."
    exit 1
fi

print_success "Python version: $python_version"

# Check if virtual environment exists and activate it
if [[ -d ".venv" ]]; then
    print_status "Activating virtual environment..."
    source .venv/bin/activate
    print_success "Virtual environment activated"
else
    print_warning "No virtual environment found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    print_success "Virtual environment created and activated"
fi

# Install/upgrade build dependencies
print_status "Installing build dependencies..."
pip install --upgrade pip
pip install pyinstaller pillow

# Install project dependencies
if [[ -f "requirements.txt" ]]; then
    print_status "Installing project dependencies..."
    pip install -r requirements.txt
    print_success "Project dependencies installed"
fi

# Create app configuration
print_status "Creating application configuration..."
cat > app_config.json << EOF
{
    "api_base_url": "$BACKEND_URL",
    "app_version": "$VERSION",
    "device_id": "$(hostname)"
}
EOF
print_success "Configuration created with backend URL: $BACKEND_URL"

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf "$BUILD_DIR" "$DIST_DIR" "*.spec"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# Prepare icon (convert if needed)
print_status "Preparing application icon..."
if [[ -f "assets/app.ico" ]]; then
    # Convert ICO to ICNS if needed (requires iconutil on macOS)
    if [[ ! -f "assets/app.icns" ]]; then
        print_status "Converting icon from ICO to ICNS format..."
        # Create temporary iconset
        mkdir -p assets/app.iconset
        
        # Use sips to convert (built-in macOS tool)
        sips -z 16 16 assets/app.ico --out assets/app.iconset/icon_16x16.png 2>/dev/null || true
        sips -z 32 32 assets/app.ico --out assets/app.iconset/icon_16x16@2x.png 2>/dev/null || true
        sips -z 32 32 assets/app.ico --out assets/app.iconset/icon_32x32.png 2>/dev/null || true
        sips -z 64 64 assets/app.ico --out assets/app.iconset/icon_32x32@2x.png 2>/dev/null || true
        sips -z 128 128 assets/app.ico --out assets/app.iconset/icon_128x128.png 2>/dev/null || true
        sips -z 256 256 assets/app.ico --out assets/app.iconset/icon_128x128@2x.png 2>/dev/null || true
        sips -z 256 256 assets/app.ico --out assets/app.iconset/icon_256x256.png 2>/dev/null || true
        sips -z 512 512 assets/app.ico --out assets/app.iconset/icon_256x256@2x.png 2>/dev/null || true
        sips -z 512 512 assets/app.ico --out assets/app.iconset/icon_512x512.png 2>/dev/null || true
        sips -z 1024 1024 assets/app.ico --out assets/app.iconset/icon_512x512@2x.png 2>/dev/null || true
        
        # Convert to ICNS
        iconutil -c icns assets/app.iconset -o assets/app.icns 2>/dev/null || {
            print_warning "Could not create ICNS icon, using ICO format"
            cp assets/app.ico assets/app.icns
        }
        
        # Cleanup
        rm -rf assets/app.iconset
        print_success "Icon converted to ICNS format"
    fi
    ICON_PATH="assets/app.icns"
else
    print_warning "No icon found at assets/app.ico"
    ICON_PATH=""
fi

# Build PyInstaller command
print_status "Building macOS application..."

PYINSTALLER_ARGS=(
    --name "$APP_NAME"
    --windowed
    --onedir
    --distpath "$DIST_DIR"
    --workpath "$BUILD_DIR"
    --specpath "."
)

# Add icon if available
if [[ -n "$ICON_PATH" ]]; then
    PYINSTALLER_ARGS+=(--icon "$ICON_PATH")
fi

# Add data files
PYINSTALLER_ARGS+=(
    --add-data "assets:assets"
    --add-data "app_config.json:."
    --add-data "desktop:desktop"
    --add-data "shared:shared" 
    --add-data "backend:backend"
)

# Add hidden imports
HIDDEN_IMPORTS=(
    "cv2"
    "mediapipe"
    "psutil"
    "PyQt6"
    "PyQt6.QtCore"
    "PyQt6.QtGui"
    "PyQt6.QtWidgets"
    "requests"
    "json"
    "pathlib"
    "datetime"
    "uuid"
    "dotenv"
    "sqlite3"
    "matplotlib"
    "matplotlib.pyplot"
    "numpy"
    "sqlalchemy"
    "sqlalchemy.ext"
    "sqlalchemy.ext.declarative"
    "sqlalchemy.orm"
    "sqlalchemy.sql"
    "sqlalchemy.engine"
    "desktop.eye_tracker"
    "shared.config"
    "backend.models"
)

for import in "${HIDDEN_IMPORTS[@]}"; do
    PYINSTALLER_ARGS+=(--hidden-import "$import")
done

# Add collect-all for problematic packages
COLLECT_ALL=(
    "mediapipe"
    "cv2"
    "matplotlib"
    "sqlalchemy"
)

for package in "${COLLECT_ALL[@]}"; do
    PYINSTALLER_ARGS+=(--collect-all "$package")
done

# Exclude unnecessary modules to reduce size
EXCLUDE_MODULES=(
    "tkinter"
    "unittest"
    "email"
    "http"
    "urllib"
    "xml"
    "test"
    "distutils"
)

for module in "${EXCLUDE_MODULES[@]}"; do
    PYINSTALLER_ARGS+=(--exclude-module "$module")
done

# Add main script
PYINSTALLER_ARGS+=("desktop/main.py")

# Run PyInstaller
echo "PyInstaller command:"
echo "pyinstaller ${PYINSTALLER_ARGS[*]}"
echo ""

pyinstaller "${PYINSTALLER_ARGS[@]}"

if [[ $? -eq 0 ]]; then
    print_success "PyInstaller completed successfully"
else
    print_error "PyInstaller failed"
    exit 1
fi

# Verify the app was created
APP_PATH="$DIST_DIR/$APP_NAME.app"
if [[ ! -d "$APP_PATH" ]]; then
    print_error "Application bundle not found at $APP_PATH"
    exit 1
fi

print_success "Application bundle created: $APP_PATH"

# Create DMG
print_status "Creating DMG package..."

# Check if create-dmg is available
if ! command -v create-dmg &> /dev/null; then
    print_status "Installing create-dmg (DMG creation tool)..."
    if command -v brew &> /dev/null; then
        brew install create-dmg
    else
        print_error "Homebrew not found. Please install create-dmg manually:"
        echo "  brew install create-dmg"
        echo "  or download from: https://github.com/create-dmg/create-dmg"
        exit 1
    fi
fi

# Remove existing DMG
rm -f "$DMG_NAME"

# Create DMG with create-dmg
create-dmg \
    --volname "Wellness at Work" \
    --volicon "$ICON_PATH" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --icon "$APP_NAME.app" 200 190 \
    --hide-extension "$APP_NAME.app" \
    --app-drop-link 600 185 \
    --hdiutil-quiet \
    "$DMG_NAME" \
    "$APP_PATH"

if [[ $? -eq 0 ]]; then
    print_success "DMG created successfully: $DMG_NAME"
else
    print_error "DMG creation failed"
    exit 1
fi

# Get file sizes
APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
DMG_SIZE=$(du -sh "$DMG_NAME" | cut -f1)

print_status "Build Summary"
echo "=============="
echo "📱 Application: $APP_PATH ($APP_SIZE)"
echo "💿 DMG Package: $DMG_NAME ($DMG_SIZE)"
echo "🔗 Backend URL: $BACKEND_URL"
echo "📅 Build Date: $(date)"

print_success "macOS build completed successfully!"
print_status "To test the application:"
echo "  1. Copy $DMG_NAME to your MacBook"
echo "  2. Double-click to mount the DMG"
echo "  3. Drag WellnessAtWork.app to Applications"
echo "  4. Launch from Applications (may need to right-click → Open first time)"

print_warning "Note: The app is unsigned, so macOS may show security warnings."
echo "To bypass: System Preferences → Security & Privacy → Allow apps downloaded from anywhere"
echo "Or right-click the app → Open → Open when prompted."

echo ""
print_success "🎉 macOS distribution package ready for testing!"
