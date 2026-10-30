"""Adds new/changed videos from the channel's public YouTube RSS feed into data/raw.jsonl (keeps older videos).
No API key, no login. The feed only lists the latest ~15 uploads, so run it at least every few days (the GitHub robot does)."""
import json, re, time, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CHANNEL_ID = "UCjTMoBN6LN7LWDpBoSd5Kiw"
RAW = Path(__file__).parent / "data/raw.jsonl"
NS = {"a": "http://www.w3.org/2005/Atom", "m": "http://search.yahoo.com/mrss/", "y": "http://www.youtube.com/xml/schemas/2015"}

req = urllib.request.Request(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}", headers={"User-Agent": "Mozilla/5.0"})
try:
    feed = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
except Exception as ex:  # YouTube's RSS feed is sometimes down (404): fall back to reading the channel pages
    print("RSS feed unavailable (", ex, ") - using channel pages instead")
    feed = None

rows = {}
if RAW.exists():
    for l in RAW.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            rows[r["id"]] = r
new = 0
for e in (feed.findall("a:entry", NS) if feed is not None else []):
    vid = e.find("y:videoId", NS).text
    stats = e.find("m:group/m:community/m:statistics", NS)
    desc = e.find("m:group/m:description", NS)
    old = rows.get(vid, {})
    new += vid not in rows
    rows[vid] = {
        "id": vid,
        "title": e.find("a:title", NS).text,
        "description": (desc.text or "") if desc is not None else "",
        "upload_date": e.find("a:published", NS).text[:10].replace("-", ""),
        "duration": old.get("duration"),
        "view_count": int(stats.get("views")) if stats is not None else old.get("view_count"),
        "webpage_url": e.find("a:link", NS).get("href"),
    }

if feed is None:
    UA0 = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    def page(u):
        rq = urllib.request.Request(u, headers={"User-Agent": UA0, "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+cb"})
        return urllib.request.urlopen(rq, timeout=30).read().decode("utf-8", "replace")
    ids = []
    for tab in ("videos", "shorts"):
        try:
            ids += re.findall(r'"videoId":"([\w-]{11})"', page(f"https://www.youtube.com/@Ankushali_Vlogs/{tab}?hl=en"))
        except Exception as ex:
            print("channel tab", tab, "failed:", ex)
    for vid in dict.fromkeys(ids):
        if vid in rows:
            continue
        try:
            h = page(f"https://www.youtube.com/watch?v={vid}&hl=en")
            import html as _h
            title = re.search(r'<meta name="title" content="([^"]*)"', h)
            desc = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', h)
            date = re.search(r'itemprop="datePublished" content="(\d{4}-\d{2}-\d{2})', h)
            views = re.search(r'"viewCount":"(\d+)"', h); secs = re.search(r'"lengthSeconds":"(\d+)"', h)
            rows[vid] = {"id": vid, "title": _h.unescape(title.group(1)) if title else vid,
                         "description": json.loads('"' + desc.group(1) + '"') if desc else "",
                         "upload_date": date.group(1).replace("-", "") if date else "", "duration": int(secs.group(1)) if secs else None,
                         "view_count": int(views.group(1)) if views else 0,
                         "webpage_url": f"https://www.youtube.com/{'shorts' if secs and int(secs.group(1)) <= 60 else 'watch?v='}{'/' if secs and int(secs.group(1)) <= 60 else ''}{vid}"}
            new += 1
        except Exception as ex:
            print("could not read", vid, ex)

# The RSS view count freezes once a video drops out of the latest 15, and it lags the
# number on the watch page. Read the public viewCount for every saved video.
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def public_views(vid):
    req = urllib.request.Request(
        f"https://www.youtube.com/watch?v={vid}&hl=en",
        headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+cb"})
    try:
        html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    except Exception:
        return None
    m = re.search(r'"viewCount":"(\d+)"', html)
    return int(m.group(1)) if m else None

bumped = 0
for row in rows.values():
    time.sleep(0.2)
    live = public_views(row["id"])
    old = row.get("view_count") or 0
    if live and live > old:
        row["view_count"] = live
        bumped += 1

RAW.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows.values()), encoding="utf-8")
print(f"{len(rows)} videos in data ({new} new, {bumped} view counts raised)")

try:  # public subscriber / video count shown on the site (never blocks the update)
    import channel_stats; channel_stats.main()
except Exception as e:
    print("channel stats skipped:", e)
