"""Met à jour data/compte.json : abonnés, j'aime, et chiffres de chaque vidéo de @dramaaverse."""
import json, re, time, datetime, urllib.request
USER = "dramaaverse"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TZ = datetime.timezone(datetime.timedelta(hours=1))
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
LOG = []

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")

def scope(html):
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(m.group(1))["__DEFAULT_SCOPE__"] if m else {}

def titre(desc):
    t = re.sub(r"^Réponse à @\S+\s*", "", desc or "").split("#")[0].strip()
    t = re.sub(r"\s+", " ", t)
    return (t[:80] + "…") if len(t) > 80 else t

def main():
    path = "data/compte.json"
    c = json.load(open(path, encoding="utf-8"))
    now = datetime.datetime.now(TZ)
    vids = {v["id"]: v for v in c.get("videos", []) if v.get("id")}
    # 1. Profil : abonnés, j'aime, nouvelles vidéos
    prof = None
    try:
        html = get(f"https://www.tiktok.com/@{USER}")
        u = scope(html).get("webapp.user-detail", {}).get("userInfo", {})
        s = u.get("statsV2") or u.get("stats") or {}
        if s.get("followerCount") is not None:
            prof = {"abonnes": int(s["followerCount"]), "jaime": int(s["heartCount"]), "videos": int(s["videoCount"])}
        for vid in set(re.findall(rf"@{USER}/video/(\d+)", html)):
            vids.setdefault(vid, {"id": vid})
        LOG.append(f"profil: {prof}")
    except Exception as e:
        LOG.append(f"profil: erreur {type(e).__name__} {str(e)[:80]}")
    # 2. Chaque vidéo
    ok = 0
    for vid, v in vids.items():
        v["lien"] = f"https://www.tiktok.com/@{USER}/video/{vid}"
        try:
            it = scope(get(v["lien"]))["webapp.video-detail"]["itemInfo"]["itemStruct"]
            st = it.get("statsV2") or it.get("stats") or {}
            if int(st.get("playCount") or 0) > 0:
                v["vues"] = int(st["playCount"]); v["likes"] = int(st.get("diggCount") or 0)
                v["comms"] = int(st.get("commentCount") or 0); v["partages"] = int(st.get("shareCount") or 0)
                v["titre"] = titre(it.get("desc")) or v.get("titre", "")
                d = datetime.datetime.fromtimestamp(int(it.get("createTime") or 0), TZ)
                v["ts"] = int(it.get("createTime") or 0); v["date"] = f"{d.day} {MOIS[d.month-1]}"
                ok += 1
        except Exception as e:
            LOG.append(f"{vid}: erreur {type(e).__name__}")
        time.sleep(1.5)
    LOG.append(f"vidéos relues: {ok}/{len(vids)}")
    c["videos"] = sorted(vids.values(), key=lambda v: -int(v.get("ts") or v["id"][:10]))
    # 3. Relevé du jour (si le profil n'a pas répondu, j'aime = somme des vidéos)
    rel = c["comptes"][0]["releves"]
    today = now.strftime("%d/%m/%Y")
    if not prof and ok:
        last = rel[-1]
        prof = {"abonnes": last["abonnes"], "jaime": max(last["jaime"], sum(v.get("likes", 0) for v in c["videos"])), "videos": len(c["videos"]), "estime": True}
    if prof:
        r = dict(prof, date=today, source="robot")
        if rel and rel[-1]["date"] == today and not (prof.get("estime") and rel[-1].get("source") != "robot"):
            rel[-1] = r
        elif not rel or rel[-1]["date"] != today:
            rel.append(r)
    c["maj"] = now.strftime("%d/%m/%Y à %H:%M")
    open(path, "w", encoding="utf-8").write(json.dumps(c, ensure_ascii=False, indent=0))
    open("data/compte-log.txt", "w", encoding="utf-8").write("\n".join(LOG) + "\n")

main()
