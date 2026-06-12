#!/usr/bin/env python3
"""
VTHC Middleware APK Build Helper
Guides through building the APK locally or via GitHub
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def print_step(num, text):
    print(f"[{num}] {text}")

def check_java():
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        return "openjdk" in result.stderr.lower() or "java" in result.stderr.lower()
    except:
        return False

def main():
    print_header("VTHC Middleware APK Build Options")
    
    print("Choose your build method:\n")
    print("1. 🚀 GitHub Actions (Recommended - Zero Setup)")
    print("   - Automatically build in the cloud")
    print("   - Download APK from GitHub")
    print("   - Time: ~5 minutes\n")
    
    print("2. 🐳 Docker (Recommended - Local Build)")
    print("   - Requires Docker")
    print("   - Self-contained environment")
    print("   - Time: ~45 minutes\n")
    
    print("3. 🔧 Manual (Advanced - Windows/Local)")
    print("   - Requires Android SDK setup")
    print("   - Full local control")
    print("   - Time: ~60 minutes\n")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == "1":
        print_header("GitHub Actions Build")
        print_step(1, "Create a GitHub repository")
        print("   git init")
        print("   git add .")
        print("   git commit -m 'Initial commit'")
        print("   git remote add origin https://github.com/YOUR_USERNAME/vthc-middleware.git")
        print("   git push -u origin main\n")
        
        print_step(2, "Visit GitHub Actions")
        print("   https://github.com/YOUR_USERNAME/vthc-middleware/actions\n")
        
        print_step(3, "Download APK from Artifacts")
        print("   The build will complete in ~5 minutes")
        print("   Download 'vthc-middleware-debug.apk' from the workflow run\n")
        
    elif choice == "2":
        print_header("Docker Build")
        print("Prerequisites: Docker installed\n")
        
        print_step(1, "Build Docker image")
        print("   docker build -t vthc-builder .\n")
        
        print_step(2, "Run build")
        print("   docker run -v $(pwd):/workspace vthc-builder\n")
        
        print_step(3, "Find APK")
        print("   app/build/outputs/apk/debug/app-debug.apk\n")
        
    elif choice == "3":
        print_header("Manual Windows Build")
        
        if not check_java():
            print("❌ Java not found. Please install Java 17+")
            sys.exit(1)
        else:
            print("✓ Java is installed\n")
        
        print_step(1, "Install Android SDK")
        print("   This will be downloaded automatically\n")
        
        print_step(2, "Run build")
        print("   .\\gradlew.bat assembleDebug\n")
        
        print_step(3, "Find APK")
        print("   app\\build\\outputs\\apk\\debug\\app-debug.apk\n")
        
        print("   This may take 45-60 minutes on first run.")
        print("   You need ~20GB free disk space for Android SDK.\n")
        
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)
    
    print_header("Next Steps")
    print("1. Read: BUILD_INSTRUCTIONS.md")
    print("2. For manual build: Set ANDROID_SDK_ROOT environment variable")
    print("3. Install APK on device: adb install app-debug.apk")
    print("\nGood luck! 🎉")

if __name__ == "__main__":
    main()
