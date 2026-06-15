from pathlib import Path
from PIL import Image
src = Path('LOGO-VEHRAD.png')
dst = Path('android_wrapper/app/src/main/res/drawable-nodpi/logo_image.png')
with Image.open(src) as im:
    im.convert('RGBA').save(dst, format='PNG')
print('wrote', dst, dst.stat().st_size)
