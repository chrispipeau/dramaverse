"""Télécharge la couverture de chaque vidéo TikTok de data/hits.json dans thumbs/."""
import json, os, re, sys, time, urllib.request, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
LOG = []

def get(url, binary=False, referer=None):
    h = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}
    if referer: h["Referer"] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")

def via_oembed(link):
    d = json.loads(get("https://www.tiktok.com/oembed?url=" + urllib.parse.quote(link, safe="")))
    return d.get("thumbnail_url")

def via_page(link):
    html = get(link)
    m = re.search(r'"(?:originCover|cover)":"(https:[^"]+)"', html)
    if m: return m.group(1).encode().decode("unicode_escape")
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    return m.group(1).replace("&amp;", "&") if m else None

def via_tikwm(link):
    d = json.loads(get("https://www.tikwm.com/api/?url=" + urllib.parse.quote(link, safe="")))
    data = d.get("data") or {}
    return data.get("origin_cover") or data.get("cover")

def main():
    path = "data/hits.json"
    d = json.load(open(path, encoding="utf-8"))
    os.makedirs("thumbs", exist_ok=True)
    changed = False
    for h in d["hits"]:
        link = h.get("lien", "")
        if "tiktok.com/@" not in link: continue
        out = f"thumbs/{h['id']}.jpg"
        if os.path.exists(out) and os.path.getsize(out) > 2000:
            if h.get("img") != out: h["img"] = out; changed = True
            continue
        ok = False
        for name, fn in (("oembed", via_oembed), ("page", via_page), ("tikwm", via_tikwm)):
            try:
                url = fn(link)
                if not url: LOG.append(f"{h['id']}: {name} sans image"); continue
                img = get(url, binary=True, referer="https://www.tiktok.com/")
                if len(img) < 2000: LOG.append(f"{h['id']}: {name} image trop petite"); continue
                open(out, "wb").write(img)
                h["img"] = out; changed = ok = True
                LOG.append(f"{h['id']}: OK via {name}")
                break
            except Exception as e:
                LOG.append(f"{h['id']}: {name} erreur {type(e).__name__} {str(e)[:80]}")
            time.sleep(1.5)
        time.sleep(1)
    if changed:
        open(path, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=0))
    open("thumbs/log.txt", "w", encoding="utf-8").write("\n".join(LOG) + "\n")

main()
