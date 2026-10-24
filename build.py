"""Builds the static site (docs/) from data/raw.jsonl (video descriptions) + posts/*.md.
Run: python build.py   (or ./fetch.sh to re-pull descriptions from YouTube + product photos first)
Any "Name: https://link" line in a video description becomes a product, auto-sorted into a section by keywords in the name."""
import html, json, re
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
SITE = {
    "name": "Ankushali Picks",
    "channel": "Ankushali Vlogs",
    "tagline": "Real parenting, everyday finds & Kushu ki masti. Everything we use, in one place.",
    "youtube": "https://www.youtube.com/@Ankushali_Vlogs",
    "instagram": "https://www.instagram.com/ankushalii_",  # video descriptions say ankushali_ - check which is right
}
CATS = [  # (label, icon, keywords) - first match wins, order = order on the page
    ("Baby Feeding", "🍼", ["cerelac", "teat", "nipple", "bottle", "feeding", "formula", "sipper", "high chair"]),
    ("Baby Care & Diapers", "🧷", ["mamy", "pampers", "diaper", "wipes", "huggies", "baby lotion", "baby oil", "baby powder"]),
    ("Play & Gear", "🧸", ["walker", "playing mat", "play mat", "toy", "stroller", "car seat", "rattle", "ride-on"]),
    ("Nursery & Storage", "🛏️", ["wardrobe", "almira", "almirah", "cot", "crib", "baby clothes", "organizer"]),
    ("Mics & Audio", "🎤", ["mic", "microphone", "headphone", "earbud", "earphone", "speaker", "airdopes", "tws", "headset"]),
    ("Laptops & Computers", "💻", ["laptop", "macbook", "keyboard", "monitor", "ssd", "mouse", "router", "pendrive", "hard disk"]),
    ("Camera & Creator Gear", "🎥", ["gopro", "dji", "osmo", "camera", "tripod", "ring light", "lens", "gimbal", "lapel"]),
    ("Shoes & Fashion", "👟", ["shoe", "sneaker", "sandal", "slipper", "watch", "bag", "jacket", "tshirt", "t-shirt", "shirt", "jeans", "kurta", "saree"]),
    ("Home & Decor", "🏡", ["frame", "table", "cover", "decor", "lamp", "curtain", "wall", "light", "sofa"]),
    ("Kitchen", "🍳", ["cooker", "mixer", "kettle", "pan", "air fryer", "bottle set", "container", "knife"]),
    ("Beauty & Personal Care", "💄", ["perfume", "hair", "straight", "trimmer", "cream", "serum", "shampoo", "makeup", "lipstick"]),
    ("Phones & Gadgets", "📱", ["phone", "mobile", "charger", "power bank", "smartwatch", "tablet", "kindle"]),
    ("Books & Learning", "📚", ["book", "course", "notebook"]),
]
FALLBACK = ("More Finds", "✨")
SKIP_DOMAINS = ("youtube.com", "youtu.be", "instagram.com", "facebook.com", "twitter.com", "x.com", "wa.me", "t.me")
esc = html.escape

def category(name):
    n = name.lower()
    for label, icon, ks in CATS:
        if any(k in n for k in ks):
            return label, icon
    return FALLBACK

def store(link):
    return next((s for k, s in (("amazon", "Amazon"), ("amzn", "Amazon"), ("flipkart", "Flipkart"), ("fkrt", "Flipkart"),
                                ("myntra", "Myntra"), ("meesho", "Meesho")) if k in link), "the store")

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def thumb(src):
    if not src:
        return '<div class="pimg ph">&#128717;</div>'
    return f'<img class="pimg" loading="lazy" referrerpolicy="no-referrer" src="{esc(src)}" alt="">'

def load():
    rows = [json.loads(l) for l in (ROOT / "data/raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rows.sort(key=lambda r: r["upload_date"] or "", reverse=True)
    products, vids = {}, []
    for r in rows:
        vp = []
        for ln in (r["description"] or "").splitlines():
            m = re.search(r"(?:(.*?):\s*)?(https?://[^\s)\]]+)", ln)
            if not m or any(d in m.group(2) for d in SKIP_DOMAINS):
                continue
            link = m.group(2)
            name = re.sub(r"^[^\w]+", "", (m.group(1) or "")).strip() or "Product from this video"
            p = products.setdefault(link, {"name": name, "link": link, "vids": []})
            if p["name"] == "Product from this video" and name != p["name"]:
                p["name"] = name
            p["vids"].append(r["id"])
            vp.append(link)
        vids.append({**r, "plinks": vp, "short": "/shorts/" in (r["webpage_url"] or "")})
    return vids, products

WAVE = """<div class="wave"><svg class="rocket" viewBox="0 0 64 96" aria-hidden="true"><path d="M32 4C44 18 48 40 44 64H20C16 40 20 18 32 4Z" fill="#fff"/><circle cx="32" cy="34" r="7" fill="#7b5cc4"/><path d="M20 52 8 72l14-6zM44 52l12 20-14-6z" fill="#e8607a"/><path d="M26 66h12l-6 24z" fill="#fbbf4a"/></svg>
<svg viewBox="0 0 1440 160" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="wg" x1="0" x2="1"><stop offset="0" stop-color="#f4a261"/><stop offset=".5" stop-color="#e8607a"/><stop offset="1" stop-color="#7b5cc4"/></linearGradient></defs>
<path d="M0 90C220 20 380 130 700 90S1180 10 1440 70V160H0Z" fill="url(#wg)"/></svg></div>"""

def page(title, body, depth=0):
    r = "../" * depth
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<meta name="description" content="Honest picks for parents and everyday life: baby must-haves, audio, laptops, shoes and more, as seen in our vlogs.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Nunito:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}style.css"></head><body>
<header><a class="brand" href="{r}index.html">{esc(SITE['name'])}</a>
<nav><a href="{r}index.html#picks">Picks</a><a href="{r}index.html#vlogs">Vlogs</a><a href="{r}index.html#blog">Blog</a>
<a class="navbtn" href="{SITE['youtube']}">Subscribe</a></nav></header>
{body}
{WAVE}
<footer><div class="fgrid"><div><div class="brand">{esc(SITE['name'])}</div><p>{esc(SITE['tagline'])}</p></div>
<div><h5>Explore</h5><a href="{r}index.html#picks">Our picks</a><a href="{r}index.html#vlogs">Vlogs</a><a href="{r}index.html#blog">Blog</a></div>
<div><h5>Follow</h5><a href="{SITE['youtube']}">YouTube</a><a href="{SITE['instagram']}">Instagram</a></div></div>
<p class="fine">As an Amazon Associate we earn from qualifying purchases. Product links are affiliate links; they cost you nothing extra. Shared from our own experience, not medical advice: please check with your doctor for health questions.</p>
<p class="fine">&copy; {esc(SITE['name'])} &middot; {esc(SITE['channel'])}</p></footer></body></html>"""

def posts():
    out = []
    for f in sorted((ROOT / "posts").glob("*.md"), reverse=True):
        txt = f.read_text(encoding="utf-8")
        t = re.match(r"#\s*(.+)", txt)
        out.append({"slug": f.stem, "date": f.stem[:10], "title": t.group(1) if t else f.stem,
                    "body": markdown.markdown(re.sub(r"^#.*\n", "", txt, count=1))})
    return out

def main():
    vids, products = load()
    (OUT / "blog").mkdir(parents=True, exist_ok=True)
    (OUT / ".nojekyll").write_text("")
    byid = {v["id"]: v for v in vids}
    imgs_f = ROOT / "data/images.json"
    imgs = json.loads(imgs_f.read_text()) if imgs_f.exists() else {}

    groups = {}
    for p in products.values():
        groups.setdefault(category(p["name"]), []).append(p)
    order = [(l, i) for l, i, _ in CATS] + [FALLBACK]
    groups = [(k, groups[k]) for k in order if k in groups]

    chips = '<button class="chip on" data-c="all">All <small>%d</small></button>' % len(products) + "".join(
        f'<button class="chip" data-c="{slug(l)}">{i} {esc(l)} <small>{len(ps)}</small></button>' for (l, i), ps in groups)
    sections = "".join(
        f'<section class="cat" data-c="{slug(l)}"><h3>{i} {esc(l)}</h3><div class="grid">' + "".join(
            f'<a class="card prod" href="{esc(p["link"])}" rel="sponsored noopener" target="_blank">'
            f'{thumb(imgs.get(p["link"]))}<b>{esc(p["name"])}</b>'
            f'<small>Seen in: {esc(byid[p["vids"][0]]["title"][:46])}</small>'
            f'<span class="go">View on {store(p["link"])} &rarr;</span></a>' for p in ps) + "</div></section>"
        for (l, i), ps in groups)

    def vcard(v):
        links = "".join(f'<a href="{esc(l)}" rel="sponsored noopener" target="_blank">{esc(products[l]["name"])}</a>' for l in v["plinks"])
        return (f'<article class="card vid"><a href="{esc(v["webpage_url"])}"><img loading="lazy" '
                f'src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt=""></a>'
                f'<h4>{esc(v["title"])}</h4><small>{"Short" if v["short"] else "Video"} &middot; {v["upload_date"]}</small>'
                + (f'<div class="plinks">{links}</div>' if links else "") + "</article>")
    long_v = [v for v in vids if not v["short"]]
    short_v = [v for v in vids if v["short"]]
    ps_ = posts()
    blog_html = "".join(f'<a class="card post" href="blog/{p["slug"]}.html"><small>{p["date"]}</small><b>{esc(p["title"])}</b></a>' for p in ps_) or "<p>Coming soon.</p>"

    body = f"""<section class="hero"><span class="pill">&#10024; For parents &amp; parents-to-be</span>
<h1>Find what we <em>actually use</em></h1><p>{esc(SITE['tagline'])}</p>
<div class="strip"><div class="stat"><b>{len(products)}</b><small>Picks</small></div>
<div class="stat"><b>{len(long_v) + len(short_v)}</b><small>Videos</small></div>
<p>Spotted in our vlogs, tested in real life</p><a class="gbtn" href="#picks">Browse picks</a></div></section>
<main><section id="picks"><h2>Meet our favourite finds</h2><p class="sub">Baby must-haves, gadgets, audio, shoes and more. Pick a section or search.</p>
<input id="q" placeholder="Search products..." aria-label="Search products"><div class="chips">{chips}</div>{sections}<p id="none" hidden>Nothing found. Try another word.</p></section>
<section id="how"><h2>How it works</h2><div class="steps"><div><b>1</b><h4>Watch</h4><p>Catch the product in one of our vlogs.</p></div>
<div><b>2</b><h4>Tap</h4><p>Find it here or in the video description.</p></div>
<div><b>3</b><h4>Shop</h4><p>Buy on the store. Same price for you, a small thank-you for us.</p></div></div></section>
<section id="vlogs"><h2>Our vlogs</h2><p class="sub">Every video, with the products from its description.</p><div class="grid">{''.join(vcard(v) for v in long_v)}</div>
<h2>Quick shorts</h2><div class="grid">{''.join(vcard(v) for v in short_v)}</div></section>
<section id="blog"><h2>Parenting &amp; life blog</h2><p class="sub">Checklists, lessons learned and real talk.</p><div class="grid">{blog_html}</div></section></main>
<script>
const cards=[...document.querySelectorAll('.prod')],secs=[...document.querySelectorAll('.cat')],chips=[...document.querySelectorAll('.chip')];
let cat='all',q='';
function apply(){{let any=false;cards.forEach(c=>{{const ok=c.textContent.toLowerCase().includes(q);c.hidden=!ok}});
secs.forEach(s=>{{const vis=(cat==='all'||s.dataset.c===cat)&&[...s.querySelectorAll('.prod')].some(c=>!c.hidden);s.hidden=!vis;any=any||vis}});
document.getElementById('none').hidden=any}}
document.getElementById('q').oninput=e=>{{q=e.target.value.toLowerCase();apply()}};
chips.forEach(b=>b.onclick=()=>{{cat=b.dataset.c;chips.forEach(x=>x.classList.toggle('on',x===b));apply()}});
</script>"""
    (OUT / "index.html").write_text(page(SITE["name"] + " - Parenting, Baby Picks & Everyday Finds", body), encoding="utf-8")
    for p in ps_:
        b = f'<main class="post-page"><small>{p["date"]}</small><h1>{esc(p["title"])}</h1>{p["body"]}</main>'
        (OUT / f"blog/{p['slug']}.html").write_text(page(p["title"], b, 1), encoding="utf-8")
    print(f"built: {len(vids)} videos, {len(products)} products in {len(groups)} sections, {len(ps_)} posts")

if __name__ == "__main__":
    main()
