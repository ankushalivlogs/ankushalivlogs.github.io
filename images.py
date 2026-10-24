"""Resolves each affiliate short link to a product image URL -> data/images.json (cached; delete file to refresh)."""
import json, re, time, urllib.request
from pathlib import Path
R = Path(__file__).parent
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
cache_f = R / "data/images.json"
cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
from build import load
links = set(load()[1])
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20)
for u in [k for k in links if not cache.get(k)]:
    time.sleep(2)
    try:
        f = get(u); page = f.read().decode("utf-8", "ignore")
        og = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', page)
        asin = re.search(r"/(?:dp|d)/([A-Z0-9]{10})", f.geturl())
        img = og.group(1) if og else None
        if not img:  # no og:image: take the main product image (not the _SL75_ thumbs)
            m = re.search(r'id="landingImage"[^>]*?(?:data-old-hires|src)="(https://[^"]+)"', page)                 or re.search(r'"hiRes":"(https://[^"]+)"', page)                 or re.search(r'(https://m\.media-amazon\.com/images/I/[\w%+-]+\.jpg)', page)
            img = m.group(1) if m else None
        if not img and asin:
            cdn = f"https://m.media-amazon.com/images/P/{asin.group(1)}.01._SL500_.jpg"
            if len(get(cdn).read()) > 1000:  # 43 bytes = Amazon's 1px "no image" gif
                img = cdn
        cache[u] = img
    except Exception as e:
        print("skip", u, e)
cache_f.write_text(json.dumps(cache, indent=1))
print(f"{sum(1 for v in cache.values() if v)}/{len(cache)} products have images")
