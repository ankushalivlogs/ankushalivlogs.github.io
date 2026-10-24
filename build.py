"""Builds the static site (docs/) from data/raw.jsonl (video descriptions) + posts/*.md.
Run: python build.py   (or ./fetch.sh to re-pull descriptions from YouTube + product photos first)
Any "Name: https://link" line in a video description becomes a product, auto-sorted into a section by keywords in the name.
Articles: posts/YYYY-MM-DD-slug.md  ->  line 1 "# Title", optional line 2 "Products: keyword, keyword" (shows matching products below)."""
import html, json, re, shutil
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
SITE = {
    "name": "Ankushali Vlogs",
    "tagline": "Real parenting, everyday finds & Kushu ki masti. Everything we use, in one place.",
    "youtube": "https://www.youtube.com/@Ankushali_Vlogs",
    "instagram": "https://www.instagram.com/ankushali_",
    "facebook": "https://www.facebook.com/profile.php?id=61586491452811",
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
ART_CATS = [("Babies", "👶"), ("Toddlers", "🧸"), ("Kids", "🎒"), ("Teens", "🎧"), ("Parents", "💛")]  # article categories
SKIP_DOMAINS = ("youtube.com", "youtu.be", "instagram.com", "facebook.com", "twitter.com", "x.com", "wa.me", "t.me")
esc = html.escape

ICO_IG = '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>'
ICO_FB = '<svg class="ico" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M14 8V6.5c0-.7.2-1 1.1-1H17V2h-2.6C11.5 2 10 3.7 10 6.2V8H7.5v3.5H10V22h4V11.5h2.7L17 8z"/></svg>'

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
        vids.append({**r, "plinks": vp, "short": "/shorts/" in (r["webpage_url"] or "") or (r["duration"] or 999) <= 60})
    return vids, products

WAVE = """<div class="wave"><svg class="rocket" viewBox="0 0 64 96" aria-hidden="true"><path d="M32 4C44 18 48 40 44 64H20C16 40 20 18 32 4Z" fill="#fff"/><circle cx="32" cy="34" r="7" fill="#7b5cc4"/><path d="M20 52 8 72l14-6zM44 52l12 20-14-6z" fill="#e8607a"/><path d="M26 66h12l-6 24z" fill="#fbbf4a"/></svg>
<svg viewBox="0 0 1440 160" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="wg" x1="0" x2="1"><stop offset="0" stop-color="#f4a261"/><stop offset=".5" stop-color="#e8607a"/><stop offset="1" stop-color="#7b5cc4"/></linearGradient></defs>
<path d="M0 90C220 20 380 130 700 90S1180 10 1440 70V160H0Z" fill="url(#wg)"/></svg></div>"""

def page(title, body, depth=0):
    r = "../" * depth
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<meta name="description" content="Honest parenting articles and the baby, home and everyday products we use, as seen in our vlogs.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Nunito:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}style.css"></head><body>
<header><a class="brand" href="{r}index.html">{esc(SITE['name'])}</a>
<nav><a href="{r}index.html#products">Products</a><a href="{r}index.html#vlogs">Vlogs</a><a href="{r}articles.html">Articles</a>
<a class="soc" href="{SITE['instagram']}" aria-label="Instagram" target="_blank" rel="noopener">{ICO_IG}</a>
<a class="soc" href="{SITE['facebook']}" aria-label="Facebook" target="_blank" rel="noopener">{ICO_FB}</a>
<a class="navbtn" href="{SITE['youtube']}">Subscribe</a></nav></header>
{body}
{WAVE}
<footer><div class="fgrid"><div><div class="brand">{esc(SITE['name'])}</div><p>{esc(SITE['tagline'])}</p></div>
<div><h5>Explore</h5><a href="{r}index.html#products">Products</a><a href="{r}index.html#vlogs">Vlogs</a><a href="{r}articles.html">Articles</a></div>
<div><h5>Follow</h5><a href="{SITE['youtube']}">YouTube</a><a href="{SITE['instagram']}">Instagram</a><a href="{SITE['facebook']}">Facebook</a></div></div>
<p class="fine">As an Amazon Associate we earn from qualifying purchases. Product links are affiliate links; they cost you nothing extra. Shared from our own experience, not medical advice: please check with your doctor for health questions.</p>
<p class="fine">&copy; {esc(SITE['name'])}</p></footer></body></html>"""

def catbar(prefix, arts, active=None):
    n = lambda c: sum(1 for a in arts if a["cat"] == c)
    items = "".join(f'<a href="{prefix}articles.html#{slug(c)}" data-c="{slug(c)}"{" class=on" if c == active else ""}>{i} {c}</a>' for c, i in ART_CATS)
    return f'<div class="catbar"><a href="{prefix}articles.html#all" data-c="all">All articles</a>{items}</div>'

def posts():
    out = []
    for f in sorted((ROOT / "posts").glob("*.md"), reverse=True):
        lines = f.read_text(encoding="utf-8").splitlines()
        title = lines[0].lstrip("# ").strip()
        rest, kw, cat = lines[1:], [], "Parents"
        while rest and re.match(r"(products|category):", rest[0], re.I):
            k, v = rest[0].split(":", 1)
            if k.lower() == "products":
                kw = [x.strip().lower() for x in v.split(",") if x.strip()]
            else:
                cat = v.strip().title()
            rest = rest[1:]
        md = "\n".join(rest).strip()
        out.append({"slug": f.stem[11:], "date": f.stem[:10], "title": title, "kw": kw, "cat": cat,
                    "excerpt": re.sub(r"[*_`#>]", "", md.split("\n\n")[0]).strip(),
                    "mins": max(1, round(len(md.split()) / 200)), "body": markdown.markdown(md)})
    return out

def main():
    vids, products = load()
    shutil.rmtree(OUT / "blog", ignore_errors=True)  # old URL
    (OUT / "articles").mkdir(parents=True, exist_ok=True)
    (OUT / ".nojekyll").write_text("")
    byid = {v["id"]: v for v in vids}
    imgs_f = ROOT / "data/images.json"
    imgs = json.loads(imgs_f.read_text()) if imgs_f.exists() else {}

    def prod_card(p, seen=True):
        return (f'<a class="card prod" href="{esc(p["link"])}" rel="sponsored noopener" target="_blank">'
                f'{thumb(imgs.get(p["link"]))}<b>{esc(p["name"])}</b>'
                + (f'<small>Seen in: {esc(byid[p["vids"][0]]["title"][:46])}</small>' if seen else "")
                + f'<span class="go">View on {store(p["link"])} &rarr;</span></a>')

    groups = {}
    for p in products.values():
        groups.setdefault(category(p["name"]), []).append(p)
    order = [(l, i) for l, i, _ in CATS] + [FALLBACK]
    groups = [(k, groups[k]) for k in order if k in groups]

    chips = '<button class="chip on" data-c="all">All <small>%d</small></button>' % len(products) + "".join(
        f'<button class="chip" data-c="{slug(l)}">{i} {esc(l)} <small>{len(ps)}</small></button>' for (l, i), ps in groups)
    sections = "".join(
        f'<section class="cat" data-c="{slug(l)}"><h3>{i} {esc(l)}</h3><div class="grid">' + "".join(prod_card(p) for p in ps) + "</div></section>"
        for (l, i), ps in groups)

    def vcard(v):
        links = "".join(f'<a href="{esc(l)}" rel="sponsored noopener" target="_blank">{esc(products[l]["name"])}</a>' for l in v["plinks"])
        return (f'<article class="card vid" data-date="{v["upload_date"]}" data-views="{v["view_count"] or 0}" data-type="{"short" if v["short"] else "video"}"><a href="{esc(v["webpage_url"])}"><img loading="lazy" '
                f'src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt=""></a>'
                f'<h4>{esc(v["title"])}</h4><small>{"Short" if v["short"] else "Video"} &middot; {v["upload_date"]}</small>'
                + (f'<div class="plinks">{links}</div>' if links else "") + "</article>")
    long_v = [v for v in vids if not v["short"]]
    short_v = [v for v in vids if v["short"]]
    arts = posts()

    def acard(p):
        return (f'<a class="card post" data-cat="{slug(p["cat"])}" href="articles/{p["slug"]}.html"><small>{esc(p["cat"])} &middot; {p["date"]} &middot; {p["mins"]} min read</small>'
                f'<b>{esc(p["title"])}</b><span class="ex">{esc(p["excerpt"][:140])}...</span><span class="go">Read article &rarr;</span></a>')
    latest = "".join(acard(p) for p in arts[:3]) or "<p>Coming soon.</p>"

    body = f"""<section class="hero"><span class="pill">&#10024; For parents &amp; parents-to-be</span>
<h1>Find what we <em>actually use</em></h1><p>{esc(SITE['tagline'])}</p>
<div class="strip"><div class="stat"><b>{len(products)}</b><small>Products</small></div>
<div class="stat"><b>{len(long_v) + len(short_v)}</b><small>Videos</small></div><div class="stat"><b>{len(arts)}</b><small>Articles</small></div>
<p>Spotted in our vlogs, explained in our articles</p><a class="gbtn" href="#products">Browse products</a></div></section>
<main><section id="products"><h2>Meet our favourite finds</h2><p class="sub">Baby must-haves, gadgets, audio, shoes and more. Pick a section or search.</p>
<input id="q" placeholder="Search products..." aria-label="Search products"><div class="chips">{chips}</div>{sections}<p id="none" hidden>Nothing found. Try another word.</p></section>
<section id="vlogs"><h2>Our vlogs</h2><p class="sub">Every video, with the products from its description.</p>
<div class="vtools"><label>Show <select id="vtype"><option value="all">All videos</option><option value="video">Vlogs</option><option value="short">Shorts</option></select></label>
<label>Sort by <select id="vsort"><option value="new">Newest first</option><option value="old">Oldest first</option><option value="views">Most viewed</option></select></label></div>
<div class="carousel"><button class="arrow" id="vprev" aria-label="Previous">&lsaquo;</button><div class="track" id="vtrack">{''.join(vcard(v) for v in vids)}</div><button class="arrow" id="vnext" aria-label="Next">&rsaquo;</button></div></section>
<section id="articles"><h2>Parenting articles</h2><p class="sub">Why parents choose these products, and what to know before you buy.</p><div class="grid">{latest}</div>
<p class="more"><a class="gbtn" href="articles.html">See all articles</a></p></section></main>
<script>
const cards=[...document.querySelectorAll('.prod')],secs=[...document.querySelectorAll('.cat')],chips=[...document.querySelectorAll('.chip')];
let cat='all',q='';
function apply(){{let any=false;cards.forEach(c=>{{const ok=c.textContent.toLowerCase().includes(q);c.hidden=!ok}});
secs.forEach(s=>{{const vis=(cat==='all'||s.dataset.c===cat)&&[...s.querySelectorAll('.prod')].some(c=>!c.hidden);s.hidden=!vis;any=any||vis}});
document.getElementById('none').hidden=any}}
document.getElementById('q').oninput=e=>{{q=e.target.value.toLowerCase();apply()}};
const tr=document.getElementById('vtrack'),vs=[...tr.children];
function vrender(){{const t=document.getElementById('vtype').value,k=document.getElementById('vsort').value;
const key={{new:a=>-a.dataset.date,old:a=>+a.dataset.date,views:a=>-a.dataset.views}}[k];
vs.sort((a,b)=>key(a)-key(b)).forEach(c=>{{c.hidden=t!=='all'&&c.dataset.type!==t;tr.appendChild(c)}});tr.scrollLeft=0}}
document.getElementById('vtype').onchange=document.getElementById('vsort').onchange=vrender;
document.getElementById('vprev').onclick=()=>tr.scrollBy({{left:-tr.clientWidth*.8,behavior:'smooth'}});
document.getElementById('vnext').onclick=()=>tr.scrollBy({{left:tr.clientWidth*.8,behavior:'smooth'}});
chips.forEach(b=>b.onclick=()=>{{cat=b.dataset.c;chips.forEach(x=>x.classList.toggle('on',x===b));apply()}});
</script>"""
    (OUT / "index.html").write_text(page(SITE["name"] + " - Parenting, Baby Products & Everyday Finds", body), encoding="utf-8")

    lst = (catbar("", arts) + '<main><h1 class="ptitle">Parenting articles</h1><p class="sub">Why parents choose these products, and what to know before you buy.</p>'
           f'<div class="grid" id="agrid">{"".join(acard(p) for p in arts)}</div><p id="anone" hidden>No articles here yet. Check back soon!</p></main>'
           """<script>function show(){const h=location.hash.slice(1)||'all';let n=0;document.querySelectorAll('#agrid .card').forEach(c=>{const ok=h==='all'||c.dataset.cat===h;c.hidden=!ok;n+=ok});
document.getElementById('anone').hidden=n>0;document.querySelectorAll('.catbar a').forEach(a=>a.classList.toggle('on',a.dataset.c===h))}
addEventListener('hashchange',show);show()</script>""")
    (OUT / "articles.html").write_text(page("Articles - " + SITE["name"], lst), encoding="utf-8")

    for p in arts:
        rel = [x for x in products.values() if any(k in x["name"].lower() for k in p["kw"])]
        related = (f'<section class="related"><h2>Products from our vlogs</h2><div class="grid">{"".join(prod_card(x, False) for x in rel)}</div></section>' if rel else "")
        b = (catbar("../", arts, p["cat"]) + f'<main class="post-page"><p class="crumb"><a href="../articles.html">&larr; All articles</a></p><small>{p["date"]} &middot; {p["mins"]} min read</small>'
             f'<h1>{esc(p["title"])}</h1>{p["body"]}{related}</main>')
        (OUT / f"articles/{p['slug']}.html").write_text(page(p["title"], b, 1), encoding="utf-8")
    print(f"built: {len(vids)} videos, {len(products)} products in {len(groups)} sections, {len(arts)} articles")

if __name__ == "__main__":
    main()
