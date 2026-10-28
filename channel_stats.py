"""Reads the public numbers shown on the YouTube channel page (subscribers, video count) -> data/channel.json.
YouTube shows exact subscriber counts below 1,000 and rounded ones (like 1.2K) above that; we show exactly what YouTube shows."""
import datetime, json, re, urllib.request
from pathlib import Path
OUT = Path(__file__).parent / "data/channel.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"

def main():
    req = urllib.request.Request("https://www.youtube.com/@Ankushali_Vlogs?hl=en", headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+cb"})
    h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    subs = re.search(r'"content":"([\d.,]+[KM]?) subscribers?"', h)
    vids = re.search(r'"content":"([\d,]+) videos"', h)
    if not subs:
        raise RuntimeError("subscriber count not found")
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    data = {"subscribers": subs.group(1), "videos": int(vids.group(1).replace(",", "")) if vids else old.get("videos"),
            "fetched_at": datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M")}
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print("channel:", data)

if __name__ == "__main__":
    main()
