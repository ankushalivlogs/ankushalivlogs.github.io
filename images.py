"""Resolves each affiliate short link to a product photo (data/images.json) and the store's listing title (data/titles.json).
Both are cached; delete the file(s) to refresh. New links in video descriptions are picked up automatically."""
import html as _html, json, re, time, urllib.request
from pathlib import Path
R = Path(__file__).parent
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
img_f, title_f = R / "data/images.json", R / "data/titles.json"
cache = json.loads(img_f.read_text()) if img_f.exists() else {}
titles = json.loads(title_f.read_text()) if title_f.exists() else {}
from build import load
links = set(load()[1])

def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20)

def clean_title(t):
    t = _html.unescape(t or "").strip()
    t = re.sub(r"\s*[:|\-]\s*Amazon\.in.*$", "", t, flags=re.I)
    t = re.sub(r"^Buy\s+", "", t)
    return re.sub(r"\s+", " ", t)[:140]

for u in [k for k in links if not cache.get(k) or not titles.get(k)]:
    time.sleep(2)
    try:
        f = get(u); page = f.read().decode("utf-8", "ignore")
        og = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', page)
        asin = re.search(r"/(?:dp|d)/([A-Z0-9]{10})", f.geturl())
        if not cache.get(u):
            img = og.group(1) if og else None
            if not img:  # no og:image: take the main product image (not the _SL75_ thumbs)
                m = (re.search(r'id="landingImage"[^>]*?(?:data-old-hires|src)="(https://[^"]+)"', page)
                     or re.search(r'"hiRes":"(https://[^"]+)"', page)
                     or re.search(r'(https://m\.media-amazon\.com/images/I/[\w%+-]+\.jpg)', page))
                img = m.group(1) if m else None
            if not img and asin:
                cdn = f"https://m.media-amazon.com/images/P/{asin.group(1)}.01._SL500_.jpg"
                if len(get(cdn).read()) > 1000:  # 43 bytes = Amazon's 1px "no image" gif
                    img = cdn
            cache[u] = img
        cands = [re.search(r'id="productTitle"[^>]*>\s*([^<]+)', page), re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', page),
                 re.search(r"<title[^>]*>([^<]*)", page)]
        for c in cands:
            ct = clean_title(c.group(1)) if c else ""
            if ct and ct.lower() not in ("amazon.in", "amazon"):
                titles[u] = ct
                break
    except Exception as e:
        print("skip", u, e)
img_f.write_text(json.dumps(cache, indent=1))
title_f.write_text(json.dumps(titles, indent=1, ensure_ascii=False))
print(f"{sum(1 for v in cache.values() if v)}/{len(cache)} products have images, {len(titles)} titles")
