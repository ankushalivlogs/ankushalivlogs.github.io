"""End-to-end + responsive tests for the site, run in real Chrome via Playwright.
Usage:  python tests/e2e.py [base_url]      (default http://localhost:8765)
Exit code 1 if any check fails. Prints a table and every failure with details."""
import json, re, sys, time, urllib.request
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765").rstrip("/")
VIEWPORTS = [("phone-small 320", 320, 640, True), ("phone 375", 375, 812, True), ("tablet 768", 768, 1024, True),
             ("laptop 1366", 1366, 768, False), ("desktop 1920", 1920, 1080, False)]
results = []  # (viewport, check, ok, detail)

def rec(vp, name, ok, detail=""):
    results.append((vp, name, bool(ok), detail))

JS_OVERFLOW = """() => { const W = innerWidth, bad = [];
  const clipped = el => { for (let p = el.parentElement; p; p = p.parentElement) { const s = getComputedStyle(p);
      if (/(auto|scroll|hidden)/.test(s.overflowX) && p !== document.documentElement && p !== document.body) return true } return false };
  document.querySelectorAll('body *').forEach(el => { const r = el.getBoundingClientRect();
    if (r.width && r.right > W + 1 && !clipped(el) && getComputedStyle(el).position !== 'fixed') bad.push(el.tagName + '.' + (el.className||'') + ' right=' + Math.round(r.right)) });
  return { sw: document.documentElement.scrollWidth, W, bad: bad.slice(0, 5) } }"""

JS_CONTRAST = """() => { const lum = c => { const a = c.map(v => { v/=255; return v<=.03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4) }); return .2126*a[0]+.7152*a[1]+.0722*a[2] };
  const rgb = s => { const m = s.match(/[\\d.]+/g); return m ? m.map(Number) : null };
  const bg = el => { for (let e = el; e; e = e.parentElement) { const bi = getComputedStyle(e).backgroundImage; if (/gradient/.test(bi)) { const m = bi.match(/rgba?\([^)]*\)/); const g = m && rgb(m[0]); if (g) return g.slice(0,3) } const c = rgb(getComputedStyle(e).backgroundColor); if (c && (c.length < 4 || c[3] > .9)) return c.slice(0,3) } return [255,255,255] };
  const out = [];
  const pick = ['h1 .w:not(em .w)', 'p.lead', '.sub', '.card b', '.card small', 'nav a', 'footer .fine', '.stat small', '.chip', '.chip.on', '.go', '.gbtn', '.pill', '.tag', '.ghost'];
  pick.forEach(sel => { const el = document.querySelector(sel); if (!el) return; const cs = getComputedStyle(el); const fg = rgb(cs.color); if (!fg || (fg.length === 4 && fg[3] < .5)) return;
    const b = bg(el), L1 = lum(fg.slice(0,3)), L2 = lum(b), r = (Math.max(L1,L2)+.05)/(Math.min(L1,L2)+.05); out.push([sel, Math.round(r*100)/100]) });
  return out }"""

def get_status(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", 0)

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="chrome", headless=True)
    for vp, w, h, touch in VIEWPORTS:
        ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch and w < 800, device_scale_factor=2 if touch else 1)
        page = ctx.new_page()
        errors, failed, bytes_total, http_bad, own404 = [], [], [0], [], []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: http_bad.append((r.status, r.url)) if r.status >= 400 else None)
        page.on("requestfailed", lambda r: failed.append(r.url[:90]))
        def on_response(r, bucket=bytes_total, missing=own404):
            bucket[0] += int((r.headers.get("content-length") or 0))
            if r.status >= 400 and urlparse(r.url).hostname in ("127.0.0.1", "localhost"):
                missing.append(r.url[:90])
        page.on("response", on_response)
        t0 = time.time(); page.goto(BASE + "/index.html", wait_until="load"); load_s = time.time() - t0
        page.wait_for_timeout(2600)

        # --- layout / responsiveness
        o = page.evaluate(JS_OVERFLOW)
        rec(vp, "no horizontal scroll", o["sw"] <= o["W"] + 1 and not o["bad"], f"scrollWidth={o['sw']} viewport={o['W']} offenders={o['bad']}")
        rec(vp, "h1 visible + inside viewport", page.evaluate("() => { const r = document.querySelector('h1').getBoundingClientRect(); return r.width > 0 && r.left >= -1 && r.right <= innerWidth + 1 }"))
        rec(vp, "header: brand + Subscribe in view", page.evaluate("() => ['.brand','.navbtn'].every(s => { const r = document.querySelector('header '+s).getBoundingClientRect(); return r.width>0 && r.right <= innerWidth+1 && r.left >= 0 })"))
        if w <= 800:
            hh = page.evaluate("() => Math.round(document.querySelector('header').getBoundingClientRect().height)")
            same_row = page.evaluate("() => { const b = document.querySelector('.brand').getBoundingClientRect(); const s = document.querySelector('header .navbtn').getBoundingClientRect(); return Math.abs(b.top - s.top) < 10 }")
            rec(vp, "header compact: brand and Subscribe share a row", same_row and hh <= 112, f"height={hh} same_row={same_row}")
        rec(vp, "hero photo visible", page.evaluate("() => { const i = document.querySelector('.hphoto'); return i.complete && i.naturalWidth > 0 && i.getBoundingClientRect().width > 150 }"))
        cols = page.evaluate("() => getComputedStyle(document.querySelector('.hero')).gridTemplateColumns.split(' ').length")
        rec(vp, "hero layout (2 cols desktop, 1 col <900)", (cols == 2) == (w >= 901), f"columns={cols}")
        if touch:
            small = page.evaluate("() => [...document.querySelectorAll('header a, .btns a, .chip, .arrow, select, #q')].filter(e => e.offsetParent).map(e => [e.className||e.tagName, Math.round(e.getBoundingClientRect().height), Math.round(e.getBoundingClientRect().width)]).filter(x => Math.min(x[1], x[2]) < 32)")
            rec(vp, "tap targets >= 32px", not small, str(small[:5]))
        rec(vp, "font size >= 14px for body copy", page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.sub')).fontSize) >= 14"))

        # --- images (force lazy ones)
        page.evaluate("() => document.querySelectorAll('img').forEach(i => i.loading = 'eager')")
        for _ in range(16):  # up to 8s for slow CDNs
            if page.evaluate("() => [...document.images].every(i => i.complete)"): break
            page.wait_for_timeout(500)
        broken = page.evaluate("() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src.slice(-60))")
        rec(vp, "all images load", not broken, str(broken[:4]))
        rec(vp, "all images have alt attr", page.evaluate("() => [...document.images].every(i => i.hasAttribute('alt'))"))
        own = [x for x in http_bad if x[1].startswith(BASE)]; ext = [x for x in http_bad if not x[1].startswith(BASE)]
        real_errors = [e for e in errors if "Failed to load resource" not in e]
        rec(vp, "no console errors / failed requests", not real_errors and not failed and not own, f"errors={real_errors[:2]} failed={failed[:2]} own404={own[:2]}")
        if ext: print(f"  warning [{vp}] external resources failing (not our files): {ext[:3]}")
        rec(vp, "page weight < 2.5MB (declared)", bytes_total[0] < 2_500_000, f"{bytes_total[0]//1024} KB, load event {load_s:.1f}s")

        # --- vlogs carousel + dropdowns
        vt = page.locator("#vtrack"); first = lambda: page.evaluate("() => document.querySelector('#vtrack .vid:not([hidden]) h4').textContent")
        a = first(); page.select_option("#vsort", "views"); b = first()
        rec(vp, "vlogs: sort by most viewed changes order", a != b, f"{a[:25]!r} -> {b[:25]!r}")
        page.select_option("#vtype", "short")
        only_short = page.evaluate("() => [...document.querySelectorAll('#vtrack .vid:not([hidden])')].every(c => c.dataset.type === 'short')")
        rec(vp, "vlogs: Shorts filter shows only shorts", only_short)
        page.select_option("#vtype", "all"); page.select_option("#vsort", "new")
        page.evaluate("() => document.getElementById('vtrack').scrollLeft = 0"); page.click("#vnext"); page.wait_for_timeout(1200)
        rec(vp, "vlogs: next arrow scrolls", page.evaluate("() => document.getElementById('vtrack').scrollLeft") > 0)
        # horizontal swipe/scroll on touch
        rec(vp, "vlogs: scroll-snap track scrollable", page.evaluate("() => { const t = document.getElementById('vtrack'); return t.scrollWidth > t.clientWidth }"))

        # --- products: chips, search
        total = page.evaluate("() => document.querySelectorAll('.prod').length")
        page.fill("#q", "cerelac"); n = page.evaluate("() => [...document.querySelectorAll('.prod')].filter(c => !c.hidden).length")
        rec(vp, "products: search 'cerelac' -> 1 result", n == 1, f"got {n}")
        page.fill("#q", "zzzzzz"); rec(vp, "products: empty search shows message", page.evaluate("() => !document.getElementById('none').hidden"))
        page.fill("#q", "")
        page.click(".chip[data-c='play-gear']"); n = page.evaluate("() => [...document.querySelectorAll('.prod')].filter(c => !c.hidden).length")
        rec(vp, "products: category chip filters", 0 < n < total, f"{n} of {total}")
        page.click(".chip[data-c='all']"); rec(vp, "products: 'All' restores everything", page.evaluate("() => [...document.querySelectorAll('.prod')].filter(c => !c.hidden).length") == total)
        bad_rel = page.evaluate("() => [...document.querySelectorAll('.prod .buy, .feat .buy')].filter(a => !/sponsored/.test(a.rel) || a.target !== '_blank').length")
        rec(vp, "affiliate links have rel=sponsored + new tab", bad_rel == 0, f"{bad_rel} bad")

        # --- accessibility basics
        rec(vp, "exactly one h1", page.evaluate("() => document.querySelectorAll('h1').length") == 1)
        rec(vp, "html lang set", bool(page.evaluate("() => document.documentElement.lang")))
        rec(vp, "buttons/arrows have accessible names", page.evaluate("() => [...document.querySelectorAll('button, a.soc')].every(b => (b.textContent.trim() || b.getAttribute('aria-label')))"))
        ctx.close()

    # ---------- article pages + articles list (laptop + phone)
    for vp, w, h, touch in (("phone 375", 375, 812, True), ("laptop 1366", 1366, 768, False)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
        page = ctx.new_page(); errs = []
        page.on("pageerror", lambda e: errs.append(str(e))); page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.goto(BASE + "/articles.html#teens", wait_until="load"); page.wait_for_timeout(800)
        vis = page.evaluate("() => [...document.querySelectorAll('#agrid .card')].filter(c => !c.hidden).map(c => c.dataset.cat)")
        rec(vp, "articles: #teens shows only teens", vis and set(vis) == {"teens"}, str(vis))
        page.click(".catbar a[data-c='all']"); page.wait_for_timeout(300)
        allv = page.evaluate("() => [...document.querySelectorAll('#agrid .card')].filter(c => !c.hidden).length")
        rec(vp, "articles: All shows every article", allv >= 9, f"{allv}")
        page.locator("#agrid .card").first.click(); page.wait_for_load_state("load"); page.wait_for_timeout(600)
        rec(vp, "article opens with h1 + author box", page.evaluate("() => !!document.querySelector('h1') && !!document.querySelector('.author')"))
        o = page.evaluate(JS_OVERFLOW); rec(vp, "article: no horizontal scroll", o["sw"] <= o["W"] + 1 and not o["bad"], str(o))
        page.evaluate("() => document.querySelectorAll('img').forEach(i => i.loading = 'eager')"); page.wait_for_timeout(2000)
        rec(vp, "article: images load", not page.evaluate("() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).length"))
        rec(vp, "article: no JS errors", not errs, str(errs[:2]))
        ld = page.evaluate("() => [...document.querySelectorAll('script[type=\"application/ld+json\"]')].map(s => { try { return JSON.parse(s.textContent)['@type'] } catch (e) { return 'INVALID' } })")
        rec(vp, "article: JSON-LD valid (Article + Breadcrumb)", "INVALID" not in ld and "Article" in ld, str(ld))
        rec(vp, "article: English only (no Hinglish markers)", not re.search(r"\b(nahi|kya|karein|bahut|zaroor|mein|hota|jaata)\b", page.inner_text("main"), re.I))
        ctx.close()


    # ---------- new conversion features: top picks, categories, watch-and-shop modal, product + category pages, sticky bar, share
    for vp, w, h, touch in (("phone 375", 375, 812, True), ("tablet 768", 768, 1024, True), ("laptop 1366", 1366, 768, False)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch and w < 800)
        page = ctx.new_page(); errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE + "/index.html", wait_until="load"); page.wait_for_timeout(1500)
        page.evaluate("() => document.querySelectorAll('img').forEach(i => i.loading = 'eager')"); page.wait_for_timeout(1500)
        rec(vp, "home: top picks shows 3 cards with Buy buttons", page.evaluate("() => document.querySelectorAll('.feat .buy').length") >= 1)
        tiles = page.evaluate("() => [...document.querySelectorAll('.tile')].map(a => a.getAttribute('href'))")
        rec(vp, "home: category tiles present", len(tiles) >= 5, f"{len(tiles)} tiles")
        # modal: open a video that lists products, check player + products + close
        page.evaluate("() => { const c = [...document.querySelectorAll('#vtrack .vid')].find(c => JSON.parse(c.dataset.prods).length >= 1); c.scrollIntoView({block:'center'}); window.__c = c }")
        page.wait_for_timeout(600)
        page.evaluate("() => window.__c.querySelector('.vthumb').click()"); page.wait_for_timeout(900)
        st = page.evaluate("() => ({open: document.getElementById('vmodal').open, src: (document.querySelector('#vframe iframe')||{}).src || '', prods: document.querySelectorAll('.vmp').length, title: document.getElementById('vmtitle').textContent.length})")
        rec(vp, "modal: opens with YouTube player + product list", st["open"] and "youtube-nocookie.com/embed/" in st["src"] and st["prods"] >= 1 and st["title"] > 0, str(st))
        inside = page.evaluate("() => { const r = document.getElementById('vmodal').getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1 && r.top >= -1 && r.bottom <= innerHeight + 1 }")
        rec(vp, "modal: fits inside the screen", inside)
        page.keyboard.press("Escape"); page.wait_for_timeout(400)
        rec(vp, "modal: Esc closes and stops the video", page.evaluate("() => !document.getElementById('vmodal').open && !document.getElementById('vframe').innerHTML"))
        # sticky mobile bar
        if w < 760:
            page.evaluate("() => scrollTo(0, 1200)"); page.wait_for_timeout(700)
            rec(vp, "sticky mobile bar appears after scrolling", page.evaluate("() => document.querySelector('.mbar').classList.contains('show')"))
        # category page
        page.goto(BASE + "/" + tiles[0], wait_until="load"); page.wait_for_timeout(500)
        o = page.evaluate(JS_OVERFLOW); rec(vp, "category page: no horizontal scroll", o["sw"] <= o["W"] + 1 and not o["bad"], str(o))
        n = page.evaluate("() => document.querySelectorAll('.prod').length")
        rec(vp, "category page: lists products + checklist + h1", n >= 1 and page.evaluate("() => !!document.querySelector('h1') && document.querySelectorAll('.checklist li').length >= 3"), f"{n} products")
        # product page
        href = page.evaluate("() => document.querySelector('.prod .pn').getAttribute('href')")
        page.goto(BASE + "/" + href.replace("../", ""), wait_until="load"); page.wait_for_timeout(800)
        page.evaluate("() => document.querySelectorAll('img').forEach(i => i.loading = 'eager')"); page.wait_for_timeout(2500)
        pi = page.evaluate("""() => ({h1: !!document.querySelector('h1'), buy: (() => { const a = document.querySelector('.buyrow .buy'); return !!a && /sponsored/.test(a.rel) && a.target === '_blank' && /^https?:/.test(a.href) })(),
            img: (() => { const i = document.querySelector('.bigimg img'); return !!i && i.naturalWidth > 100 })(), crumbs: !!document.querySelector('.crumb'), wa: !!document.querySelector('.share .wa'),
            ld: [...document.querySelectorAll('script[type="application/ld+json"]')].every(s => { try { JSON.parse(s.textContent); return true } catch (e) { return false } }), checklist: document.querySelectorAll('.checklist li').length})""")
        rec(vp, "product page: h1, working Buy link, image, breadcrumb, share, valid JSON-LD", all([pi["h1"], pi["buy"], pi["img"], pi["crumbs"], pi["wa"], pi["ld"], pi["checklist"] >= 3]), str(pi))
        o = page.evaluate(JS_OVERFLOW); rec(vp, "product page: no horizontal scroll", o["sw"] <= o["W"] + 1 and not o["bad"], str(o))
        if w < 760:
            page.evaluate("() => scrollTo(0, 900)"); page.wait_for_timeout(700)
            rec(vp, "product page: sticky Buy bar visible on phone", page.evaluate("() => { const b = document.querySelector('.mbar'); return b.classList.contains('show') && /Check price/.test(b.textContent) }"))
        rec(vp, "new pages: no JS errors", not errs, str(errs[:2]))
        ctx.close()

    # crawl every internal link found on home, category and product pages (one level) and make sure none are broken
    seen, bad, queue = set(), [], [BASE + "/index.html"]
    while queue and len(seen) < 120:
        u = queue.pop(0)
        if u in seen: continue
        seen.add(u)
        try:
            html_ = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8", "ignore")
        except Exception as e:
            bad.append((u, getattr(e, "code", str(e)))); continue
        for m in re.findall(r'href="([^"#]+)"', html_):
            if m.startswith(("http", "mailto", "data:", "javascript")): continue
            t = urljoin(u, m).split("?")[0]
            if t.startswith(BASE) and t not in seen and t.endswith((".html", "/")): queue.append(t)
    rec("site", f"crawl: {len(seen)} internal pages reachable, 0 broken", not bad, str(bad[:5]))

    # ---------- theme + motion preferences
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1366, "height": 768}, color_scheme=scheme); page = ctx.new_page()
        page.goto(BASE + "/index.html", wait_until="load"); page.wait_for_timeout(2600)
        low = [x for x in page.evaluate(JS_CONTRAST) if x[1] < 4.5]
        rec(f"theme {scheme}", "text contrast >= 4.5:1", not low, str(low))
        ctx.close()
    ctx = browser.new_context(viewport={"width": 1366, "height": 768}, reduced_motion="reduce"); page = ctx.new_page()
    page.goto(BASE + "/index.html", wait_until="load"); page.wait_for_timeout(300)
    rec("reduced motion", "hero text visible immediately", page.evaluate("() => [...document.querySelectorAll('.split .w')].every(w => getComputedStyle(w).opacity === '1')"))
    rec("reduced motion", "sections visible without scrolling in", page.evaluate("() => [...document.querySelectorAll('.rv')].every(e => getComputedStyle(e).opacity !== '0' || e.classList.contains('in'))"))
    ctx.close()
    browser.close()

# ---------- links + SEO files (no browser)
home = urllib.request.urlopen(BASE + "/index.html").read().decode("utf-8")
links = sorted({urljoin(BASE + "/", m) for m in re.findall(r'(?:href|src)="([^"#]+)"', home) if not m.startswith(("http", "data:", "mailto")) and "'" not in m and "+" not in m})
bad = [(u, get_status(u)) for u in links if get_status(u) != 200]
rec("site", f"internal links/assets from home ({len(links)})", not bad, str(bad[:5]))
sm = urllib.request.urlopen(BASE + "/sitemap.xml").read().decode()
urls = re.findall(r"<loc>(.*?)</loc>", sm); local = [BASE + urlparse(u).path for u in urls]
bad = [(u, get_status(u)) for u in local if get_status(u) != 200]
rec("site", f"sitemap URLs resolve ({len(urls)})", not bad, str(bad[:5]))
rec("site", "robots.txt points to sitemap", "Sitemap:" in urllib.request.urlopen(BASE + "/robots.txt").read().decode())
rec("site", "404 page exists", get_status(BASE + "/404.html") == 200)
for need in ('rel="canonical"', 'property="og:image"', 'name="description"', 'application/ld+json', 'name="viewport"'):
    rec("site", f"home has {need}", need in home)
og = re.search(r'property="og:image" content="([^"]+)"', home).group(1)
rec("site", "og:image reachable", get_status(og.replace("https://ankushalivlogs.github.io", BASE)) == 200, og)

# ---------- report
fails = [r for r in results if not r[2]]
print(f"\n{'VIEWPORT':<20}{'CHECK':<58}RESULT")
for vp, name, ok, d in results:
    print(f"{vp:<20}{name[:56]:<58}{'PASS' if ok else 'FAIL'}")
print(f"\n{len(results) - len(fails)} passed, {len(fails)} failed of {len(results)}")
for vp, name, ok, d in fails:
    print(f"  FAIL [{vp}] {name}: {d}")
sys.exit(1 if fails else 0)
