from pathlib import Path
p = Path('android_wrapper/app/src/main/res/drawable-nodpi/logo_image.png')
print('exists', p.exists())
if p.exists():
    print('size', p.stat().st_size)
    sig = p.read_bytes()[:16]
    print('sig', sig)
    try:
        from PIL import Image
        img = Image.open(p)
        print('format', img.format)
        print('size', img.size)
        print('mode', img.mode)
        img.close()
    except Exception as e:
        print('PIL error', e)
