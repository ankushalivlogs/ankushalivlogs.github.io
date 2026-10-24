"""Adds new/changed videos from the channel's public YouTube RSS feed into data/raw.jsonl (keeps older videos).
No API key, no login. The feed only lists the latest ~15 uploads, so run it at least every few days (the GitHub robot does)."""
import json, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CHANNEL_ID = "UCjTMoBN6LN7LWDpBoSd5Kiw"
RAW = Path(__file__).parent / "data/raw.jsonl"
NS = {"a": "http://www.w3.org/2005/Atom", "m": "http://search.yahoo.com/mrss/", "y": "http://www.youtube.com/xml/schemas/2015"}

req = urllib.request.Request(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}", headers={"User-Agent": "Mozilla/5.0"})
feed = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())

rows = {}
if RAW.exists():
    for l in RAW.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            rows[r["id"]] = r
new = 0
for e in feed.findall("a:entry", NS):
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
RAW.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows.values()), encoding="utf-8")
print(f"{len(rows)} videos in data ({new} new)")
