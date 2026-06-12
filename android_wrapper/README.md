# VTHC Middleware - Native Android APK

A native Android application that packages the VTHC Middleware (Flask-based RFID inventory bridge) as a standalone APK for Chainway C72 and other Android devices.

## 🎯 Quick Start

### Fastest Way: GitHub Actions (No Setup)
```bash
git push -u origin main  # Push to GitHub
# Visit: https://github.com/YOUR_USERNAME/vthc-middleware/actions
# Download APK from artifacts
```

### Local with Docker
```bash
docker build -t vthc-builder .
docker run -v $(pwd):/workspace vthc-builder
```

### Manual Build
```bash
./gradlew assembleDebug  # Unix/Mac/Linux
gradlew.bat assembleDebug  # Windows
```

---

## 📁 What's Inside

```
.
├── app/src/main/
│   ├── java/com/vthc/middleware/MainActivity.java   # WebView + Python launcher
│   ├── python/
│   │   ├── middleware.py                            # Your Flask app
│   │   └── main.py                                  # Startup entry
│   ├── res/layout/activity_main.xml                 # UI layout
│   └── AndroidManifest.xml                          # App permissions & config
├── build.gradle                                     # Root build config
├── app/build.gradle                                 # App-specific config (Chaquopy)
├── settings.gradle                                  # Project settings
├── gradlew / gradlew.bat                            # Gradle wrapper scripts
├── .github/workflows/build.yml                      # GitHub Actions CI/CD
├── Dockerfile                                       # Docker build environment
├── BUILD_INSTRUCTIONS.md                            # Detailed build guide
└── build_helper.py                                  # Interactive build helper

```

---

## 🔧 Architecture

**Android Layer (Java):**
- WebView component displays local website
- Launches Python Flask server on startup
- Communicates via `http://127.0.0.1:5000`

**Python Layer (Flask):**
- Same `middleware.py` from parent project
- Embedded via Chaquopy plugin
- Includes Flask + Pillow dependencies
- Accesses `http://localhost:5000` on device

**Build Tools:**
- **Gradle 8.1** - Build automation
- **Chaquopy** - Python on Android
- **Android SDK 34** - Latest Android API

---

## 📋 Requirements

### For GitHub Actions
- GitHub account ✓
- This repository pushed to GitHub

### For Docker
- Docker installed
- ~15GB free disk space
- ~45 minutes build time

### For Manual Build
- Java 17+ (you have)
- Android SDK (auto-downloaded, ~8GB)
- 60+ minutes build time

---

## 🚀 Installation

### Step 1: Enable USB Debugging
1. Settings → About Phone → tap "Build Number" 7 times
2. Settings → Developer Options → USB Debugging **ON**

### Step 2: Install APK
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

### Step 3: Launch
- Tap "VTHC Middleware" app icon
- Flask server starts automatically
- Web UI loads at `http://127.0.0.1:5000`

---

## 📖 Documentation

- **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)** - Detailed build methods
- **[Chaquopy Docs](https://chaquo.com/chaquopy/)** - Python on Android
- **[Gradle Docs](https://gradle.org/docs/)** - Build system

---

## 🔌 Customization

### Change App Name
```gradle
// app/build.gradle
manifestPlaceholders = ['appName': 'My Custom Name']
```

### Add Python Dependencies
```gradle
// app/build.gradle
chaquopy {
    python {
        pip {
            install "flask"
            install "requests"         // Add here
            install "numpy"
        }
    }
}
```

### Change Port
```python
# app/src/main/python/main.py
from middleware import run_flask_server
def run_server():
    run_flask_server(host='127.0.0.1', port=8080)  # Change port
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| "Gradle not found" | Run `python build_helper.py` or `python create_gradle_wrapper.py` |
| "Android SDK not found" | Set `ANDROID_SDK_ROOT` env variable |
| "Chaquopy download timeout" | Retry build; it downloads on first build |
| "APK won't install" | Check device minimum SDK (24) or try unsigned release build |
| "Server won't start" | Check logcat: `adb logcat \| grep middleware` |

---

## 📦 Build Outputs

After successful build, find APK at:

```
app/build/outputs/apk/debug/app-debug.apk
```

**Size:** ~150-200 MB (includes Python runtime)

---

## 🔒 Security Notes

- This is a **debug APK** (no code obfuscation)
- For production, rebuild with: `./gradlew assembleRelease`
- Sign APK before distributing

---

## 📞 Support

- Check logcat: `adb logcat`
- View Python errors: `adb shell "cat /data/data/com.vthc.middleware/files/vthc_error.log"`
- Rebuild clean: `./gradlew clean assembleDebug`

---

## 📄 License

Inherits license from parent VTHC Middleware project.

