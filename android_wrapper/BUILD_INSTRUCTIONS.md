# VTHC Middleware APK Build Guide

This project builds a native Android APK for the VTHC Middleware (Flask-based RFID inventory app).

## Verified Fast Rebuild (Windows, 2026-06-17)

Use this exact method for future rebuilds on this machine.

### 0) Ensure local SDK path format is valid

`android_wrapper/local.properties` must contain exactly:

```properties
sdk.dir=C:/Android/Sdk
```

Do not use extra escaping like `C\\:\\Android\\Sdk`.

### 1) Keep Chaquopy config as below

In `app/build.gradle` under `chaquopy { defaultConfig { ... } }`:

```gradle
version "3.13"
buildPython "C:/Python313/python.exe"
```

### 2) Regenerate launcher icon assets (if logo changed)

From workspace root:

```powershell
Set-Location 'C:\Users\hamza\Desktop\VTHC\MiddleWare'
python generate_mipmaps.py
```

### 3) Run this exact PowerShell build command

From PowerShell:

```powershell
$sdkRoot='C:\Android\Sdk';
$jdk17 = Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory |
   Where-Object { $_.Name -like 'jdk-17*' } |
   Sort-Object Name -Descending |
   Select-Object -First 1;

if (-not $jdk17) { throw 'JDK 17 not found under C:\Program Files\Eclipse Adoptium' }

$env:JAVA_HOME=$jdk17.FullName;
$env:ANDROID_SDK_ROOT=$sdkRoot;
$env:ANDROID_HOME=$sdkRoot;
$env:Path="$($env:JAVA_HOME)\bin;$sdkRoot\cmdline-tools\latest\bin;$sdkRoot\platform-tools;$env:Path";

Set-Location 'C:\Users\hamza\Desktop\VTHC\MiddleWare\android_wrapper';
.\gradlew.bat assembleDebug
```

### 4) Confirm APK exists

```powershell
Test-Path 'C:\Users\hamza\Desktop\VTHC\MiddleWare\android_wrapper\app\build\outputs\apk\debug\app-debug.apk'
Get-Item 'C:\Users\hamza\Desktop\VTHC\MiddleWare\android_wrapper\app\build\outputs\apk\debug\app-debug.apk' |
   Select-Object FullName,Length,LastWriteTime
```

Expected output location:

```text
app\build\outputs\apk\debug\app-debug.apk
```

### Why this method is the reliable one here

- Build was successful with this exact flow (`BUILD SUCCESSFUL in 2m 24s`).
- Gradle 8.1 failed under Java 25 (`Unsupported class file major version 69`), and JDK 17 fixed it.
- Android SDK resolution failed until `local.properties` used `sdk.dir=C:/Android/Sdk` format.
- Python 3.10 installation was blocked by Windows Installer pending reboot (`MsiSystemRebootPending=1`).
- Using Chaquopy Python 3.13 with `C:/Python313/python.exe` avoided that blocker and completed the APK build.

## Quick Start (Recommended)

### Option 1: Build Using GitHub Actions (⭐ Easiest - No Setup Required)

1. **Push to GitHub:**
   - Create a GitHub repository
   - Push this folder to GitHub
   - The APK builds automatically and is downloadable as an artifact

**Steps:**
```bash
git init
git add .
git commit -m "Initial VTHC Middleware APK"
git remote add origin https://github.com/YOUR_USERNAME/vthc-middleware.git
git push -u origin main
```

- Visit: `https://github.com/YOUR_USERNAME/vthc-middleware/actions`
- Click on the latest workflow run
- Download `vthc-middleware-debug.apk` from "Artifacts"

**Time:** ~5 minutes, fully automated

---

### Option 2: Build Locally with Docker (⭐ Recommended for Local)

**Prerequisites:**
- Docker installed
- ~15GB free disk space

**Steps:**
```bash
cd android_wrapper
docker build -t vthc-builder .
docker run -v $(pwd):/workspace vthc-builder
```

The APK will be at: `app/build/outputs/apk/debug/app-debug.apk`

**Time:** 30-45 minutes (first build)

---

### Option 3: Manual Build on Windows (Advanced)

**Prerequisites:**
- Java 17+ (you have this: `java -version` ✓)
- Android SDK (needs download)
- Gradle (auto-downloaded via gradlew)

**Steps:**

1. **Install Android SDK:**
   ```powershell
   # Download and extract Android SDK command-line tools
   $url = "https://dl.google.com/android/repository/commandlinetools-windows-9862592_latest.zip"
   Invoke-WebRequest -Uri $url -OutFile "C:\android-tools.zip"
   Expand-Archive "C:\android-tools.zip" -DestinationPath "C:\Android\cmdline-tools"
   ```

2. **Install Required Android Components:**
   ```powershell
   $env:ANDROID_SDK_ROOT="C:\Android"
   & "C:\Android\cmdline-tools\cmdline-tools\bin\sdkmanager.bat" "platforms;android-34" "build-tools;34.0.0"
   ```

3. **Build APK:**
   ```powershell
   cd android_wrapper
   .\gradlew.bat assembleDebug
   ```

4. **APK Location:**
   ```
   app\build\outputs\apk\debug\app-debug.apk
   ```

**Time:** 45-60 minutes (first build, many downloads)

---

## Project Structure

```
android_wrapper/
├── app/
│   ├── src/main/
│   │   ├── java/com/vthc/middleware/      # Android Java code
│   │   ├── python/                        # Python server code
│   │   │   ├── middleware.py              # Flask app
│   │   │   └── main.py                    # Startup entrypoint
│   │   ├── res/layout/                    # Android UI layouts
│   │   └── AndroidManifest.xml
│   └── build.gradle
├── build.gradle
├── settings.gradle
├── gradlew                                 # Gradle wrapper (Unix/Mac)
├── gradlew.bat                             # Gradle wrapper (Windows)
└── Dockerfile                              # For Docker builds
```

---

## Installation on Android Device

1. **Enable Developer Mode:**
   - Settings > About Phone > tap "Build Number" 7 times
   - Settings > Developer Options > USB Debugging ON

2. **Connect Device:**
   ```bash
   adb devices
   ```

3. **Install APK:**
   ```bash
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```

4. **Launch App:**
   - Look for "VTHC Middleware" on home screen or app drawer
   - Tap to open

---

## How It Works

- **Android UI (Java):** WebView displaying local website
- **Python Backend:** Flask server running on `http://127.0.0.1:5000`
- **Middleware:** Bridges Odoo XMLRPC API ↔ RFID Scanner ↔ Android UI
- **Packaging:** Chaquopy embeds Python runtime + dependencies (Flask, Pillow)

---

## Troubleshooting

### "Gradle wrapper jar not found"
- Run: `python create_gradle_wrapper.py`

### "Android SDK not found"
- Set `ANDROID_SDK_ROOT` environment variable to your SDK path

### "Cannot build on Windows"
- Use GitHub Actions (Option 1) - absolutely zero setup

### "Couldn't find Python 3.10" or installer exits 1603
- This project is now set to Python 3.13 in `app/build.gradle` for local Windows rebuilds.
- If you ever switch back to Python 3.10 and see 1603, check for pending reboot state first, then reboot and retry.

### APK too large
- Run: `./gradlew assembleRelease` for optimized build

---

## Customization

### Change App Name
Edit: `app/build.gradle`
```gradle
manifestPlaceholders = [
    'appName': 'Your App Name Here'
]
```

### Change Port
Edit: `app/src/main/python/middleware.py`
```python
run_flask_server(host='127.0.0.1', port=8080)  # Change 5000 to 8080
```

### Add Dependencies
Edit: `app/build.gradle`
```gradle
chaquopy {
    python {
        pip {
            install "flask"
            install "requests"           # Add new package
        }
    }
}
```

---

## Support

- **For GitHub Actions issues:** See `.github/workflows/build.yml`
- **For Docker issues:** Rebuild with `docker build --no-cache -t vthc-builder .`
- **For local build issues:** Check `Android SDK Root` path and Java version

---

## License

Same as parent VTHC Middleware project.

