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

fam = cutout(ROOT / "assets/family-sticker-original.webp"); ban = cutout(ROOT / "assets/banner-sticker-original.webp")
def fit(im, w): return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
fit(fam, 900).save(OUT / "family-sticker.webp", quality=88, method=6)
fit(ban, 1500).save(OUT / "banner-sticker.webp", quality=88, method=6)
ico = fit(fam, 180); canvas = Image.new("RGBA", (192, 192), (0, 0, 0, 0)); canvas.paste(ico, (6, 6), ico)
canvas.resize((64, 64), Image.LANCZOS).save(OUT / "favicon.png"); canvas.save(OUT / "apple-touch-icon.png")
# 1200x630 share image
bg = Image.new("RGB", (1200, 630)); g = Image.linear_gradient("L").resize((1200, 630)).rotate(0)
c1, c2 = (251, 213, 220), (207, 227, 245)
bg = Image.composite(Image.new("RGB", (1200, 630), c2), Image.new("RGB", (1200, 630), c1), g)
b = fit(ban, 1120); sh = Image.new("RGBA", b.size, (0, 0, 0, 0)); sh.putalpha(b.getchannel("A").point(lambda v: int(v * .25))); sh = sh.filter(ImageFilter.GaussianBlur(14))
x, y = (1200 - b.width) // 2, (630 - b.height) // 2
bg.paste(sh.convert("RGB"), (x, y + 10), sh); bg.paste(b, (x, y), b)
bg.save(OUT.parent / "og.png", optimize=True)
for f in sorted(OUT.iterdir()): print(f.name, f.stat().st_size // 1024, "KB")
print("og.png", (OUT.parent / "og.png").stat().st_size // 1024, "KB")
