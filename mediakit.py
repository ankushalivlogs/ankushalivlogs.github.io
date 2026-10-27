"""Builds the brand-collaboration media kit: docs/media-kit.html (+ docs/Ankushali-Vlogs-Media-Kit.pdf via Chrome).
Numbers for YouTube come from data/raw.jsonl (real). Edit data/mediakit.json for contact details and Instagram numbers.
Run: python mediakit.py"""
import datetime, html, json, subprocess, sys
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0, str(Path(__file__).parent))
import build as B

ROOT = B.ROOT; OUT = B.OUT; esc = html.escape
CFG = {"email": "ankushalivlogs@gmail.com", "whatsapp": "918171933692", "whatsapp_display": "+91 81719 33692", "location": "Aligarh, Uttar Pradesh",
       "ig_followers": "1.1K", "ig_posts": "94", "ig_avg_likes": "257", "ig_avg_comments": "14", "ig_top_likes": "3.6K", "response": "within 12 hours"}
CFG.update(json.loads((ROOT / "data/mediakit.json").read_text(encoding="utf-8")) if (ROOT / "data/mediakit.json").exists() else {})
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def main():
    vids, products = B.load()
    imgs, titles = B.jload("data/images.json"), B.jload("data/titles.json")
    longv = [v for v in vids if not v["short"]]; shortv = [v for v in vids if v["short"]]
    tv = sum(v["view_count"] or 0 for v in vids)
    best = max(vids, key=lambda v: v["view_count"] or 0)
    recent = longv[:8]; avg_recent = round(sum(v["view_count"] or 0 for v in recent) / max(1, len(recent)))
    top = sorted(vids, key=lambda v: -(v["view_count"] or 0))[:4]
    plist = []
    for link, p in products.items():
        name = B.short_title(titles[link]) if p["name"] == B.GENERIC and titles.get(link) else p["name"]
        if imgs.get(link):
            plist.append((len(set(p["vids"])), name, imgs[link], B.category(name, titles.get(link, ""))[0]))
    plist.sort(key=lambda x: -x[0]); plist = plist[:8]
    today = datetime.date.today().strftime("%B %Y")
    mail = f"mailto:{CFG['email']}?subject={quote('Collaboration with Ankushali Vlogs')}&body={quote('Hi Ankur & Vaishali,%0A%0AWe are [brand] and would love to collaborate.%0AProduct / campaign:%0ATimeline:%0ABudget:%0A'.replace('%0A', chr(10)))}"
    wa = f"https://wa.me/{CFG['whatsapp']}?text={quote('Hi Ankushali Vlogs team, we found your media kit and would like to discuss a collaboration with our brand.')}"

    stat = lambda n, l: f'<div class="st"><b>{n}</b><span>{l}</span></div>'
    stats = (stat(f"{len(vids)}", "videos & Shorts published") + stat(f"{tv:,}", "total YouTube views") + stat(B.kfmt(best["view_count"] or 0), "views on our best video")
             + stat(B.kfmt(avg_recent), "avg views, latest 8 vlogs") + stat(CFG["ig_followers"], "Instagram followers") + stat(CFG["ig_avg_likes"], "avg likes per reel"))
    topcards = "".join(
        f'<a class="vc" href="{esc(v["webpage_url"])}" target="_blank" rel="noopener"><span class="th"><img src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'"><i>&#9654;</i></span>'
        f'<b>{esc(v["title"][:70])}</b><small>{"Short" if v["short"] else "Vlog"} &middot; {B.kfmt(v["view_count"] or 0)} views</small></a>' for v in top)
    prodcards = "".join(f'<div class="pc"><img src="{esc(B.shrink(i, 300))}" alt="{esc(n)}" loading="lazy" referrerpolicy="no-referrer"><b>{esc(n[:42])}</b><small>{esc(c)} &middot; in {k} vlog{"s" if k != 1 else ""}</small></div>' for k, n, i, c in plist)
    pillars = [("&#127868;", "Baby care routines", "Bath, massage, feeding and sleep routines as they really happen at home."),
               ("&#129529;", "Honest product use", "Diapers, wipes, oils, feeding gear and nursery items shown in daily use."),
               ("&#128118;", "Milestones & firsts", "First foods, doctor visits, play and little wins with Kushu."),
               ("&#127968;", "Family lifestyle", "Home, festivals, travel and the everyday rituals of a young Indian family.")]
    pil = "".join(f'<div class="card"><span class="ic">{i}</span><h3>{t}</h3><p>{d}</p></div>' for i, t, d in pillars)
    services = [("Product feature in a vlog", "Natural placement in a family vlog: bath time, feeding, play or home routines.", ["Mention + on-screen use", "Link in description and pinned comment", "Product shown in our website 'Products' section"]),
                ("Dedicated review video", "A full 8 to 12 minute family review on YouTube with honest first impressions.", ["Script reviewed with you", "Description link + pinned comment", "Cut-down Short for reach"]),
                ("Instagram Reel + Story set", "A 30 to 60 second reel plus follow-up stories with your link.", ["1 reel, 3 story frames", "Collab post on request", "Saves & shares focused"]),
                ("Parenting tip collaboration", "Vaishali shares routines and tips with your product woven in, with a doctor-check reminder.", ["Educational angle", "Written article on our site", "Evergreen search traffic"]),
                ("Long-term ambassador", "Repeat integrations across 3 to 6 months for a story that builds trust.", ["Monthly content plan", "Priority slots", "Performance recap each month"])]
    svc = "".join(f'<div class="card sv"><h3>{t}</h3><p>{d}</p><ul>{"".join(f"<li>{x}</li>" for x in l)}</ul></div>' for t, d, l in services)
    steps = [("Brief", "Share your product, goal and timeline."), ("Fit check", "We confirm the product suits our baby and audience."), ("Plan", "Concept and talking points agreed together."),
             ("Shoot", "Natural light, real home, no scripted shouting."), ("Review", "You see the draft before it goes live."), ("Publish & report", "Live links plus a results summary.")]
    stp = "".join(f'<li><b>{i}</b><div><h4>{t}</h4><p>{d}</p></div></li>' for i, (t, d) in enumerate(steps, 1))
    faq = [("Do you disclose paid partnerships?", "Always. Sponsored posts are clearly marked, as required by Indian advertising rules."),
           ("Will you try a product before promoting it?", "Yes. For baby products we check ingredients and age suitability first, and we only feature items that are safe for Kushu."),
           ("What do you not promote?", "Anything unsafe for babies, medical claims, or products we have not used."),
           ("Can you share results?", "Yes. After publishing we share views, saves and link clicks where the platform provides them."),
           ("What are your rates?", "They depend on format and usage rights. Send a short brief and we reply with options and a quote.")]
    fq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
    ld = {"@context": "https://schema.org", "@type": "WebPage", "name": "Ankushali Vlogs Media Kit", "url": f"{B.SITE['url']}/media-kit.html"}

    page = f"""<!doctype html><html lang="en-IN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brand Collaboration Media Kit | Ankushali Vlogs</title><meta name="description" content="Collaborate with Ankushali Vlogs: a family and baby-care channel from Aligarh with real parent trust. Stats, formats, audience and contact.">
<link rel="canonical" href="{B.SITE['url']}/media-kit.html"><meta property="og:title" content="Ankushali Vlogs: Brand Collaboration Media Kit"><meta property="og:description" content="Family, parenting and baby care content that young Indian parents trust.">
<meta property="og:image" content="{B.SITE['url']}/og.png"><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="img/favicon.png">
<script type="application/ld+json">{json.dumps(ld)}</script>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;1,500&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#fdf8ee;--ink:#231f2e;--mut:#6b6478;--line:#eadfc8;--card:#fff;--gold:#c7931b;--yel:#ffd400;--plum:#5b3fa0;--rose:#c93d62}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 Manrope,system-ui,sans-serif}}
h1,h2,h3,h4{{font-family:'Playfair Display',serif;font-weight:500;margin:0}}a{{color:inherit}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 22px}}
nav.top{{position:sticky;top:0;z-index:10;background:rgba(253,248,238,.9);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}}
nav.top .wrap{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-top:10px;padding-bottom:10px}}
.logo{{display:flex;align-items:center;gap:10px;text-decoration:none;font:600 15px Manrope}}.logo img{{width:38px;height:38px}}.logo small{{display:block;font-weight:500;color:var(--mut);font-size:11px;letter-spacing:.12em}}
nav.top .links{{display:flex;gap:20px;font-size:13px;font-weight:600;color:var(--mut)}}nav.top .links a{{text-decoration:none}}nav.top .links a:hover{{color:var(--ink)}}
.btn{{display:inline-flex;align-items:center;gap:8px;border-radius:99px;padding:11px 22px;font:700 14px Manrope;text-decoration:none;border:2px solid var(--ink);color:var(--ink);background:transparent;transition:transform .2s,box-shadow .2s}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 18px rgba(35,31,46,.15)}}.btn.dark{{background:var(--ink);color:#fff}}.btn.wa{{background:#128c4a;border-color:#128c4a;color:#fff}}.btn.sm{{padding:8px 16px;font-size:13px}}
.hero{{display:grid;grid-template-columns:1.1fr .9fr;gap:30px;align-items:center;padding:56px 0 36px}}
.eyebrow{{display:inline-flex;gap:8px;align-items:center;font:700 11px Manrope;letter-spacing:.16em;text-transform:uppercase;color:var(--gold);border:1px solid var(--line);background:#fff;border-radius:99px;padding:5px 14px}}.eyebrow:before{{content:"";width:7px;height:7px;border-radius:50%;background:#2fb26a}}
.hero h1{{font-size:clamp(46px,8vw,92px);line-height:.98;margin:18px 0 12px}}.hero h1 em{{display:block;color:var(--plum)}}
.pillars{{display:flex;gap:12px;flex-wrap:wrap;font:700 11px Manrope;letter-spacing:.16em;color:var(--mut);margin:0 0 16px}}
.lead{{font-size:19px;color:#443d52;max-width:560px}}.lead b{{color:var(--ink)}}
.roles{{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}}.role{{border-radius:16px;padding:10px 16px;font-size:13px;background:#fff;border:1px solid var(--line)}}.role small{{display:block;font:700 10px Manrope;letter-spacing:.14em;color:var(--gold)}}
.cta{{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}}
.hvis{{position:relative;text-align:center}}.hvis img{{width:min(100%,470px);height:auto;filter:drop-shadow(0 22px 30px rgba(91,63,160,.25));animation:fl 7s ease-in-out infinite}}@keyframes fl{{50%{{transform:translateY(-10px) rotate(1deg)}}}}
.stats{{display:grid;grid-template-columns:repeat(6,1fr);gap:0;background:#fff;border:1px solid var(--line);border-radius:26px;margin:10px 0 0;overflow:hidden}}
.st{{padding:22px 14px;text-align:center;border-right:1px solid var(--line)}}.st:last-child{{border:0}}.st b{{display:block;font:600 clamp(24px,3.2vw,36px) 'Playfair Display';color:var(--plum)}}.st span{{font-size:12px;color:var(--mut);line-height:1.3;display:block}}
section{{padding:56px 0 0}}.sec-h{{margin-bottom:22px}}.kick{{font:700 11px Manrope;letter-spacing:.18em;text-transform:uppercase;color:var(--gold)}}.sec-h h2{{font-size:clamp(28px,4.4vw,42px);line-height:1.12;margin-top:6px}}.sec-h p{{color:var(--mut);max-width:620px;margin:8px 0 0}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:26px}}.card{{background:#fff;border:1px solid var(--line);border-radius:22px;padding:22px}}.card h3{{font-size:20px;margin:6px 0}}.card p{{margin:0;color:var(--mut);font-size:15px}}
.ic{{display:grid;place-items:center;width:44px;height:44px;border-radius:14px;background:#fff6d6;font-size:22px}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
.quote{{background:linear-gradient(135deg,#fff6d6,#f1eaff);border:1px solid var(--line);border-radius:26px;padding:26px}}.quote p{{font:500 22px/1.45 'Playfair Display';margin:0}}
.vc{{display:flex;flex-direction:column;gap:6px;text-decoration:none;background:#fff;border:1px solid var(--line);border-radius:20px;overflow:hidden;padding-bottom:14px;transition:transform .2s}}.vc:hover{{transform:translateY(-4px)}}
.th{{position:relative;display:block;aspect-ratio:16/9;background:#eee}}.th img{{width:100%;height:100%;object-fit:cover;display:block}}.th i{{position:absolute;inset:0;display:grid;place-items:center;font-style:normal;color:#fff;font-size:26px;text-shadow:0 2px 8px rgba(0,0,0,.5)}}
.vc b{{font:600 14px/1.35 Manrope;padding:0 14px}}.vc small{{padding:0 14px;color:var(--mut)}}
.pc{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:12px;display:flex;flex-direction:column;gap:4px}}.pc img{{width:100%;aspect-ratio:1;object-fit:contain;background:#fff;border-radius:12px}}.pc b{{font-size:13px;line-height:1.3}}.pc small{{color:var(--mut);font-size:12px}}
.sv ul{{margin:12px 0 0;padding:0;list-style:none}}.sv li{{padding:4px 0 4px 22px;position:relative;font-size:14px}}.sv li:before{{content:"\\2713";position:absolute;left:0;color:#2fb26a;font-weight:700}}
.steps{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(3,1fr);gap:14px;counter-reset:s}}.steps li{{display:flex;gap:14px;background:#fff;border:1px solid var(--line);border-radius:20px;padding:16px}}.steps b{{flex:none;display:grid;place-items:center;width:34px;height:34px;border-radius:50%;background:var(--ink);color:#fff;font-size:14px}}.steps h4{{font:600 16px Manrope}}.steps p{{margin:2px 0 0;color:var(--mut);font-size:14px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:20px;overflow:hidden}}th,td{{text-align:left;padding:14px 18px;border-bottom:1px solid var(--line);font-size:14px}}th{{font:700 11px Manrope;letter-spacing:.14em;color:var(--gold);text-transform:uppercase;background:#fffaf0}}tr:last-child td{{border:0}}
details{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:14px 18px;margin:10px 0}}summary{{cursor:pointer;font:600 16px Manrope;list-style:none}}summary::-webkit-details-marker{{display:none}}summary:after{{content:"+";float:right;color:var(--gold);font-size:22px;line-height:1}}details[open] summary:after{{content:"\\2013"}}details p{{margin:8px 0 0;color:var(--mut)}}
.contact{{background:var(--ink);color:#fff;border-radius:32px;padding:40px;display:grid;grid-template-columns:1.2fr 1fr;gap:30px;margin-top:56px}}.contact h2{{font-size:clamp(30px,5vw,48px);line-height:1.08}}.contact p{{color:#cfc9dc}}
.contact .row{{display:flex;justify-content:space-between;align-items:center;gap:10px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);border-radius:16px;padding:14px 18px;text-decoration:none;margin-bottom:10px}}.contact .row b{{font-weight:600}}.contact .row span{{font:700 11px Manrope;letter-spacing:.14em;color:var(--yel)}}
footer{{padding:34px 0 40px;color:var(--mut);font-size:12px;letter-spacing:.06em;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}}footer a{{text-decoration:none;margin-left:14px}}
.rv{{opacity:0;transform:translateY(22px);transition:opacity .7s,transform .7s}}.rv.in{{opacity:1;transform:none}}
@media(max-width:900px){{.hero,.two,.contact{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(3,1fr)}}.st:nth-child(3){{border-right:0}}.st{{border-bottom:1px solid var(--line)}}.grid4{{grid-template-columns:1fr 1fr}}.grid3,.steps{{grid-template-columns:1fr}}nav.top .links{{display:none}}.hvis{{order:-1}}.hvis img{{width:min(80%,340px)}}.contact{{padding:26px}}table{{display:block;overflow-x:auto;white-space:normal}}th,td{{min-width:130px}}}}
@media print{{@page{{size:A4;margin:10mm}}nav.top,.btn.sm,.cta{{display:none!important}}.rv{{opacity:1!important;transform:none!important}}body{{background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}}section,.card,.vc,.pc,details,.steps li,.st{{break-inside:avoid}}.hvis img{{animation:none}}details p{{display:block}}.hero{{padding-top:10px}}}}
@media(prefers-reduced-motion:reduce){{.rv{{opacity:1;transform:none;transition:none}}.hvis img{{animation:none}}}}
</style></head><body>
<nav class="top"><div class="wrap"><a class="logo" href="#top"><img src="img/apple-touch-icon.png" alt=""><span>ANKUSHALI VLOGS<small>ANKUR &amp; VAISHALI</small></span></a>
<div class="links"><a href="#numbers">Numbers</a><a href="#work">Our work</a><a href="#audience">Audience</a><a href="#services">Collaborate</a><a href="#faq">FAQ</a></div>
<a class="btn dark sm" href="{mail}">{esc(CFG['email'])} &nearr;</a></div></nav>
<main class="wrap" id="top">
<div class="hero"><div><span class="eyebrow">Open for brand collaborations</span><h1>Ankushali <em>Vlogs</em></h1>
<div class="pillars"><span>FAMILY</span><span>&middot;</span><span>PARENTING</span><span>&middot;</span><span>BABY CARE</span></div>
<p class="lead">A heart-led family storytelling channel documenting life with <b>Kushu</b>: honest baby care, mindful parenting and the everyday rituals that family brands can trust.</p>
<div class="roles"><div class="role"><small>ANKUR</small>Papa &middot; Storyteller</div><div class="role"><small>VAISHALI</small>Mamma &middot; Care Curator</div><div class="role"><small>KUSHAGRA</small>Kushu &middot; Heart of the channel</div></div>
<div class="cta"><a class="btn dark" href="{mail}">Email us</a><a class="btn wa" href="{wa}" target="_blank" rel="noopener">WhatsApp {esc(CFG['whatsapp_display'])}</a><a class="btn" href="Ankushali-Vlogs-Media-Kit.pdf" download>Download PDF</a></div></div>
<div class="hvis"><img src="img/family-sticker.webp" alt="Ankur, Vaishali and baby Kushu" width="900" height="900"></div></div>
<div class="stats rv" id="numbers">{stats}</div>
<p style="font-size:12px;color:var(--mut);margin:8px 4px 0">YouTube numbers are taken from our public channel and refreshed {today}. Instagram figures are from our professional dashboard.</p>

<section class="rv"><div class="two"><div class="sec-h"><span class="kick">About</span><h2>Gentle parenting, told like a family album.</h2>
<p>Ankushali Vlogs is run by Ankur and Vaishali from {esc(CFG['location'])}, sharing real moments with their baby boy Kushagra. The content is calm, clean and useful, from daily baby-care routines to honest first-time-parent learnings. No noise, no drama.</p></div>
<div class="quote"><p>&ldquo;Our viewers are young Indian parents who are actively buying for their baby. They save our routines and message us for product links.&rdquo;</p><small style="color:var(--mut)">Why brands choose us: baby care, diapers and wipes, feeding, nursery, mother and child, family lifestyle.</small></div></div></section>

<section class="rv"><div class="sec-h"><span class="kick">What we create</span><h2>Four content pillars</h2></div><div class="grid4">{pil}</div></section>

<section class="rv" id="work"><div class="sec-h"><span class="kick">Our work</span><h2>Real videos. Real products. Real parents.</h2><p>Our most-watched videos, and the products that appear in our vlogs. Each one is linked from our website with a "Check price" button, so a feature can drive direct clicks.</p></div>
<div class="grid4">{topcards}</div><h3 style="margin:30px 0 14px;font-size:22px">How products appear on our website</h3><div class="grid4">{prodcards}</div>
<p style="margin-top:14px"><a class="btn sm" href="index.html#products">See our products page &nearr;</a> <a class="btn sm" href="articles.html">Read our parenting articles &nearr;</a></p></section>

<section class="rv" id="audience"><div class="sec-h"><span class="kick">Audience</span><h2>Young parents who buy with care.</h2></div>
<div class="grid3"><div class="card"><span class="ic">&#128205;</span><h3>Where</h3><p>{esc(CFG['location'])} and the Tier 2 India family belt. Hindi + English.</p></div>
<div class="card"><span class="ic">&#128106;</span><h3>Who</h3><p>Parents aged 22 to 34, mostly moms, with strong baby-care purchase intent.</p></div>
<div class="card"><span class="ic">&#128150;</span><h3>Interests</h3><p>Baby care, first-time parenting, home rituals, family vlogs.</p></div></div></section>

<section class="rv" id="services"><div class="sec-h"><span class="kick">Collaborate</span><h2>Brand work that feels like family.</h2><p>Rates depend on format and usage rights. Send a short brief and we will reply with options.</p></div><div class="grid3">{svc}</div></section>

<section class="rv"><div class="sec-h"><span class="kick">How we work</span><h2>Simple, transparent, brand-safe.</h2></div><ol class="steps">{stp}</ol>
<div class="card" style="margin-top:16px"><h3>Brand safety promise</h3><p>All content is family-friendly and shot in natural home light. We always disclose paid partnerships, put baby safety first, and never make medical claims.</p></div></section>

<section class="rv"><div class="sec-h"><span class="kick">Platforms</span><h2>Where we publish</h2></div>
<table><tr><th>Platform</th><th>Handle</th><th>What we post</th><th>Link</th></tr>
<tr><td>YouTube</td><td>@Ankushali_Vlogs</td><td>Family vlogs and baby-care series, long-form trust building</td><td><a href="{B.SITE['youtube']}" target="_blank" rel="noopener">Visit &rarr;</a></td></tr>
<tr><td>Instagram</td><td>@ankushali_ &middot; {esc(CFG['ig_followers'])}</td><td>Reels and stories, baby-care routines, product moments ({esc(CFG['ig_avg_likes'])} avg likes, {esc(CFG['ig_avg_comments'])} avg comments)</td><td><a href="{B.SITE['instagram']}" target="_blank" rel="noopener">Visit &rarr;</a></td></tr>
<tr><td>Facebook</td><td>Ankushali Vlogs</td><td>Community and family audiences</td><td><a href="{B.SITE['facebook']}" target="_blank" rel="noopener">Visit &rarr;</a></td></tr>
<tr><td>Website</td><td>ankushalivlogs.github.io</td><td>Products, parenting articles, buying guides</td><td><a href="index.html">Visit &rarr;</a></td></tr></table></section>

<section class="rv" id="faq"><div class="sec-h"><span class="kick">For brands</span><h2>Good to know</h2></div>{fq}</section>

<div class="contact rv"><div><span class="kick" style="color:var(--yel)">Contact</span><h2>Let's create something parents will trust.</h2><p>For baby care, mother and child, and family lifestyle brands. We reply {esc(CFG['response'])} on email and WhatsApp.</p></div>
<div><a class="row" href="{mail}"><b>{esc(CFG['email'])}</b><span>EMAIL &rarr;</span></a><a class="row" href="{wa}" target="_blank" rel="noopener"><b>WhatsApp {esc(CFG['whatsapp_display'])}</b><span>CHAT &rarr;</span></a><a class="row" href="index.html"><b>ankushalivlogs.github.io</b><span>VISIT &rarr;</span></a></div></div>
<footer><span>&copy; {datetime.date.today().year} ANKUSHALI VLOGS &middot; FAMILY &middot; PARENTING &middot; BABY CARE</span><span><a href="{mail}">EMAIL</a><a href="{wa}">WHATSAPP</a><a href="index.html">WEBSITE</a></span></footer></main>
<script>const io=new IntersectionObserver(es=>es.forEach(e=>{{if(e.isIntersecting){{e.target.classList.add('in');io.unobserve(e.target)}}}}),{{threshold:.08}});document.querySelectorAll('.rv').forEach(e=>io.observe(e));</script>
</body></html>"""
    (OUT / "media-kit.html").write_text(page, encoding="utf-8")
    print("media-kit.html written")
    if "--pdf" in sys.argv or True:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=12000",
                        f"--print-to-pdf={OUT / 'Ankushali-Vlogs-Media-Kit.pdf'}", (OUT / "media-kit.html").as_uri()], check=True, capture_output=True)
        print("PDF written", (OUT / 'Ankushali-Vlogs-Media-Kit.pdf').stat().st_size // 1024, "KB")

if __name__ == "__main__":
    main()
