"""Builds the static site (docs/) from data/raw.jsonl (video descriptions) + posts/*.md.
Run: python build.py   (or ./fetch.sh to re-pull descriptions from YouTube + product photos first)

Pages generated: home, articles list + every article, a page for each product category, a page for each product,
feed.xml, sitemap.xml, robots.txt, 404.html.
Any "Name: https://link" line in a video description becomes a product, auto-sorted into a category by keywords in the name.
Articles: posts/YYYY-MM-DD-slug.md  ->  "# Title", then optional lines "Category:", "Description:", "Products: kw, kw"."""
import datetime, html, json, os, re, shutil
from pathlib import Path
from urllib.parse import quote
import markdown

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
SITE = {
    "name": "Ankushali Vlogs",
    "tagline": "Real parenting, everyday finds & Kushu ki masti. Everything we use, in one place.",
    "url": "https://ankushalivlogs.github.io",
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
CAT_INFO = {  # intro paragraph + "before you buy" checklist for each category page / product page
    "Baby Feeding": ("Feeding gear and first foods can feel overwhelming. These are the feeding products that appear in our family vlogs, with links so you can check them yourself.",
        ["Check the age range printed on the pack", "Match nipple size and neck type to your bottle, and start with a slow flow", "Choose food-safe, BPA-free materials", "Introduce one new food at a time, and ask your paediatrician when to start solids", "Replace nipples when they crack, tear or turn sticky"]),
    "Baby Care & Diapers": ("Diapers and baby-care basics are things you will use every single day. Here are the ones we use and mention in our vlogs.",
        ["Choose the size by baby's weight, not age", "Tape diapers suit newborns, pull-up pants suit crawling babies", "Look for a soft inner layer and a wetness indicator", "Buy a small pack first to check the fit", "Change often to help prevent rashes"]),
    "Play & Gear": ("Mats, toys and ride-ons for play time, as seen in our vlogs. Always check age limits and supervise play.",
        ["Follow the age and weight limits on the pack", "Pick wipe-clean, non-toxic materials for mats", "Avoid wheeled baby walkers and ask your paediatrician for safer options", "Look for rounded edges and no small detachable parts", "Supervise play, always"]),
    "Nursery & Storage": ("Wardrobes and storage that keep a baby's things organised. These are the pieces you will spot in our home vlogs.",
        ["Anchor tall furniture to the wall", "Check the weight limit of each shelf", "Air out new plastic for a day or two before use", "Measure the space before you order", "Keep heavy items low and the next clothing size handy"]),
    "Mics & Audio": ("Clear sound makes a video feel professional. These are the audio products we mention in our vlogs.",
        ["Pick the mic type for your use: lapel for walking vlogs, shotgun for on-camera", "Check the connector (3.5 mm, USB-C or Lightning) fits your phone or camera", "Look for wind protection if you shoot outdoors", "Compare battery life for wireless sets", "Read recent reviews for build quality"]),
    "Laptops & Computers": ("The computers and desk accessories that help us edit and manage our channel.",
        ["Choose RAM and storage for your work: 8 GB and an SSD at minimum for editing", "Check ports and weight if you travel", "Compare screen quality, not just size", "Look for warranty and a service centre nearby", "Pick accessories like mouse pads that fit your desk"]),
    "Camera & Creator Gear": ("Cameras and creator gear we use to film our family vlogs.",
        ["Match the camera to your style: action cam for movement, pocket gimbal for walking shots", "Check stabilisation and low-light performance", "Plan memory cards and spare batteries", "Buy only the accessories you will actually use", "Test the audio quality too"]),
    "Shoes & Fashion": ("Everyday shoes and fashion picks from our videos.",
        ["Check the size chart and recent reviews on fit", "Look at the return and exchange policy", "Choose breathable, comfortable materials", "Compare with similar styles before you buy"]),
    "Home & Decor": ("Decor and home items from our room makeover and home vlogs.",
        ["Measure walls and furniture first", "Choose child-safe, stable frames and hang them securely", "Pick washable fabrics for covers", "Match colours across the room", "Check delivery and return policy for fragile items"]),
    "Kitchen": ("Kitchen helpers we use at home.",
        ["Check capacity against your family size", "Look for easy-clean, food-safe materials", "Check the power rating and warranty", "Make sure service is available in your area"]),
    "Beauty & Personal Care": ("Personal-care picks from our everyday routine.",
        ["Patch test new products first", "Check ingredients if you have sensitive skin", "Check the expiry or batch date on delivery", "For hair tools, choose adjustable heat settings", "Buy from the brand's official seller"]),
    "Phones & Gadgets": ("Phones and gadgets we use day to day.",
        ["Compare battery life and charging speed", "Check the warranty and service options", "Look for official accessories", "Read recent reviews"]),
    "Books & Learning": ("Books and learning picks we like.",
        ["Check the age or level", "Preview a sample if you can", "Choose editions with clear print"]),
    "More Finds": ("Other products we mention in our vlogs.",
        ["Read the listing carefully: size, age range and what is in the box", "Check recent reviews and ratings", "Compare with similar products", "Confirm the return policy"]),
}
ART_CATS = [("Babies", "👶"), ("Toddlers", "🧸"), ("Kids", "🎒"), ("Teens", "🎧"), ("Parents", "💛")]  # article categories
SKIP_DOMAINS = ("youtube.com", "youtu.be", "instagram.com", "facebook.com", "twitter.com", "x.com", "wa.me", "t.me")
GENERIC = "Product from this video"
NAV_CATS = []  # [(label, icon, slug)] filled in main(); used by the footer
esc = html.escape

ICO_IG = '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>'
ICO_FB = '<svg class="ico" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M14 8V6.5c0-.7.2-1 1.1-1H17V2h-2.6C11.5 2 10 3.7 10 6.2V8H7.5v3.5H10V22h4V11.5h2.7L17 8z"/></svg>'

def category(name, title=""):
    n = name.lower()
    for label, icon, ks in CATS:
        if any(k in n for k in ks):
            return label, icon
    if title:  # label gave no clue: try the store's listing title
        t = title.lower()
        for label, icon, ks in CATS:
            if any(k in t for k in ks):
                return label, icon
    return FALLBACK

def store(link):
    return next((s for k, s in (("amazon", "Amazon"), ("amzn", "Amazon"), ("flipkart", "Flipkart"), ("fkrt", "Flipkart"),
                                ("myntra", "Myntra"), ("meesho", "Meesho")) if k in link), "")

def nice(d):  # 20261023 -> 23 Oct 2026
    return datetime.datetime.strptime(d, "%Y%m%d").strftime("%d %b %Y")

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def short_title(t, n=64):
    t = re.split(r"[,|(–—]| - ", t)[0].strip()
    return (t[:n].rsplit(" ", 1)[0] if len(t) > n else t) or GENERIC

def kfmt(n):
    return f"{n/1000:.1f}K".replace(".0K", "K") if n >= 1000 else str(n)

def shrink(u, n=420):  # Amazon serves any size: ask for the size we need instead of the 1200-1500px originals
    return re.sub(r"\._[A-Z]{2}\d+_\.", "._SL%d_." % n, u) if "media-amazon.com" in u else u

def thumb(src, alt="", n=420):
    if not src:
        return '<div class="pimg ph">&#128717;</div>'
    return f'<img class="pimg" loading="lazy" decoding="async" width="{n}" height="{n}" referrerpolicy="no-referrer" src="{esc(shrink(src, n))}" alt="{esc(alt)}">'

def jload(rel):
    f = ROOT / rel
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

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
            name = re.sub(r"^[^\w]+", "", (m.group(1) or "")).strip() or GENERIC
            p = products.setdefault(link, {"name": name, "link": link, "vids": []})
            if p["name"] == GENERIC and name != p["name"]:
                p["name"] = name
            p["vids"].append(r["id"])
            vp.append(link)
        vids.append({**r, "plinks": vp, "short": "/shorts/" in (r["webpage_url"] or "") or (r["duration"] or 999) <= 60})
    return vids, products

WAVE = """<div class="wave"><svg class="rocket" viewBox="0 0 64 96" aria-hidden="true"><path d="M32 4C44 18 48 40 44 64H20C16 40 20 18 32 4Z" fill="#fff"/><circle cx="32" cy="34" r="7" fill="#7b5cc4"/><path d="M20 52 8 72l14-6zM44 52l12 20-14-6z" fill="#e8607a"/><path d="M26 66h12l-6 24z" fill="#fbbf4a"/></svg>
<svg viewBox="0 0 1440 160" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="wg" x1="0" x2="1"><stop offset="0" stop-color="#f4a261"/><stop offset=".5" stop-color="#e8607a"/><stop offset="1" stop-color="#7b5cc4"/></linearGradient></defs>
<path d="M0 90C220 20 380 130 700 90S1180 10 1440 70V160H0Z" fill="url(#wg)"/></svg></div>"""

COMMON_JS = """<script>
(function(){var b=document.querySelector('.mbar');if(b){var f=function(){b.classList.toggle('show',scrollY>380)};addEventListener('scroll',f,{passive:true});f()}
document.querySelectorAll('[data-copy]').forEach(function(a){a.onclick=function(e){e.preventDefault();var t=a.dataset.copy;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){a.textContent='Link copied!'},function(){prompt('Copy this link',t)})}})})();
</script>"""

def mbar_default(r):
    return f'<nav class="mbar" aria-label="Quick actions"><a class="s" href="{r}index.html#vlogs">&#9654; Watch vlogs</a><a class="p" href="{r}index.html#products">&#128717; Shop our picks</a></nav>'

def page(title, body, depth=0, desc=None, path="", image=None, ld=None, kind="website", published=None, mbar=None, extra_js=""):
    r = "../" * depth
    desc = desc or "Parenting tips and honest guides, plus the baby, home and everyday products we use, as seen in the Ankushali Vlogs family vlogs."
    url = f"{SITE['url']}/{path}"
    image = image or f"{SITE['url']}/og.png"
    ldj = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (ld or []))
    pub = f'<meta property="article:published_time" content="{published}">' if published else ""
    catlinks = "".join(f'<a href="{r}category/{s}.html">{esc(l)}</a>' for l, i, s in NAV_CATS)
    return f"""<!doctype html><html lang="en-IN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}"><meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{url}"><meta name="theme-color" content="#7b5cc4"><script>document.documentElement.className="js"</script>
<link rel="icon" type="image/png" href="{r}img/favicon.png"><link rel="apple-touch-icon" href="{r}img/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="{esc(SITE['name'])} articles" href="{r}feed.xml">
<meta property="og:site_name" content="{esc(SITE['name'])}"><meta property="og:type" content="{kind}"><meta property="og:locale" content="en_IN">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{esc(image)}">{pub}
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(desc)}"><meta name="twitter:image" content="{esc(image)}">
{ldj}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://i.ytimg.com"><link rel="preconnect" href="https://m.media-amazon.com">
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Nunito:wght@400;600;700&display=swap" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Nunito:wght@400;600;700&display=swap"></noscript>
<link rel="stylesheet" href="{r}style.css"></head><body>
<div class="topbar">&#127873; Honest picks from our family vlogs &middot; <a href="{r}index.html#products">See what we use &rarr;</a></div>
<header><a class="brand" href="{r}index.html">{esc(SITE['name'])}</a>
<nav><a href="{r}index.html#vlogs">Vlogs</a><a href="{r}index.html#products">Products</a><a href="{r}articles.html">Articles</a>
<a class="soc" href="{SITE['instagram']}" aria-label="Instagram" target="_blank" rel="noopener">{ICO_IG}</a>
<a class="soc" href="{SITE['facebook']}" aria-label="Facebook" target="_blank" rel="noopener">{ICO_FB}</a></nav>
<a class="navbtn" href="{SITE['youtube']}">Subscribe</a></header>
{body}
<section class="join"><img src="{r}img/banner-sticker.webp" alt="Ankushali Vlogs family: Ankur, Vaishali and baby Kushu" width="1500" height="600" loading="lazy" decoding="async">
<h2>Join the Ankushali family</h2><p>Family vlogs, real parenting tips and the products we use. New videos every week.</p>
<div class="btns"><a class="gbtn shine" href="{SITE['youtube']}">Subscribe on YouTube</a><a class="ghost" href="{SITE['instagram']}">Instagram</a><a class="ghost" href="{SITE['facebook']}">Facebook</a></div></section>
{WAVE}
<footer><div class="fgrid"><div><div class="brand">{esc(SITE['name'])}</div><p>{esc(SITE['tagline'])}</p></div>
<div><h5>Explore</h5><a href="{r}index.html#vlogs">Vlogs</a><a href="{r}index.html#products">Products</a><a href="{r}articles.html">Articles</a><a href="{r}feed.xml">RSS feed</a></div>
<div><h5>Shop by category</h5>{catlinks}</div>
<div><h5>Follow</h5><a href="{SITE['youtube']}">YouTube</a><a href="{SITE['instagram']}">Instagram</a><a href="{SITE['facebook']}">Facebook</a></div></div>
<p class="fine">As an Amazon Associate we earn from qualifying purchases. Product links are affiliate links; they cost you nothing extra. Shared from our own experience, not medical advice: please check with your doctor for health questions.</p>
<p class="fine">&copy; {esc(SITE['name'])}</p></footer>
{mbar if mbar is not None else mbar_default(r)}
{COMMON_JS}{extra_js}</body></html>"""

def catbar(prefix, arts, active=None):
    items = "".join(f'<a href="{prefix}articles.html#{slug(c)}" data-c="{slug(c)}"{" class=on" if c == active else ""}>{i} {c}</a>' for c, i in ART_CATS)
    return f'<div class="catbar"><a href="{prefix}articles.html#all" data-c="all">All articles</a>{items}</div>'

def posts():
    out = []
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    today = os.environ.get("PREVIEW_ALL") and "9999" or datetime.datetime.now(ist).strftime("%Y-%m-%d")
    for f in sorted((ROOT / "posts").glob("*.md"), reverse=True):
        if f.stem[:10] > today:  # scheduled for a future date: not published yet
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        title = lines[0].lstrip("# ").strip()
        rest, kw, cat, desc = lines[1:], [], "Parents", ""
        while rest and re.match(r"(products|category|description):", rest[0], re.I):
            k, v = rest[0].split(":", 1)
            if k.lower() == "products":
                kw = [x.strip().lower() for x in v.split(",") if x.strip()]
            elif k.lower() == "description":
                desc = v.strip()
            else:
                cat = v.strip().title()
            rest = rest[1:]
        md = "\n".join(rest).strip()
        out.append({"slug": f.stem[11:], "date": f.stem[:10], "title": title, "kw": kw, "cat": cat, "desc": desc,
                    "excerpt": re.sub(r"[*_`#>]", "", md.split("\n\n")[0]).strip(),
                    "mins": max(1, round(len(md.split()) / 200)), "body": markdown.markdown(md)})
    return out

# ----------------------------------------------------------------------------------------------------------------
JS_HOME = """<script>
const cards=[...document.querySelectorAll('.prod')],chips=[...document.querySelectorAll('.chip')],pt=document.getElementById('ptrack');
let cat='all',q='';
function apply(){let n=0;cards.forEach(c=>{const ok=(cat==='all'||c.dataset.c===cat)&&c.textContent.toLowerCase().includes(q);c.hidden=!ok;n+=ok});
document.getElementById('none').hidden=n>0;pt.scrollLeft=0}
document.getElementById('q').oninput=e=>{q=e.target.value.toLowerCase();apply()};
const tr=document.getElementById('vtrack'),vs=[...tr.children];
function vrender(){const t=document.getElementById('vtype').value,k=document.getElementById('vsort').value;
const key={new:a=>-a.dataset.date,old:a=>+a.dataset.date,views:a=>-a.dataset.views}[k];
vs.sort((a,b)=>key(a)-key(b)).forEach(c=>{c.hidden=t!=='all'&&c.dataset.type!==t;tr.appendChild(c)});tr.scrollLeft=0}
document.getElementById('vtype').onchange=document.getElementById('vsort').onchange=vrender;
document.getElementById('vprev').onclick=()=>tr.scrollBy({left:-tr.clientWidth*.8,behavior:'smooth'});
document.getElementById('vnext').onclick=()=>tr.scrollBy({left:tr.clientWidth*.8,behavior:'smooth'});
document.getElementById('pprev').onclick=()=>pt.scrollBy({left:-pt.clientWidth*.8,behavior:'smooth'});
document.getElementById('pnext').onclick=()=>pt.scrollBy({left:pt.clientWidth*.8,behavior:'smooth'});
chips.forEach(b=>b.onclick=()=>{cat=b.dataset.c;chips.forEach(x=>x.classList.toggle('on',x===b));apply()});
/* watch & shop modal */
const dlg=document.getElementById('vmodal'),vf=document.getElementById('vframe'),vmp=document.getElementById('vmprods');
function closeV(){vf.innerHTML='';if(dlg.open)dlg.close()}
tr.addEventListener('click',e=>{const a=e.target.closest('.vthumb');if(!a||!dlg.showModal||e.metaKey||e.ctrlKey)return;e.preventDefault();
const c=a.closest('.vid'),id=c.dataset.id,ps=JSON.parse(c.dataset.prods||'[]');
vf.className='vframe'+(c.dataset.type==='short'?' short':'');
vf.innerHTML='<iframe src="https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1&rel=0" title="'+c.dataset.title.replace(/"/g,'&quot;')+'" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>';
document.getElementById('vmtitle').textContent=c.dataset.title;document.getElementById('vmyt').href=a.href;
vmp.innerHTML=ps.length?ps.map(p=>'<a class="vmp" href="'+p.l+'" target="_blank" rel="sponsored noopener">'+(p.i?'<img src="'+p.i+'" alt="" width="54" height="54" referrerpolicy="no-referrer">':'')+'<span><b>'+p.n.replace(/</g,'&lt;')+'</b><small>Check price'+(p.s?' on '+p.s:'')+' &rarr;</small></span></a>').join(''):'<p class="vmnone">No products listed for this video.</p>';
document.getElementById('vmh').hidden=!ps.length;dlg.showModal()});
document.querySelector('.mclose').onclick=closeV;dlg.addEventListener('close',()=>{vf.innerHTML=''});
dlg.addEventListener('click',e=>{if(e.target===dlg)closeV()});
const rm=matchMedia('(prefers-reduced-motion:reduce)').matches;
if(!rm){const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{threshold:.1});
document.querySelectorAll('main .sh,.vtools,#q,.chips,.carousel,.tiles,.featgrid,.more,.faq details').forEach(el=>{el.classList.add('rv');io.observe(el)});
document.querySelectorAll('.stat b[data-n]').forEach(b=>{const n=+b.dataset.n;let t0;b.textContent='0';
const step=t=>{t0=t0||t;const k=Math.min((t-t0)/1100,1);b.textContent=Math.round(n*(1-Math.pow(1-k,3))).toLocaleString('en-IN');if(k<1)requestAnimationFrame(step)};setTimeout(()=>requestAnimationFrame(step),500)});
const hw=document.querySelector('.herowrap');hw.addEventListener('pointermove',e=>{const r=hw.getBoundingClientRect();hw.style.setProperty('--px',((e.clientX-r.left)/r.width-.5)*2);hw.style.setProperty('--py',((e.clientY-r.top)/r.height-.5)*2)})}
</script>"""

def main():
    global NAV_CATS
    vids, products = load()
    imgs, titles = jload("data/images.json"), jload("data/titles.json")
    arts = posts()
    byid = {v["id"]: v for v in vids}
    for d in ("blog", "articles", "category", "products"):
        shutil.rmtree(OUT / d, ignore_errors=True)  # drop pages of unpublished/removed items
        if d != "blog":
            (OUT / d).mkdir(parents=True, exist_ok=True)
    (OUT / ".nojekyll").write_text("")

    # ---- enrich products
    used, plist = {}, []
    for link, p in products.items():
        t = titles.get(link, "")
        if p["name"] == GENERIC and t:
            p["name"] = short_title(t)
        p.update(title=t, img=imgs.get(link), vids=list(dict.fromkeys(p["vids"])), store=store(link))
        p["nv"] = len(p["vids"])
        p["cat"] = category(p["name"], t)
        base = slug(p["name"]) or "product"
        used[base] = used.get(base, 0) + 1
        p["slug"] = base if used[base] == 1 else f"{base}-{used[base]}"
        hay = (p["name"] + " " + t).lower()
        p["arts"] = [a for a in arts if any(k in hay for k in a["kw"])]
        plist.append(p)
    groups = {}
    for p in plist:
        groups.setdefault(p["cat"], []).append(p)
    order = [(l, i) for l, i, _ in CATS] + [FALLBACK]
    groups = [(k, groups[k]) for k in order if k in groups]
    NAV_CATS = [(l, i, slug(l)) for (l, i), ps in groups]
    total_views = sum(v["view_count"] or 0 for v in vids)
    long_v = [v for v in vids if not v["short"]]

    # ---- reusable cards
    def buy_text(p):
        return f'Check price on {p["store"]}' if p["store"] else "Check price"

    def prod_card(p, r="", show_cat=True, seen=True):
        rib = f'In {p["nv"]} vlogs' if p["nv"] > 1 else "Seen in our vlog"
        href = f'{r}products/{p["slug"]}.html'
        cat_attr = f' data-c="{slug(p["cat"][0])}"' if show_cat else ""
        seen_html = f'<small>Seen in: {esc(byid[p["vids"][0]]["title"][:46])}</small>' if seen and p["vids"] else ""
        tag = f'<span class="tag">{p["cat"][1]} {esc(p["cat"][0])}</span>' if show_cat else ""
        return (f'<article class="card prod"{cat_attr}><a class="pimgwrap" href="{href}" aria-label="{esc(p["name"])} details">{thumb(p["img"], p["name"])}'
                f'<span class="ribbon">&#9654; {rib}</span></a>{tag}<b><a class="pn" href="{href}">{esc(p["name"])}</a></b>{seen_html}'
                f'<div class="cta"><a class="buy" href="{esc(p["link"])}" rel="sponsored noopener" target="_blank">{buy_text(p)} &rarr;</a><a class="dtl" href="{href}">Details</a></div></article>')

    def feat_card(p, n):
        rib = f'Featured in {p["nv"]} vlogs' if p["nv"] > 1 else "Seen in our vlog"
        href = f'products/{p["slug"]}.html'
        return (f'<article class="feat"><span class="badge">{"&#127942; Parent favourite" if n == 0 else "&#11088; Top pick"}</span>'
                f'<a class="pimgwrap" href="{href}" aria-label="{esc(p["name"])} details">{thumb(p["img"], p["name"], 520)}</a>'
                f'<small class="fcat">{p["cat"][1]} {esc(p["cat"][0])} &middot; {rib}</small><h3><a href="{href}">{esc(p["name"])}</a></h3>'
                f'<div class="cta"><a class="buy" href="{esc(p["link"])}" rel="sponsored noopener" target="_blank">{buy_text(p)} &rarr;</a><a class="dtl" href="{href}">Details</a></div></article>')

    def athumb(a, big=False, r=""):
        rel = [x for x in plist if any(k in (x["name"] + " " + x["title"]).lower() for k in a["kw"])]
        img = next((x["img"] for x in rel if x["img"]), None)
        inner = (f'<img src="{esc(shrink(img, 760 if big else 420))}" alt="{esc(a["title"])}" loading="lazy" decoding="async" referrerpolicy="no-referrer">' if img
                 else f'<span>{dict(ART_CATS).get(a["cat"], "📖")}</span>')
        return f'<div class="athumb c-{slug(a["cat"])}">{inner}</div>', img

    def acard(a, pre="articles/"):
        return (f'<a class="card post" data-cat="{slug(a["cat"])}" href="{pre}{a["slug"]}.html">{athumb(a)[0]}<small>{esc(a["cat"])} &middot; {a["date"]} &middot; {a["mins"]} min read</small>'
                f'<b>{esc(a["title"])}</b><span class="ex">{esc(a["excerpt"][:140])}...</span><span class="go">Read article &rarr;</span></a>')

    def share_box(title, path):
        u = f"{SITE['url']}/{path}"
        return (f'<div class="share"><span>Share:</span><a class="wa" href="https://wa.me/?text={quote(title + " " + u)}" target="_blank" rel="noopener">WhatsApp</a>'
                f'<a class="cp" href="#" data-copy="{u}">Copy link</a></div>')

    def vcard(v):
        pl = [products[l] for l in v["plinks"] if l in products]
        data = [{"n": products[l]["name"], "l": l, "s": products[l]["store"] or "",
                 "i": shrink(products[l]["img"], 120) if products[l]["img"] else ""} for l in dict.fromkeys(v["plinks"])]
        links = "".join(f'<a href="{esc(l)}" rel="sponsored noopener" target="_blank">{esc(products[l]["name"])}</a>' for l in dict.fromkeys(v["plinks"]))
        return (f'<article class="card vid" data-id="{v["id"]}" data-date="{v["upload_date"]}" data-views="{v["view_count"] or 0}" data-type="{"short" if v["short"] else "video"}" '
                f'data-title="{esc(v["title"])}" data-prods="{esc(json.dumps(data, ensure_ascii=False))}">'
                f'<a class="vthumb" href="{esc(v["webpage_url"])}" aria-label="Watch: {esc(v["title"])}"><img loading="lazy" decoding="async" '
                f'src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="{esc(v["title"])}" width="480" height="360" onerror="this.onerror=null;this.src=&quot;img/family-sticker.webp&quot;;this.classList.add(&quot;nothumb&quot;)"><span class="play" aria-hidden="true"></span></a>'
                f'<h4>{esc(v["title"])}</h4><small>{"Short" if v["short"] else "Video"} &middot; {nice(v["upload_date"])}' + (f' &middot; {kfmt(v["view_count"])} views' if v["view_count"] else "") + '</small>'
                + (f'<div class="plinks">{links}</div>' if links else "") + "</article>")

    # ---- HOME ---------------------------------------------------------------------------------------------
    fl = json.loads((ROOT / "data/floaties.json").read_text(encoding="utf-8"))
    floaties = "".join(f'<div class="f f{n}" style="--r:{r}deg"><span style="--d:{d}px">{fl[k]}</span></div>'
                       for n, (k, r, d) in enumerate([("teddy", 7, -14), ("rocket", 12, 22), ("bottle", -10, -18)], 1))
    words = ["Parenting", "tips", "&amp;", "baby", "products", "we", "actually", "use"]
    h1w = "".join(("<em>" if k == 6 else "") + f'<span class="w" style="--i:{k}">{w}</span> ' + ("</em>" if k == 7 else "") for k, w in enumerate(words))
    chips_m = ["👶 Babies", "🧸 Toddlers", "🎒 Kids", "🎧 Teens", "💛 Parents", "🍼 Feeding tips", "🛏️ Safe sleep", "🧷 Diaper guides", "🎥 Family vlogs", "🛍️ Products we use"]
    marq = "".join(f"<span>{c}</span>" for c in chips_m * 2)
    chips = '<button class="chip on" data-c="all">All <small>%d</small></button>' % len(plist) + "".join(
        f'<button class="chip" data-c="{slug(l)}">{i} {esc(l)} <small>{len(ps)}</small></button>' for (l, i), ps in groups)
    ptrack = ('<div class="carousel"><button class="arrow prev" id="pprev" aria-label="Previous">&lsaquo;</button><div class="track" id="ptrack">'
              + "".join(prod_card(p) for (l, i), ps in groups for p in ps)
              + '</div><button class="arrow next" id="pnext" aria-label="Next">&rsaquo;</button></div>')
    tiles = "".join(f'<a class="tile" href="category/{slug(l)}.html"><span class="ti">{i}</span><b>{esc(l)}</b><small>{len(ps)} product{"s" if len(ps) != 1 else ""}</small></a>' for (l, i), ps in groups)
    top = [p for p in sorted(plist, key=lambda p: -p["nv"]) if p["img"]][:3]
    featgrid = "".join(feat_card(p, n) for n, p in enumerate(top))
    latest = "".join(acard(a) for a in arts[:3]) or "<p>Coming soon.</p>"
    faq = [("Are these affiliate links?", "Yes. When you buy through our links we may earn a small commission from the store, at no extra cost to you. It helps us keep making our vlogs and guides."),
           ("Do you really use these products?", "These are the products we mention in our family vlogs. Each product shows which vlog it appears in, so you can see it in real life before you decide."),
           ("How do I find a product from a video?", "Tap any vlog above to watch it here, and the products from that video are listed right under the player. You can also search or filter the product list."),
           ("Is the parenting advice medical advice?", "No. Our articles share general information and our own experience as parents. Please ask your doctor or paediatrician about anything health related."),
           ("How often do you add new content?", "We upload new vlogs every week, and new parenting articles are added regularly.")]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
    body = f"""<div class="herowrap"><div class="aurora" aria-hidden="true"><i></i><i></i><i></i></div>
<section class="hero"><div class="hcopy"><span class="pill">&#10024; For parents &amp; parents-to-be</span>
<h1 class="split">{h1w}</h1><p class="lead">{esc(SITE['tagline'])}</p>
<div class="btns"><a class="gbtn shine" href="#vlogs">Watch our vlogs</a><a class="ghost" href="#products">Shop our picks</a></div>
<div class="strip"><div class="stat"><b data-n="{len(plist)}">{len(plist)}</b><small>Products</small></div>
<div class="stat"><b data-n="{len(vids)}">{len(vids)}</b><small>Videos</small></div><div class="stat"><b data-n="{len(arts)}">{len(arts)}</b><small>Articles</small></div>
<div class="stat"><b data-n="{total_views}">{total_views:,}</b><small>Views</small></div>
<a class="gbtn" href="#products">Browse products</a></div>
<ul class="trust"><li>Real products from our vlogs</li><li>Honest picks, no fake reviews</li><li>Same price for you</li></ul></div>
<div class="hvis"><img class="hphoto" src="img/family-sticker.webp" alt="Ankur, Vaishali and baby Kushu of Ankushali Vlogs" width="900" height="900" fetchpriority="high" decoding="async"><div class="floaties" aria-hidden="true">{floaties}</div></div></section></div>
<div class="marquee" aria-hidden="true"><div class="mtrack">{marq}</div></div>
<main><section id="vlogs"><div class="sh"><span class="eyebrow">Watch &amp; shop</span><h2>Our vlogs</h2><p class="sub">Tap a video to watch it here. The products from that video are listed right under the player.</p></div>
<div class="vtools"><label>Show <select id="vtype"><option value="all">All videos</option><option value="video">Vlogs</option><option value="short">Shorts</option></select></label>
<label>Sort by <select id="vsort"><option value="new">Newest first</option><option value="old">Oldest first</option><option value="views">Most viewed</option></select></label></div>
<div class="carousel"><button class="arrow" id="vprev" aria-label="Previous">&lsaquo;</button><div class="track" id="vtrack">{''.join(vcard(v) for v in vids)}</div><button class="arrow" id="vnext" aria-label="Next">&rsaquo;</button></div></section>
<section class="panel warm" id="top-picks"><div class="sh"><span class="eyebrow">Parent favourites</span><h2>Top picks from our vlogs</h2><p class="sub">The products that show up most in our videos.</p></div><div class="featgrid">{featgrid}</div></section>
<section id="categories"><div class="sh"><span class="eyebrow">Shop by category</span><h2>What are you looking for?</h2></div><div class="tiles">{tiles}</div></section>
<section id="products"><div class="sh"><span class="eyebrow">All products</span><h2>Everything we use</h2><p class="sub">Baby must-haves, gadgets, audio, shoes and more. Pick a section or search.</p></div>
<input id="q" placeholder="Search products..." aria-label="Search products"><div class="chips">{chips}</div>{ptrack}<p id="none" hidden>Nothing found. Try another word.</p></section>
<section id="articles"><div class="sh"><span class="eyebrow">Guides</span><h2>Parenting articles</h2><p class="sub">Why parents choose these products, and what to know before you buy.</p></div><div class="grid">{latest}</div>
<p class="more"><a class="gbtn" href="articles.html">See all articles</a></p></section>
<section id="faq"><div class="sh"><span class="eyebrow">Good to know</span><h2>Questions parents ask</h2></div><div class="faq">{faq_html}</div></section></main>
<dialog id="vmodal" aria-label="Video player"><button class="mclose" aria-label="Close video">&times;</button><div class="vframe" id="vframe"></div>
<div class="vmbody"><h3 id="vmtitle"></h3><h4 id="vmh">Products from this video</h4><div class="vmprods" id="vmprods"></div><a class="ghost" id="vmyt" href="#" target="_blank" rel="noopener">Watch on YouTube</a></div></dialog>
{JS_HOME}"""
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    org = {"@type": "Organization", "name": SITE["name"], "url": SITE["url"] + "/", "logo": SITE["url"] + "/img/apple-touch-icon.png", "sameAs": [SITE["youtube"], SITE["instagram"], SITE["facebook"]]}
    home_ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE["name"], "url": SITE["url"] + "/", "inLanguage": "en-IN"}, {"@context": "https://schema.org", **org}, faq_ld]
    (OUT / "index.html").write_text(page(SITE["name"] + " | Parenting Tips, Baby Products & Family Vlogs", body,
        desc="Honest parenting guides for babies, toddlers, kids and teens, plus the baby and everyday products we use in our family vlogs. Real tips for parents and parents-to-be.",
        path="", ld=home_ld), encoding="utf-8")

    # ---- ARTICLES LIST ------------------------------------------------------------------------------------
    lst = (catbar("", arts) + '<main><h1 class="ptitle">Parenting articles</h1><p class="sub">Why parents choose these products, and what to know before you buy.</p>'
           f'<div class="grid" id="agrid">{"".join(acard(a) for a in arts)}</div><p id="anone" hidden>No articles here yet. Check back soon!</p></main>'
           """<script>function show(){const h=location.hash.slice(1)||'all';let n=0;document.querySelectorAll('#agrid .card').forEach(c=>{const ok=h==='all'||c.dataset.cat===h;c.hidden=!ok;n+=ok});
document.getElementById('anone').hidden=n>0;document.querySelectorAll('.catbar a').forEach(a=>a.classList.toggle('on',a.dataset.c===h))}
addEventListener('hashchange',show);show()</script>""")
    (OUT / "articles.html").write_text(page("Parenting Articles: Babies, Toddlers, Kids & Teens | " + SITE["name"], lst,
        desc="Practical parenting articles on newborns, babies, toddlers, kids, teens and new-parent life, plus why parents choose common baby products.",
        path="articles.html", ld=[{"@context": "https://schema.org", "@type": "CollectionPage", "name": "Parenting articles", "url": SITE["url"] + "/articles.html"}]), encoding="utf-8")

    urls = [SITE["url"] + "/", SITE["url"] + "/articles.html"]

    # ---- ARTICLES -----------------------------------------------------------------------------------------
    for a in arts:
        rel = [x for x in plist if any(k in (x["name"] + " " + x["title"]).lower() for k in a["kw"])]
        related = (f'<section class="related"><h2>Products from our vlogs</h2><div class="grid">{"".join(prod_card(x, "../", False, False) for x in rel)}</div></section>' if rel else "")
        more = sorted([x for x in arts if x is not a], key=lambda x: x["cat"] != a["cat"])
        morehtml = f'<section class="related"><h2>More parenting articles</h2><div class="grid">{"".join(acard(x, "") for x in more[:3])}</div></section>' if more else ""
        path = f"articles/{a['slug']}.html"
        thumb_html, photo = athumb(a, True)
        b = (catbar("../", arts, a["cat"]) + f'<main class="post-page"><p class="crumb"><a href="../articles.html">&larr; All articles</a></p><small><time datetime="{a["date"]}">{a["date"]}</time> &middot; {a["mins"]} min read</small>'
             f'<div class="abig">{thumb_html}</div><h1>{esc(a["title"])}</h1>{share_box(a["title"], path)}{a["body"]}{share_box(a["title"], path)}'
             f'<aside class="author"><img src="../img/family-sticker.webp" alt="" width="96" height="96" loading="lazy" decoding="async"><div><b>Written by the Ankushali Vlogs family</b><p>Ankur, Vaishali and little Kushu share what they learn as parents. This is general information, not medical advice. Please ask your doctor about health questions.</p><a href="{SITE["youtube"]}">Watch our family vlogs &rarr;</a></div></aside>{related}{morehtml}</main>')
        d = a["desc"] or a["excerpt"][:155]
        ld = [{"@context": "https://schema.org", "@type": "Article", "headline": a["title"], "description": d, "inLanguage": "en-IN",
               "datePublished": a["date"], "dateModified": a["date"], "mainEntityOfPage": f"{SITE['url']}/{path}",
               "image": [photo or SITE["url"] + "/og.png"], "author": {"@type": "Organization", "name": SITE["name"], "url": SITE["url"] + "/"},
               "publisher": {"@type": "Organization", "name": SITE["name"], "url": SITE["url"] + "/"}},
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE["url"] + "/"},
                  {"@type": "ListItem", "position": 2, "name": "Articles", "item": SITE["url"] + "/articles.html"},
                  {"@type": "ListItem", "position": 3, "name": a["title"], "item": f"{SITE['url']}/{path}"}]}]
        (OUT / path).write_text(page(f"{a['title']} | {SITE['name']}", b, 1, desc=d, path=path, image=photo, ld=ld, kind="article", published=a["date"]), encoding="utf-8")
        urls.append(f"{SITE['url']}/{path}")

    # ---- CATEGORY PAGES -----------------------------------------------------------------------------------
    for (label, icon), ps in groups:
        intro, check = CAT_INFO.get(label, CAT_INFO["More Finds"])
        cs = slug(label); path = f"category/{cs}.html"
        arts_here = list(dict.fromkeys(a["slug"] for p in ps for a in p["arts"]))
        arts_html = (f'<section class="related"><h2>Guides to read first</h2><div class="grid">{"".join(acard(a, "../articles/") for a in arts if a["slug"] in arts_here)}</div></section>' if arts_here else "")
        others = "".join(f'<a class="chip" href="{slug(l)}.html">{i} {esc(l)}</a>' for (l, i), _ in groups if l != label)
        checklist = "".join(f"<li>{esc(c)}</li>" for c in check)
        b = (f'<main class="catpage"><p class="crumb"><a href="../index.html">Home</a> &rsaquo; <a href="../index.html#products">Products</a> &rsaquo; {esc(label)}</p>'
             f'<div class="cathead"><span class="ti">{icon}</span><div><h1>Best {esc(label)} We Use</h1><p class="lead2">{esc(intro)}</p></div></div>'
             f'<div class="grid pgrid">{"".join(prod_card(p, "../", False, False) for p in ps)}</div>'
             f'<section class="panel"><h2>Before you buy: {esc(label.lower())} checklist</h2><ul class="checklist">{checklist}</ul></section>{arts_html}'
             f'<section class="related"><h2>More categories</h2><div class="chips">{others}</div></section></main>')
        ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE["url"] + "/"},
                {"@type": "ListItem", "position": 2, "name": label, "item": f"{SITE['url']}/{path}"}]},
              {"@context": "https://schema.org", "@type": "CollectionPage", "name": f"Best {label} We Use", "url": f"{SITE['url']}/{path}"}]
        first_img = next((p["img"] for p in ps if p["img"]), None)
        (OUT / path).write_text(page(f"Best {label} We Use: Picks From Our Family Vlogs | {SITE['name']}", b, 1,
            desc=f"{intro} {len(ps)} product{'s' if len(ps) != 1 else ''} we mention in our vlogs, with a buying checklist.", path=path,
            image=shrink(first_img, 760) if first_img else None, ld=ld), encoding="utf-8")
        urls.append(f"{SITE['url']}/{path}")

    # ---- PRODUCT PAGES ------------------------------------------------------------------------------------
    for p in plist:
        label, icon = p["cat"]
        intro, check = CAT_INFO.get(label, CAT_INFO["More Finds"])
        path = f"products/{p['slug']}.html"
        vl = [byid[i] for i in p["vids"] if i in byid]
        vids_html = "".join(
            f'<a class="card vmini" href="{esc(v["webpage_url"])}" target="_blank" rel="noopener"><span class="vt"><img loading="lazy" decoding="async" src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="{esc(v["title"])}" width="480" height="360" '
            f'onerror="this.onerror=null;this.src=&quot;../img/family-sticker.webp&quot;;this.classList.add(&quot;nothumb&quot;)"><span class="play" aria-hidden="true"></span></span><b>{esc(v["title"][:80])}</b><small>{nice(v["upload_date"])}</small></a>' for v in vl[:6])
        same = [x for x in plist if x["cat"] == p["cat"] and x is not p][:4]
        arts_html = (f'<section class="related"><h2>Read before you buy</h2><div class="grid">{"".join(acard(a, "../articles/") for a in p["arts"][:3])}</div></section>' if p["arts"] else "")
        same_html = (f'<section class="related"><h2>More in {esc(label)}</h2><div class="grid pgrid">{"".join(prod_card(x, "../", False, False) for x in same)}</div></section>' if same else "")
        listing = f'<p class="listing"><b>Listing on {p["store"] or "the store"}:</b> {esc(p["title"] if len(p["title"]) < 130 else p["title"][:130].rsplit(" ", 1)[0] + "…")}</p>' if p["title"] and p["title"].lower() != p["name"].lower() else ""
        big = thumb(p["img"], p["name"], 760).replace('loading="lazy"', 'fetchpriority="high"')
        buy = f'<a class="buy lg" href="{esc(p["link"])}" rel="sponsored noopener" target="_blank">{buy_text(p)} &rarr;</a>'
        b = (f'<main class="prodpage"><p class="crumb"><a href="../index.html">Home</a> &rsaquo; <a href="../category/{slug(label)}.html">{esc(label)}</a> &rsaquo; {esc(p["name"])}</p>'
             f'<div class="pp"><div class="bigimg">{big}</div><div class="pinfo"><span class="tag">{icon} {esc(label)}</span><h1>{esc(p["name"])}</h1>'
             f'<p class="seen">&#9654; {"Featured in %d of our vlogs" % p["nv"] if p["nv"] > 1 else "Seen in one of our vlogs"}</p>{listing}'
             f'<div class="buyrow">{buy}</div><p class="aff">Affiliate link: we may earn a small commission at no extra cost to you.</p>{share_box(p["name"] + " | " + SITE["name"], path)}'
             f'<h2>Before you buy</h2><ul class="checklist">{"".join(f"<li>{esc(c)}</li>" for c in check)}</ul></div></div>'
             + (f'<section class="related"><h2>See it in our vlogs</h2><div class="grid vgrid">{vids_html}</div></section>' if vids_html else "")
             + arts_html + same_html + '</main>')
        ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE["url"] + "/"},
                {"@type": "ListItem", "position": 2, "name": label, "item": f"{SITE['url']}/category/{slug(label)}.html"},
                {"@type": "ListItem", "position": 3, "name": p["name"], "item": f"{SITE['url']}/{path}"}]}]
        mb = f'<nav class="mbar" aria-label="Buy"><a class="p" href="{esc(p["link"])}" rel="sponsored noopener" target="_blank">{buy_text(p)} &rarr;</a></nav>'
        (OUT / path).write_text(page(f"{p['name']}: Where We Used It & What To Check | {SITE['name']}", b, 1,
            desc=f"{p['name']} as seen in our family vlogs. Watch it in use, read our buying checklist and check the price on {p['store'] or 'the store'}.", path=path,
            image=shrink(p["img"], 760) if p["img"] else None, ld=ld, mbar=mb), encoding="utf-8")
        urls.append(f"{SITE['url']}/{path}")

    # ---- feed, sitemap, robots, 404 -----------------------------------------------------------------------
    today = datetime.date.today().isoformat()
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE['url']}/sitemap.xml\n", encoding="utf-8")
    items = "".join(f"<item><title>{esc(a['title'])}</title><link>{SITE['url']}/articles/{a['slug']}.html</link><guid>{SITE['url']}/articles/{a['slug']}.html</guid>"
                    f"<pubDate>{datetime.datetime.strptime(a['date'], '%Y-%m-%d').strftime('%a, %d %b %Y 06:00:00 +0530')}</pubDate><description>{esc(a['desc'] or a['excerpt'][:200])}</description></item>" for a in arts)
    (OUT / "feed.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{esc(SITE["name"])} articles</title><link>{SITE["url"]}/</link>'
        f'<description>{esc(SITE["tagline"])}</description><language>en-IN</language>{items}</channel></rss>\n', encoding="utf-8")
    (OUT / "404.html").write_text(page("Page not found | " + SITE["name"], '<main style="text-align:center;padding:80px 18px"><h1>Oops, page not found</h1><p>The page may have moved. Try our <a href="/articles.html">parenting articles</a> or go back <a href="/">home</a>.</p></main>', 0, path="404.html", mbar="")
        .replace('<meta name="robots" content="index,follow,max-image-preview:large">', '<meta name="robots" content="noindex">').replace('href="style.css"', 'href="/style.css"')
        .replace('href="index.html', 'href="/index.html').replace('href="articles.html', 'href="/articles.html').replace('href="category/', 'href="/category/').replace('href="img/', 'href="/img/').replace('src="img/', 'src="/img/').replace('href="feed.xml', 'href="/feed.xml'), encoding="utf-8")
    print(f"built: {len(vids)} videos, {len(plist)} products ({len(groups)} categories), {len(arts)} articles, {len(urls)} URLs")

if __name__ == "__main__":
    main()
