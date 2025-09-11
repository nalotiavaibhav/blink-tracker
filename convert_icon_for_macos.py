#!/usr/bin/env python3
"""
Icon Converter for macOS Build

Converts Windows ICO to macOS ICNS format for proper icon display.
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def convert_ico_to_icns(ico_path, icns_path):
    """Convert ICO file to ICNS format using Pillow"""
    if not HAS_PIL:
        print("❌ Pillow (PIL) not available. Install with: pip install Pillow")
        return False
    
    try:
        # Load the ICO file
        img = Image.open(ico_path)
        
        # ICO files can contain multiple sizes, get the largest
        if hasattr(img, 'n_frames'):
            # Find the largest frame
            largest_size = 0
            best_frame = 0
            for frame in range(img.n_frames):
                img.seek(frame)
                size = max(img.size)
                if size > largest_size:
                    largest_size = size
                    best_frame = frame
            img.seek(best_frame)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Resize to standard macOS icon size (512x512 is good)
        target_size = min(512, max(img.size))
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Save as PNG first (ICNS is complex, but PNG works for PyInstaller)
        png_path = icns_path.replace('.icns', '.png')
        img.save(png_path, 'PNG')
        
        # Try to save as ICNS if possible
        try:
            img.save(icns_path, 'ICNS')
            print(f"✅ Converted {ico_path} → {icns_path}")
            return True
        except Exception as e:
            # ICNS save might not work, but PNG will work for PyInstaller
            print(f"⚠️ ICNS save failed ({e}), but PNG created: {png_path}")
            # Copy PNG to ICNS name so PyInstaller can find it
            import shutil
            shutil.copy2(png_path, icns_path)
            return True
            
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False

def main():
    """Main function to convert icon"""
    print("🔄 Converting Windows ICO to macOS ICNS...")
    
    # Find the ICO file
    ico_path = Path("assets/app.ico")
    if not ico_path.exists():
        print(f"❌ Icon file not found: {ico_path}")
        print("Please ensure assets/app.ico exists")
        return 1
    
    # Output path
    icns_path = Path("assets/app.icns")
    
    print(f"📁 Input: {ico_path}")
    print(f"📁 Output: {icns_path}")
    
    # Convert
    if convert_ico_to_icns(str(ico_path), str(icns_path)):
        print("🎉 Icon conversion completed successfully!")
        
        # Show file sizes
        ico_size = ico_path.stat().st_size
        icns_size = icns_path.stat().st_size
        print(f"📊 ICO size: {ico_size:,} bytes")
        print(f"📊 ICNS size: {icns_size:,} bytes")
        
        return 0
    else:
        print("💥 Icon conversion failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
