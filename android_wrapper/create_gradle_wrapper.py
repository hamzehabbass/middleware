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
        z.extract('gradle-8.1/lib/gradle-wrapper.jar', root / 'gradle-tmp')
    src = root / 'gradle-tmp' / 'gradle-8.1' / 'lib' / 'gradle-wrapper.jar'
    src.replace(jar_path)
    import shutil
    shutil.rmtree(root / 'gradle-tmp', ignore_errors=True)
    zip_path.unlink()
    print('Gradle wrapper jar downloaded.')

print('Created Gradle wrapper at', jar_path)
print('Files:')
print((root / 'gradlew.bat').resolve())
print((root / 'gradlew').resolve())
print((wrapper_dir / 'gradle-wrapper.properties').resolve())
print(jar_path.resolve())
