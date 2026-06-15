from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
src = ROOT / 'LOGO-VEHRAD.png'
res_root = ROOT / 'android_wrapper' / 'app' / 'src' / 'main' / 'res'

# 108 dp at each density (modern Android standard)
sizes = {
    'mipmap-mdpi': 108,
    'mipmap-hdpi': 162,
    'mipmap-xhdpi': 216,
    'mipmap-xxhdpi': 324,
    'mipmap-xxxhdpi': 432,
}

if not src.exists():
    print('Source logo not found:', src)
    raise SystemExit(1)

with Image.open(src) as im:
    im = im.convert('RGBA')
    
    # Create logo centered in transparent canvas (for adaptive icon foreground)
    def make_transparent_logo(size):
        canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))  # Transparent background
        iw, ih = im.size
        # Scale logo to 72% of canvas (safe zone is 66dp, but 72% gives good visual balance)
        scale = min(size * 0.72 / iw, size * 0.72 / ih)
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
        resized = im.resize((nw, nh), Image.LANCZOS)
        paste_x = (size - nw) // 2
        paste_y = (size - nh) // 2
        canvas.paste(resized, (paste_x, paste_y), resized)
        return canvas

    # Generate the adaptive launcher foreground asset in mipmap-anydpi-v26 (108 dp)
    anydpi = res_root / 'mipmap-anydpi-v26'
    anydpi.mkdir(parents=True, exist_ok=True)
    launcher_foreground = make_transparent_logo(432)  # xxxhdpi equivalent for density scaling
    launcher_foreground.save(anydpi / 'ic_launcher_foreground.png', format='PNG')
    print('Wrote', anydpi / 'ic_launcher_foreground.png', (anydpi / 'ic_launcher_foreground.png').stat().st_size)

    # Generate density-specific static launcher icons (108 dp at each density)
    for folder, size in sizes.items():
        out_dir = res_root / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'ic_launcher.png'
        out_round = out_dir / 'ic_launcher_round.png'
        icon = make_transparent_logo(size)
        icon.save(out_path, format='PNG')
        icon.save(out_round, format='PNG')
        print('Wrote', out_path, out_path.stat().st_size)
        print('Wrote', out_round, out_round.stat().st_size)
