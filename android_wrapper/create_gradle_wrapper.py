from pathlib import Path
import urllib.request
import zipfile

root = Path(r'C:/Users/hamza/Desktop/MiddleWare/android_wrapper')
wrapper_dir = root / 'gradle' / 'wrapper'
wrapper_dir.mkdir(parents=True, exist_ok=True)

props = (
    'distributionBase=GRADLE_USER_HOME\n'
    'distributionPath=wrapper/dists\n'
    'distributionUrl=https://services.gradle.org/distributions/gradle-8.1-bin.zip\n'
    'zipStoreBase=GRADLE_USER_HOME\n'
    'zipStorePath=wrapper/dists\n'
)
(wrapper_dir / 'gradle-wrapper.properties').write_text(props, encoding='utf-8')
(root / 'gradlew.bat').write_text('@echo off\nset DIR=%~dp0\n"%DIR%gradle\\wrapper\\gradle-wrapper.jar" %*\n', encoding='ascii')
(root / 'gradlew').write_text('#!/usr/bin/env sh\nDIR="$(cd "$(dirname "$0")" && pwd)"\njava -jar "$DIR/gradle/wrapper/gradle-wrapper.jar" "$@"\n', encoding='ascii')

jar_path = wrapper_dir / 'gradle-wrapper.jar'
if not jar_path.exists():
    zip_path = root / 'gradle-wrapper.zip'
    print('Downloading Gradle wrapper zip...')
    urllib.request.urlretrieve('https://services.gradle.org/distributions/gradle-8.1-bin.zip', zip_path)
    with zipfile.ZipFile(zip_path, 'r') as z:
        candidate = None
        for name in z.namelist():
            if name.endswith('gradle-wrapper.jar'):
                candidate = name
                break
            if name.endswith('gradle-wrapper-8.1.jar'):
                candidate = name
                break
        if not candidate:
            raise RuntimeError('Could not find gradle wrapper jar in Gradle distribution')
        with z.open(candidate) as src, open(jar_path, 'wb') as dst:
            dst.write(src.read())
    try:
        zip_path.unlink()
    except Exception:
        pass
    print('Gradle wrapper jar downloaded from', candidate)

print('Created Gradle wrapper at', jar_path)
print('Files:')
print((root / 'gradlew.bat').resolve())
print((root / 'gradlew').resolve())
print((wrapper_dir / 'gradle-wrapper.properties').resolve())
print(jar_path.resolve())
