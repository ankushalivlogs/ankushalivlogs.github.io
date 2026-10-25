"""Makes the website images from assets/*-original.webp: transparent background (keeps the sticker's white border), resized, favicon, share image."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/img"; OUT.mkdir(parents=True, exist_ok=True)

def cutout(path):
    import numpy as np
    from scipy import ndimage as ndi
    im = Image.open(path).convert("RGB"); w, h = im.size
    for pt in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)):
        ImageDraw.floodfill(im, pt, (255, 0, 255), thresh=2)  # flat 254-grey background; the sticker's grey edge line stops the fill
    arr = np.array(im)
    keep = ~((arr[..., 0] == 255) & (arr[..., 1] == 0) & (arr[..., 2] == 255))
    keep = ndi.binary_opening(keep, structure=np.ones((5, 5)))           # kill 1-4px specks
    lab, n = ndi.label(keep); sizes = ndi.sum(keep, lab, range(1, n + 1))
    keep = np.isin(lab, [i + 1 for i, a in enumerate(sizes) if a > 0.0015 * w * h])  # drop small floating bits
    keep = ndi.binary_fill_holes(keep)
    rgba = np.dstack([arr, (keep * 255).astype("uint8")])
    out = Image.fromarray(rgba, "RGBA")
    out.putalpha(out.getchannel("A").filter(ImageFilter.GaussianBlur(1)))  # soft edge
    return out

def fit(im, w): return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
fam = cutout(ROOT / "assets/family-sticker-original.webp")                  # sticker with white border -> transparent background
fit(fam, 900).save(OUT / "family-sticker.webp", quality=88, method=6)
ban = Image.open(ROOT / "assets/banner-original.webp").convert("RGB")          # full-bleed channel banner, used as a rounded card
fit(ban, 1600).save(OUT / "banner-sticker.webp", quality=86, method=6)
logo = Image.open(ROOT / "assets/logo-circle-original.png").convert("RGBA")    # circular logo -> favicon + touch icon
box = logo.getbbox() or (0, 0, *logo.size); logo = logo.crop(box)
canvas = Image.new("RGBA", (192, 192), (0, 0, 0, 0)); lg = logo.resize((184, 184), Image.LANCZOS); canvas.paste(lg, (4, 4), lg)
canvas.resize((64, 64), Image.LANCZOS).save(OUT / "favicon.png"); canvas.save(OUT / "apple-touch-icon.png")
# 1200x630 share image: whole banner on a matching cream background (nothing cropped)
edge = ban.getpixel((ban.width - 6, ban.height // 2)); canvas = Image.new("RGB", (1200, 630), edge)
bw = fit(ban, 1200); canvas.paste(bw, (0, (630 - bw.height) // 2)); canvas.save(OUT.parent / "og.png", optimize=True)
for f in sorted(OUT.iterdir()): print(f.name, f.stat().st_size // 1024, "KB")
print("og.png", (OUT.parent / "og.png").stat().st_size // 1024, "KB")
