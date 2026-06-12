from pathlib import Path
import urllib.request
import zipfile
import os
import tempfile

url = 'https://services.gradle.org/distributions/gradle-8.1-bin.zip'
path = Path(tempfile.gettempdir()) / 'gradle-8.1-bin.zip'
print('Downloading', url)
urllib.request.urlretrieve(url, path)
print('Downloaded to', path)
with zipfile.ZipFile(path, 'r') as z:
    names = z.namelist()
    print('Total entries:', len(names))
    matches = [n for n in names if 'gradle-wrapper.jar' in n or 'wrapper' in n or 'gradle-wrapper.properties' in n]
    for n in matches[:50]:
        print(n)
    print('---')
    print('First 50 entries:')
    for n in names[:50]:
        print(n)
