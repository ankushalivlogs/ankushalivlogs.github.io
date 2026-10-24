#!/bin/bash
# Re-pull every video/short description from the channel -> data/raw.jsonl, then rebuild the site.
export PYTHONUTF8=1
cd "$(dirname "$0")"
: > data/raw.jsonl
for t in videos shorts streams; do
  yt-dlp --skip-download --no-warnings --ignore-errors -j "https://www.youtube.com/@Ankushali_Vlogs/$t" 2>/dev/null | python -c "
import sys,json
for l in sys.stdin:
    try:d=json.loads(l)
    except: continue
    print(json.dumps({k:d.get(k) for k in ['id','title','description','upload_date','duration','view_count','webpage_url']},ensure_ascii=False))
" >> data/raw.jsonl
done
python images.py
python build.py
