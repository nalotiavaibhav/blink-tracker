#!/usr/bin/env python3
"""
Desktop Shortcut Creator for WaW Application
============================================

Creates desktop shortcuts for easy access to the WaW application.
Supports Windows (.lnk), macOS (.app), and Linux (.desktop).
"""

import os
import sys
from pathlib import Path
import platform

def create_windows_shortcut():
    """Create Windows desktop shortcut (.lnk)"""
    try:
        import win32com.client
        
        # Get paths
        desktop = Path.home() / "Desktop"
        project_root = Path(__file__).parent.absolute()
        launcher_bat = project_root / "launch_app.bat"
        
        # Create shortcut
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(desktop / "WaW - Wellness at Work.lnk"))
        shortcut.Targetpath = str(launcher_bat)
        shortcut.WorkingDirectory = str(project_root)
        shortcut.Description = "Wellness at Work - Eye Blink Tracker Application"
        shortcut.IconLocation = str(launcher_bat) + ",0"
        shortcut.save()
        
        print(f"✅ Windows shortcut created: {desktop / 'WaW - Wellness at Work.lnk'}")
        return True
        
    except ImportError:
        print("⚠️ pywin32 not installed. Installing...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
            return create_windows_shortcut()  # Retry
        except:
            print("❌ Failed to install pywin32. Please install manually:")
            print("  pip install pywin32")
            return False
    except Exception as e:
        print(f"❌ Failed to create Windows shortcut: {e}")
        return False

def create_macos_shortcut():
    """Create macOS application bundle (.app)"""
    try:
        desktop = Path.home() / "Desktop"
        app_path = desktop / "WaW - Wellness at Work.app"
        contents_path = app_path / "Contents"
        macos_path = contents_path / "MacOS"
        resources_path = contents_path / "Resources"
        
        # Create directory structure
        macos_path.mkdir(parents=True, exist_ok=True)
        resources_path.mkdir(parents=True, exist_ok=True)
        
        # Create Info.plist
        info_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launch_waw</string>
    <key>CFBundleIdentifier</key>
    <string>com.waw.wellness-at-work</string>
    <key>CFBundleName</key>
    <string>WaW - Wellness at Work</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>"""
        
        (contents_path / "Info.plist").write_text(info_plist)
        
        # Create launcher script
        project_root = Path(__file__).parent.absolute()
        launcher_script = f"""#!/bin/bash
cd "{project_root}"
python3 app_launcher.py
"""
        
        launcher_path = macos_path / "launch_waw"
        launcher_path.write_text(launcher_script)
        launcher_path.chmod(0o755)
        
        print(f"✅ macOS app bundle created: {app_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create macOS app bundle: {e}")
        return False

def create_linux_shortcut():
    """Create Linux desktop entry (.desktop)"""
    try:
        desktop = Path.home() / "Desktop"
        project_root = Path(__file__).parent.absolute()
        
        # Create .desktop file content
        desktop_entry = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=WaW - Wellness at Work
Comment=Eye Blink Tracker for Digital Wellness
Exec=python3 "{project_root / 'app_launcher.py'}"
Path={project_root}
Icon=applications-health
Terminal=false
StartupNotify=true
Categories=Health;Utility;
"""
        
        desktop_file = desktop / "WaW - Wellness at Work.desktop"
        desktop_file.write_text(desktop_entry)
        desktop_file.chmod(0o755)
        
        print(f"✅ Linux desktop entry created: {desktop_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create Linux desktop entry: {e}")
        return False

def main():
    """Create appropriate shortcut for current platform"""
    print("🔗 WaW Desktop Shortcut Creator")
    print("=" * 40)
    
    system = platform.system().lower()
    
    if system == "windows":
        print("🪟 Detected Windows - Creating .lnk shortcut...")
        success = create_windows_shortcut()
    elif system == "darwin":
        print("🍎 Detected macOS - Creating .app bundle...")
        success = create_macos_shortcut()
    elif system == "linux":
        print("🐧 Detected Linux - Creating .desktop entry...")
        success = create_linux_shortcut()
    else:
        print(f"❌ Unsupported platform: {system}")
        success = False
    
    if success:
        print("\n✅ Desktop shortcut created successfully!")
        print("💡 You can now launch WaW from your desktop.")
    else:
        print("\n❌ Failed to create desktop shortcut.")
        print("💡 You can still run the application using:")
        print(f"   python {Path(__file__).parent / 'app_launcher.py'}")

if __name__ == "__main__":
    main()
