"""Radar : cherche des vidéos TikTok par thème et garde celles à 1 M+ de vues, avec leur couverture."""
import json, os, time, urllib.request, urllib.parse, datetime

TOPICS = {
  "Fruits": ["histoire de fruits", "fruit story", "fruitstory", "fruit drama"],
  "Fruits IA": ["ai fruit", "fruit ai drama", "aifruitstory"],
  "Drame couple": ["drame couple", "tromperie", "infidélité histoire"],
  "Belle-famille": ["belle mère", "belle famille drama"],
  "Vengeance": ["vengeance", "karma"],
  "Sketch": ["sketch couple", "sketch famille"],
}
MIN_VIEWS = 1_000_000
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
LOG = []

def req(url, data=None, binary=False):
    body = urllib.parse.urlencode(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
    with urllib.request.urlopen(r, timeout=30) as f:
        b = f.read()
    return b if binary else json.loads(b.decode("utf-8", "replace"))

def search(kw, cursor=0):
    d = req("https://www.tikwm.com/api/feed/search", {"keywords": kw, "count": 30, "cursor": cursor, "HD": 0})
    if d.get("code") != 0:
        LOG.append(f"{kw} p{cursor}: code {d.get('code')} {d.get('msg')}")
        return [], None
    data = d.get("data") or {}
    return data.get("videos") or [], (data.get("cursor") if data.get("hasMore") else None)

def main():
    old = {}
    if os.path.exists("data/radar.json"):
        for v in json.load(open("data/radar.json", encoding="utf-8")).get("videos", []):
            old[v["id"]] = v
    os.makedirs("radar", exist_ok=True)
    found = {}
    for topic, kws in TOPICS.items():
        for kw in kws:
            cursor = 0
            for page in range(3):
                try:
                    vids, cursor = search(kw, cursor)
                except Exception as e:
                    LOG.append(f"{kw}: erreur {type(e).__name__} {str(e)[:80]}"); vids, cursor = [], None
                LOG.append(f"{topic} / {kw} page {page+1}: {len(vids)} vidéos")
                for x in vids:
                    views = x.get("play_count") or 0
                    if views < MIN_VIEWS: continue
                    vid = str(x.get("video_id"))
                    a = x.get("author") or {}
                    v = found.get(vid) or {
                        "id": vid, "compte": "@" + (a.get("unique_id") or ""),
                        "lien": f"https://www.tiktok.com/@{a.get('unique_id')}/video/{vid}",
                        "titre": (x.get("title") or "").strip(), "vues": views,
                        "likes": x.get("digg_count"), "comms": x.get("comment_count"),
                        "partages": x.get("share_count"), "duree": x.get("duration"),
                        "ts": x.get("create_time"), "pays": x.get("region") or "", "themes": [],
                        "cover_url": x.get("origin_cover") or x.get("cover")}
                    if topic not in v["themes"]: v["themes"].append(topic)
                    found[vid] = v
                time.sleep(1.2)
                if cursor is None: break
    # couvertures
    for v in found.values():
        out = f"radar/{v['id']}.jpg"
        if not os.path.exists(out):
            try:
                img = req(v["cover_url"], binary=True)
                if len(img) > 2000: open(out, "wb").write(img)
            except Exception as e:
                LOG.append(f"cover {v['id']}: {type(e).__name__}")
            time.sleep(0.3)
        v["img"] = out if os.path.exists(out) else ""
        v.pop("cover_url", None)
    # garder les anciennes vidéos non retrouvées (sans écraser)
    for k, v in old.items():
        if k not in found: found[k] = v
    # ménage : couvertures orphelines
    keep = {f"{k}.jpg" for k in found}
    for f in os.listdir("radar"):
        if f.endswith(".jpg") and f not in keep: os.remove(os.path.join("radar", f))
    vids = sorted(found.values(), key=lambda v: -v["vues"])
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
    json.dump({"maj": now.strftime("%d/%m/%Y à %H:%M"), "themes": list(TOPICS), "videos": vids},
              open("data/radar.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    open("radar/log.txt", "w", encoding="utf-8").write("\n".join(LOG) + f"\nTotal 1M+: {len(vids)}\n")

main()
