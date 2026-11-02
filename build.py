#!/usr/bin/env python3
"""Static site generator for Maltese Stays (maltesestays.com).
Usage: python3 build.py [--preview]
  default : clean URLs (folder/index.html) for real hosting  -> dist/
  --preview: .html links, index page without outer skeleton    -> preview/
"""
import json, os, sys, shutil, html, datetime

PREVIEW = "--preview" in sys.argv
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "preview" if PREVIEW else "dist")

SITE = "https://maltesestays.com"
BRAND = "Maltese Stays"
BOOK_BASE = "https://landlord-care.bookingsboom.com"   # swap to https://book.maltesestays.com once the CNAME is live
WA = "35699550351"
WA_URL = f"https://wa.me/{WA}?text=Hi%20Landlord%20Care%2C%20I%27d%20like%20to%20book%20a%20stay%20in%20Malta"
EMAIL = "reservations.landlordcare@gmail.com"
PHONE_DISPLAY = "+356 9955 0351"
COUPON = ""  # returning-guest code: not shown publicly
OWNER_SITE = "https://landlord.care"
GA_ID = "G-N4DX6XZHKG"
ADDRESS = {"street": "30, Triq San Girgor", "locality": "Sliema", "postal": "SLM 2113", "country": "MT"}
TODAY = datetime.date.today().isoformat()

def load(n):
    with open(os.path.join(ROOT, "data", n), encoding="utf-8") as f:
        return json.load(f)

CURATED = load("listings.json")      # hand-written copy, keyed by Boom listing id
AREAS = load("areas.json")
GROUPS = load("groups.json")
AREA_BY = {a["slug"]: a for a in AREAS}
GROUP_BY = {g["slug"]: g for g in GROUPS}
AREA_CENTROIDS = {"valletta": (35.899, 14.513), "sliema": (35.911, 14.502), "st-julians": (35.917, 14.489),
    "three-cities": (35.885, 14.518), "central-harbour": (35.895, 14.489), "st-pauls-bay": (35.949, 14.409),
    "marsaskala": (35.861, 14.565), "rabat-mdina": (35.882, 14.402)}
CITY_TO_AREA = {"valletta": "valletta", "il-belt valletta": "valletta", "floriana": "valletta", "il-furjana": "valletta",
    "sliema": "sliema", "tas-sliema": "sliema", "gzira": "sliema", "il-gzira": "sliema", "il-gżira": "sliema",
    "st. julian's": "st-julians", "st julian's": "st-julians", "san giljan": "st-julians", "san ġiljan": "st-julians", "paceville": "st-julians", "swieqi": "st-julians", "san gwann": "st-julians", "san ġwann": "st-julians", "pembroke": "st-julians",
    "cospicua": "three-cities", "bormla": "three-cities", "senglea": "three-cities", "l-isla": "three-cities", "isla": "three-cities", "birgu": "three-cities", "vittoriosa": "three-cities", "il-birgu": "three-cities", "kalkara": "three-cities",
    "pietà": "central-harbour", "pieta": "central-harbour", "tal-pietà": "central-harbour", "tal-pieta": "central-harbour", "msida": "central-harbour", "l-imsida": "central-harbour", "ta' xbiex": "central-harbour", "ta xbiex": "central-harbour", "santa venera": "central-harbour", "hamrun": "central-harbour", "il-hamrun": "central-harbour", "birkirkara": "central-harbour",
    "st. paul's bay": "st-pauls-bay", "st paul's bay": "st-pauls-bay", "san pawl il-bahar": "st-pauls-bay", "san pawl il-baħar": "st-pauls-bay", "bugibba": "st-pauls-bay", "qawra": "st-pauls-bay", "mellieha": "st-pauls-bay", "mellieħa": "st-pauls-bay", "il-mellieħa": "st-pauls-bay",
    "marsaskala": "marsaskala", "wied il-ghajn": "marsaskala", "wied il-għajn": "marsaskala", "marsaxlokk": "marsaskala", "zejtun": "marsaskala", "żejtun": "marsaskala", "zabbar": "marsaskala", "ħaż-żabbar": "marsaskala",
    "rabat": "rabat-mdina", "ir-rabat": "rabat-mdina", "mdina": "rabat-mdina", "l-imdina": "rabat-mdina", "dingli": "rabat-mdina", "attard": "rabat-mdina", "ħ'attard": "rabat-mdina", "mosta": "rabat-mdina", "il-mosta": "rabat-mdina"}

def area_for(city, lat, lng):
    c = (city or "").strip().lower()
    if c in CITY_TO_AREA:
        return CITY_TO_AREA[c]
    for k, v in CITY_TO_AREA.items():
        if k in c:
            return v
    return min(AREA_CENTROIDS, key=lambda a: (AREA_CENTROIDS[a][0] - lat) ** 2 + (AREA_CENTROIDS[a][1] - lng) ** 2)

def slugify(s):
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:70]

def short_pic(url_):
    # https://res.cloudinary.com/.../upload/v123/tenants/Thehostinglab/listings/Folder/pictures/abc.jpg -> v123|Folder|abc
    import re
    m = re.search(r"/upload/(v\d+)/tenants/Thehostinglab/listings/([^/]+)/pictures/([^./]+)\.", url_)
    return f"{m.group(1)}|{m.group(2)}|{m.group(3)}" if m else None

def clean_text(t, n=420):
    import re
    t = re.sub(r"[=\-]+>\s*", "", t or "").replace("\u2014", ", ").replace("\u2013", ", ").replace(" , ", ", ")
    t = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > n:
        t = t[:n].rsplit(" ", 1)[0].rstrip(",;:") + "."
    return t

def auto_listing(b):
    """Build a listing entry from raw Boom data for a property that has no hand-written copy yet."""
    import re
    title = b.get("title") or b.get("nickname")
    city = (b.get("city_name") or "Malta").replace("Il-Belt Valletta", "Valletta").replace("Tas-Sliema", "Sliema").replace("L-Imsida", "Msida").replace("Tal-Pietà", "Pietà").replace("L-Isla", "Senglea").replace("Wied il-Għajn", "Marsaskala").replace("Ir-Rabat", "Rabat").replace("San Ġiljan", "St Julian's").replace("San Ġwann", "San Gwann").replace("St. Julian's", "St Julian's").replace("St. Paul's Bay", "St Paul's Bay").replace("Il-Gżira", "Gzira").replace("Il-Gzira", "Gzira").replace("Il-Furjana", "Floriana").replace("Il-Birgu", "Birgu").replace("Il-Mellieħa", "Mellieħa").replace("San Pawl il-Baħar", "St Paul's Bay")
    tl = title.lower()
    is_room = any(w in tl for w in ("room", "ensuite", "suite")) and b.get("beds", 1) == 1
    kind = "Private room" if is_room else "Penthouse" if "penthouse" in tl else "Townhouse" if any(w in tl for w in ("house", "townhouse", "home")) else "Maisonette" if "maisonette" in tl else "Apartment"
    mc = b.get("marketing_content") or {}
    bullets = [clean_text(x, 90) for x in re.split(r"\n+", mc.get("space") or "") if re.match(r"\s*(=+>|[-•*])", x)]
    bullets = [x for x in bullets if 6 < len(x) < 90][:6]
    if len(bullets) < 3:
        bullets = ["Fully equipped kitchen", "Air conditioning", "Fast WiFi", "Fresh linen and towels", "Self check-in", "Local team on WhatsApp 24/7"]
    lat, lng = b.get("lat") or 35.9, b.get("lng") or 14.5
    area = area_for(b.get("city_name"), lat, lng)
    return {"id": b["id"], "slug": slugify(f"{city} {title}"), "name": title, "area": area, "locality": city, "type": "room" if is_room else "home",
            "kind": kind, "beds": b.get("beds") or 1, "baths": b.get("baths") or 1, "acc": b.get("accommodates") or 2, "lat": lat, "lng": lng,
            "score": b.get("airbnb_score"), "pics": [p for p in (short_pic(x.get("original", "")) for x in b.get("pictures", [])) if p][:8],
            "intro": clean_text(mc.get("summary") or f"{kind} in {city}, Malta, managed by Landlord Care."),
            "highlights": bullets, "sleeps": f"Sleeps up to {b.get('accommodates') or 2} guests in {b.get('beds') or 1} bedroom{'s' if (b.get('beds') or 1) > 1 else ''}.",
            "nearby": clean_text(mc.get("notes") or "", 300) or f"Well placed in {city} for exploring Malta. See the area guide for what is nearby.",
            "good_for": ["Couples", "Families"] if not is_room else ["Couples", "Solo travellers"], "auto": True}

def fetch_boom():
    import urllib.request
    req = urllib.request.Request(f"{BOOK_BASE}/api/booking/listings?adults=1&children=0&lang=en&language=en",
                                 headers={"Referer": BOOK_BASE + "/", "User-Agent": "Mozilla/5.0 (maltesestays.com build)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.load(r)
    return data["listings"]

def merge_listings():
    cur = {c["id"]: c for c in CURATED}
    try:
        boom = fetch_boom()
        print(f"Boom API: {len(boom)} listings")
        with open(os.path.join(ROOT, "data", "boom-snapshot.json"), "w", encoding="utf-8") as f:
            json.dump([{k: b.get(k) for k in ("id", "nickname", "title", "city_name", "beds", "baths", "accommodates", "airbnb_score")} for b in boom], f, ensure_ascii=False, indent=1)
    except Exception as e:
        print(f"Boom API unavailable ({e}); using curated list only")
        return CURATED
    out = []
    for b in boom:
        if b["id"] in cur:
            c = dict(cur[b["id"]])
            for k_b, k_c in (("accommodates", "acc"), ("airbnb_score", "score")):
                if b.get(k_b) is not None:
                    c[k_c] = b[k_b]
            pics = [p for p in (short_pic(x.get("original", "")) for x in b.get("pictures", [])) if p][:8]
            if pics:
                c["pics"] = pics
            out.append(c)
        else:
            print(f"  new listing from Boom (auto copy): {b['id']} {b.get('title')}")
            out.append(auto_listing(b))
    gone = [c["name"] for i, c in cur.items() if i not in {b["id"] for b in boom}]
    if gone:
        print("  removed (no longer in Boom):", gone)
    # keep Boom's own order (best rated first) but push unrated to the end
    out.sort(key=lambda l: -(l.get("score") or 0))
    seen = set()
    for l in out:
        while l["slug"] in seen:
            l["slug"] += "-2"
        seen.add(l["slug"])
    return out

LISTINGS = merge_listings()
for l in LISTINGS:
    l["area_name"] = AREA_BY[l["area"]]["name"]

def _pick(pref_id, idx_fallback):
    for l in LISTINGS:
        if l["id"] == pref_id and l["pics"]:
            return l["pics"][0]
    return LISTINGS[min(idx_fallback, len(LISTINGS) - 1)]["pics"][0]
HERO_PIC = _pick(21762, 0)    # Rabat rooftop pool
HERO_PIC2 = _pick(22404, 1)   # Ta' Xbiex terrace

# ---------- helpers ----------
def esc(s): return html.escape(str(s), quote=True)

def img(pic, w=800, h=600, mode="c_fill"):
    ver, folder, pid = pic.split("|")
    if PREVIEW:
        import urllib.parse, re
        label = re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", folder)
        svg = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#C2CBDA'/><stop offset='1' stop-color='#8fa0bf'/></linearGradient></defs><rect width='{w}' height='{h}' fill='url(#g)'/><text x='50%' y='50%' text-anchor='middle' font-family='Inter,Arial' font-size='{max(14, w//28)}' fill='#32375D' opacity='.8'>Photo: {label} ({pid})</text></svg>"
        return "data:image/svg+xml," + urllib.parse.quote(svg)
    return f"https://res.cloudinary.com/do4tedxg6/image/upload/{mode},w_{w},h_{h},q_auto,f_auto/{ver}/tenants/Thehostinglab/listings/{folder}/pictures/{pid}.jpg"

def url(path):
    """path like '' | 'properties' | 'properties/slug' | 'areas/x'. Returns root-relative link."""
    if PREVIEW:
        return "index.html" if path == "" else path.replace("/", "--") + ".html"
    return "/" if path == "" else f"/{path}/"

def canon(path):
    return SITE + ("/" if path == "" else f"/{path}/")

def book_url(l):
    return f"{BOOK_BASE}/listing/{l['id']}?lang=en"

def write(path, content):
    if PREVIEW:
        fp = os.path.join(OUT, "index.html" if path == "" else path.replace("/", "--") + ".html")
    else:
        fp = os.path.join(OUT, path, "index.html") if path else os.path.join(OUT, "index.html")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)

def score_badge(l):
    if l.get("score"):
        return f'<span class="score" title="Guest rating on Airbnb">&#9733; {l["score"]:.2f}'.rstrip("0").rstrip(".") + "</span>"
    return '<span class="score new">New</span>'

def fmt_baths(b):
    return str(int(b)) if float(b).is_integer() else str(b)

# ---------- CSS ----------
CSS = r"""
/* Layout concept: limestone page, navy ink, one blue accent; editorial cards, generous photos */
:root{
  --bg:#f6f3ec; --bg2:#ffffff; --stone:#ece7db; --ink:#1f2340; --navy:#32375D; --blue:#275FB5; --blue-dark:#1d4a8f;
  --mist:#C2CBDA; --slate:#5c637a; --line:#dcd6c8; --lime:#b9d85a; --wa:#25D366;
  --display:"Fraunces",Georgia,"Times New Roman",serif; --body:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --radius:14px; --maxw:1180px;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#15172a;--bg2:#1d2036;--stone:#232743;--ink:#eef0f6;--navy:#dfe4f3;--blue:#7fa8ec;--blue-dark:#a9c4f4;--mist:#3a4060;--slate:#a9b0c6;--line:#2f3453;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#15172a;--bg2:#1d2036;--stone:#232743;--ink:#eef0f6;--navy:#dfe4f3;--blue:#7fa8ec;--blue-dark:#a9c4f4;--mist:#3a4060;--slate:#a9b0c6;--line:#2f3453;color-scheme:dark}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased}
img{max-width:100%;display:block}
a{color:var(--blue)}
h1,h2,h3{font-family:var(--display);font-weight:600;line-height:1.15;text-wrap:balance;margin:0 0 .5em;color:var(--navy)}
h1{font-size:clamp(2rem,4.5vw,3.4rem);letter-spacing:-.01em}
h2{font-size:clamp(1.6rem,3vw,2.3rem)}
h3{font-size:1.25rem}
p{margin:0 0 1em;max-width:68ch}
.wrap{max-width:var(--maxw);margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.eyebrow{font-size:.78rem;text-transform:uppercase;letter-spacing:.12em;color:var(--blue);font-weight:600;margin-bottom:.6rem}
.btn{display:inline-flex;align-items:center;gap:.5rem;padding:.8rem 1.3rem;border-radius:999px;font-weight:600;text-decoration:none;border:2px solid transparent;transition:transform .15s,background .15s;cursor:pointer;font-size:1rem;line-height:1.2}
.btn:hover{transform:translateY(-1px)}
.btn-primary{background:var(--blue);color:#fff}
.btn-primary:hover{background:var(--blue-dark)}
.btn-outline{border-color:var(--navy);color:var(--navy);background:transparent}
.btn-wa{background:var(--wa);color:#fff}
.btn svg{width:18px;height:18px;flex:none}
/* header */
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg)}
header.site{position:sticky;top:env(safe-area-inset-top,0px);z-index:9;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding-block:.8rem}
.logo{display:flex;align-items:center;gap:.6rem;text-decoration:none;color:var(--navy);font-family:var(--display);font-weight:600;font-size:1.2rem;letter-spacing:-.01em}
.logo span{width:34px;height:34px;border-radius:9px;background:var(--navy);color:#fff;display:grid;place-items:center;font-family:var(--body);font-size:.75rem;font-weight:700;letter-spacing:.04em}
nav.main{display:flex;gap:1.4rem;align-items:center}
nav.main a{color:var(--ink);text-decoration:none;font-weight:500;font-size:.95rem}
nav.main a:hover{color:var(--blue)}
nav.main .btn{padding:.55rem 1rem;font-size:.9rem}
.menu-btn{display:none;background:none;border:1px solid var(--line);border-radius:8px;padding:.45rem .6rem;color:var(--ink);font:inherit}
@media(max-width:820px){nav.main{display:none;position:absolute;left:0;right:0;top:100%;background:var(--bg2);flex-direction:column;align-items:stretch;padding:1rem max(16px,env(safe-area-inset-left,0px));border-bottom:1px solid var(--line);gap:.9rem}nav.main.open{display:flex}.menu-btn{display:block}}
/* hero */
.hero{position:relative;color:#fff;background:var(--navy);overflow:hidden}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.55}
.hero .wrap{position:relative;padding-block:clamp(4rem,10vw,8rem) clamp(3rem,7vw,5rem);max-width:860px}
.hero h1{color:#fff;font-size:clamp(2.2rem,5.5vw,4rem)}
.hero p{font-size:1.15rem;color:#e9edf5;max-width:56ch}
.hero .actions{display:flex;flex-wrap:wrap;gap:.8rem;margin-top:1.6rem}
.hero .eyebrow{color:#cfe0ff}
.hero-small .wrap{padding-block:clamp(3rem,7vw,5rem) clamp(2rem,5vw,3.5rem)}
/* sections */
section{padding-block:clamp(2.5rem,6vw,4.5rem)}
section.alt{background:var(--stone)}
.sec-head{display:flex;justify-content:space-between;align-items:end;gap:1rem;flex-wrap:wrap;margin-bottom:1.6rem}
.sec-head p{margin:0;color:var(--slate)}
.grid{display:grid;gap:1.4rem;grid-template-columns:repeat(auto-fill,minmax(280px,1fr))}
.card{background:var(--bg2);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column;min-width:0;text-decoration:none;color:inherit;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(31,35,64,.12)}
.card .ph{aspect-ratio:4/3;max-width:100%;overflow:hidden;background:var(--mist)}
.card .ph img{width:100%;height:100%;object-fit:cover}
.card .body{padding:1rem 1.1rem 1.2rem;display:flex;flex-direction:column;gap:.35rem}
.card h3{font-size:1.12rem;margin:0}
.card .loc{color:var(--slate);font-size:.9rem;display:flex;justify-content:space-between;gap:.5rem}
.card .specs{font-size:.88rem;color:var(--slate);display:flex;gap:.7rem;flex-wrap:wrap;margin-top:.2rem}
.score{font-size:.85rem;font-weight:600;color:var(--navy);white-space:nowrap}
.score.new{color:var(--blue)}
.kind{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:var(--blue);font-weight:600}
/* why direct */
.why{display:grid;gap:1.2rem;grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
.why div{background:var(--bg2);border:1px solid var(--line);border-radius:var(--radius);padding:1.3rem}
.why h3{font-size:1.1rem;margin-bottom:.4rem}
.why p{margin:0;color:var(--slate);font-size:.95rem}
.why .num{font-family:var(--display);font-size:2rem;color:var(--blue);line-height:1;margin-bottom:.6rem}
.coupon{display:inline-block;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--navy);color:#fff;padding:.25rem .6rem;border-radius:6px;letter-spacing:.1em;font-weight:600}
/* areas */
.areas{display:grid;gap:1rem;grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
.area{position:relative;border-radius:var(--radius);overflow:hidden;aspect-ratio:5/4;max-width:100%;text-decoration:none;color:#fff;display:flex;align-items:end;background:var(--navy)}
.area img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .4s}
.area:hover img{transform:scale(1.04)}
.area div{position:relative;padding:1rem;background:linear-gradient(transparent,rgba(20,24,48,.85));width:100%}
.area strong{font-family:var(--display);font-size:1.3rem;display:block;font-weight:600}
.area small{opacity:.9}
/* faq */
.faq{max-width:760px}
.faq details{border-bottom:1px solid var(--line);padding:.9rem 0}
.faq summary{cursor:pointer;font-weight:600;font-size:1.05rem;list-style:none;display:flex;justify-content:space-between;gap:1rem}
.faq summary::after{content:"+";color:var(--blue);font-size:1.3rem;line-height:1}
.faq details[open] summary::after{content:"\2212"}
.faq p{margin:.6rem 0 0;color:var(--slate)}
/* property page */
.gallery{display:grid;gap:.6rem;grid-template-columns:2fr 1fr 1fr;grid-template-rows:repeat(2,minmax(0,1fr));margin-block:1.5rem}
.gallery a{display:block;overflow:hidden;border-radius:10px;aspect-ratio:4/3;max-width:100%;background:var(--mist)}
.gallery a:first-child{grid-row:span 2;aspect-ratio:auto}
.gallery img{width:100%;height:100%;object-fit:cover}
@media(max-width:700px){.gallery{grid-template-columns:1fr 1fr}.gallery a:first-child{grid-column:span 2;grid-row:auto;aspect-ratio:16/10}.gallery a:nth-child(n+5){display:none}}
.prop{display:grid;gap:2.5rem;grid-template-columns:minmax(0,1fr) 340px;align-items:start}
@media(max-width:900px){.prop{grid-template-columns:1fr}}
.prop .main{min-width:0}
.specs-big{display:flex;gap:1.4rem;flex-wrap:wrap;color:var(--slate);font-size:.95rem;margin:.6rem 0 1.2rem}
.specs-big b{color:var(--ink)}
.hl{display:grid;gap:.5rem .9rem;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));padding:0;list-style:none;margin:0 0 1.5rem}
.hl li{padding-left:1.4rem;position:relative}
.hl li::before{content:"";position:absolute;left:0;top:.55em;width:.6rem;height:.6rem;border-radius:50%;background:var(--lime)}
.tags{display:flex;gap:.5rem;flex-wrap:wrap;margin:0 0 1.2rem}
.tags span{background:var(--stone);border-radius:999px;padding:.25rem .7rem;font-size:.85rem}
.bookbox{position:sticky;top:calc(80px + env(safe-area-inset-top,0px));background:var(--bg2);border:1px solid var(--line);border-radius:var(--radius);padding:1.4rem;display:flex;flex-direction:column;gap:.8rem}
.bookbox .btn{justify-content:center;width:100%}
.bookbox small{color:var(--slate);line-height:1.4}
.note{background:var(--stone);border-left:4px solid var(--mist);padding:.8rem 1rem;border-radius:0 8px 8px 0;font-size:.95rem;color:var(--slate)}
.crumbs{font-size:.85rem;color:var(--slate);margin-bottom:.8rem}
.crumbs a{color:var(--slate);text-decoration:none}
.crumbs a:hover{color:var(--blue)}
/* filters */
.filters{display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:1.5rem}
.filters button{background:var(--bg2);border:1px solid var(--line);border-radius:999px;padding:.45rem .95rem;font:inherit;font-size:.9rem;color:var(--ink);cursor:pointer}
.filters button[aria-pressed="true"]{background:var(--navy);color:#fff;border-color:var(--navy)}
.filters .sep{width:1px;background:var(--line);margin:0 .3rem}
/* two col */
.two{display:grid;gap:2rem;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));align-items:start}
.check{list-style:none;padding:0;margin:0 0 1.2rem;display:grid;gap:.5rem}
.check li{padding-left:1.6rem;position:relative}
.check li::before{content:"\2713";position:absolute;left:0;color:var(--blue);font-weight:700}
/* footer */
footer{background:var(--navy);color:#dfe4f3;padding-block:3rem 2rem;margin-top:2rem}
footer .wrap{display:grid;gap:2rem;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
footer h4{color:#fff;font-family:var(--display);font-weight:600;margin:0 0 .6rem;font-size:1.05rem}
footer a{color:#dfe4f3;text-decoration:none}
footer a:hover{color:#fff;text-decoration:underline}
footer ul{list-style:none;padding:0;margin:0;display:grid;gap:.35rem;font-size:.95rem}
footer .legal{grid-column:1/-1;border-top:1px solid rgba(255,255,255,.15);padding-top:1.2rem;font-size:.85rem;color:#b9c2db;display:flex;flex-wrap:wrap;gap:1rem;justify-content:space-between}
/* mobile bar */
.mbar{display:none}
@media(max-width:820px){.mbar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:9;background:var(--bg2);border-top:1px solid var(--line);padding:.6rem max(16px,env(safe-area-inset-right,0px)) calc(.6rem + env(safe-area-inset-bottom,0px)) max(16px,env(safe-area-inset-left,0px));gap:.6rem}.mbar .btn{flex:1;justify-content:center;padding:.7rem .8rem;font-size:.92rem}body{padding-bottom:76px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}html{scroll-behavior:auto}}
:focus-visible{outline:3px solid var(--lime);outline-offset:2px}
.cookie{position:fixed;z-index:20;left:max(16px,env(safe-area-inset-left,0px));right:max(16px,env(safe-area-inset-right,0px));bottom:calc(16px + env(safe-area-inset-bottom,0px));max-width:560px;margin:0 auto;background:var(--bg2);border:1px solid var(--line);border-radius:var(--radius);box-shadow:0 12px 30px rgba(31,35,64,.18);padding:1rem 1.1rem;display:flex;gap:1rem;align-items:center;flex-wrap:wrap}
.cookie p{margin:0;flex:1 1 240px;font-size:.92rem}
.cookie div{display:flex;gap:.5rem}
.cookie .btn{padding:.5rem 1rem;font-size:.9rem}
@media(max-width:820px){.cookie{bottom:calc(84px + env(safe-area-inset-bottom,0px))}}
"""

NAV_JS = """
<script>
(function(){var b=document.querySelector('.menu-btn'),n=document.querySelector('nav.main');if(b){b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)})}})();
</script>
"""

WA_ICON = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.5 3.5A11.8 11.8 0 0 0 12 0C5.5 0 .2 5.3.2 11.8c0 2.1.5 4.1 1.6 5.9L0 24l6.5-1.7a11.8 11.8 0 0 0 5.6 1.4c6.5 0 11.8-5.3 11.8-11.8 0-3.2-1.2-6.1-3.4-8.4zM12 21.7c-1.8 0-3.5-.5-5-1.4l-.4-.2-3.8 1 1-3.7-.2-.4a9.8 9.8 0 0 1-1.5-5.2C2.1 6.4 6.5 2 12 2c2.6 0 5.1 1 6.9 2.9a9.7 9.7 0 0 1 2.9 6.9c0 5.4-4.4 9.9-9.8 9.9zm5.4-7.3c-.3-.1-1.8-.9-2-1-.3-.1-.5-.1-.7.1l-.9 1.1c-.2.2-.3.2-.6.1-.3-.1-1.2-.5-2.4-1.5-.9-.8-1.5-1.8-1.6-2.1-.2-.3 0-.5.1-.6l.4-.5.3-.5c.1-.2 0-.4 0-.5l-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.1-.3-.2-.6-.3z"/></svg>'

def nav(active=""):
    items = [("properties", "All properties"), ("areas", "Areas"), ("guest-houses", "Guest houses"), ("book-direct", "Why book direct"), ("contact", "Contact")]
    links = "".join(f'<a href="{url(p)}"{" aria-current=\"page\"" if p == active else ""}>{t}</a>' for p, t in items)
    return f"""<header class="site"><div class="wrap">
<a class="logo" href="{url('')}" aria-label="{BRAND} home"><span>MS</span>{BRAND}<small style="font-family:var(--body);font-weight:500;font-size:.7rem;color:var(--slate);margin-left:.4rem">by Landlord Care</small></a>
<button class="menu-btn" aria-expanded="false" aria-controls="mainnav">Menu</button>
<nav class="main" id="mainnav" aria-label="Main">{links}<a class="btn btn-primary" href="{BOOK_BASE}/?lang=en" rel="noopener">Check availability</a></nav>
</div></header>"""

def footer():
    area_links = "".join(f'<li><a href="{url("areas/"+a["slug"])}">{esc(a["name"])}</a></li>' for a in AREAS)
    return f"""<footer><div class="wrap">
<div><h4>{BRAND}</h4><p style="font-size:.95rem;color:#dfe4f3">Licensed holiday homes and rooms across Malta, managed by a local team. Book direct for the best price.</p>
<p style="font-size:.9rem"><a href="{WA_URL}" rel="noopener">WhatsApp {PHONE_DISPLAY}</a><br><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
<div><h4>Areas</h4><ul>{area_links}</ul></div>
<div><h4>Stays</h4><ul><li><a href="{url('properties')}">All properties</a></li><li><a href="{url('guest-houses')}">Guest houses</a></li><li><a href="{url('book-direct')}">Why book direct</a></li><li><a href="{url('about')}">About us</a></li><li><a href="{url('contact')}">Contact</a></li></ul></div>
<div><h4>Owners</h4><ul><li><a href="{OWNER_SITE}" rel="noopener">Property management in Malta</a></li><li><a href="{OWNER_SITE}/guaranteed-rent" rel="noopener">Guaranteed rent</a></li></ul></div>
<div class="legal"><span>&copy; {datetime.date.today().year} Landlord Care, {ADDRESS['street']}, {ADDRESS['locality']} {ADDRESS['postal']}, Malta. All properties hold a Malta Tourism Authority holiday licence.</span><span><a href="{BOOK_BASE}/terms?lang=en" rel="noopener">Terms</a> &middot; <a href="{BOOK_BASE}/privacy?lang=en" rel="noopener">Privacy</a></span></div>
</div></footer>
<div class="mbar"><a class="btn btn-wa" href="{WA_URL}" rel="noopener">{WA_ICON} WhatsApp</a><a class="btn btn-primary" href="{BOOK_BASE}/?lang=en" rel="noopener">Book direct</a></div>
{NAV_JS}<div class="cookie" id="cookie" hidden><p>We use analytics cookies to understand how guests find us. No advertising cookies.</p><div><button class="btn btn-outline" data-c="denied">Reject</button><button class="btn btn-primary" data-c="granted">Accept</button></div></div>
<script>(function(){{var b=document.getElementById('cookie'),c=null;try{{c=localStorage.getItem('ms_consent')}}catch(e){{}}if(!c)b.hidden=false;b.querySelectorAll('button').forEach(function(x){{x.addEventListener('click',function(){{var v=x.dataset.c;try{{localStorage.setItem('ms_consent',v)}}catch(e){{}}gtag('consent','update',{{analytics_storage:v}});b.hidden=true}})}});
document.addEventListener('click',function(e){{var a=e.target.closest('a');if(!a)return;var h=a.href||'';if(h.indexOf('bookingsboom.com')>-1||h.indexOf('book.maltesestays.com')>-1)gtag('event','begin_booking',{{link_url:h}});else if(h.indexOf('wa.me')>-1)gtag('event','whatsapp_click',{{link_url:h}});else if(h.indexOf('mailto:')===0)gtag('event','email_click')}})}})();</script>
"""

def page(path, title, meta, body, schema=None, og_image=None, active="", extra_head=""):
    schema_tag = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>' if schema else ""
    og = og_image or img(HERO_PIC, 1200, 630)
    head = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(meta)}">
<link rel="canonical" href="{canon(path)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{BRAND}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(meta)}"><meta property="og:url" content="{canon(path)}"><meta property="og:image" content="{og}"><meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%2332375D'/%3E%3Ctext x='32' y='41' text-anchor='middle' font-family='Inter,Arial' font-weight='700' font-size='24' fill='white'%3EMS%3C/text%3E%3C/svg%3E">
{extra_head}
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
var _c=null;try{{_c=localStorage.getItem('ms_consent')}}catch(e){{}}
gtag('consent','default',{{ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',analytics_storage:_c==='granted'?'granted':'denied',wait_for_update:500}});
gtag('js',new Date());gtag('config','{GA_ID}');</script>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<style>{CSS}</style>
{schema_tag}"""
    inner = f"{nav(active)}<main>{body}</main>{footer()}"
    if PREVIEW and path == "":
        return head + inner
    return f"<!doctype html>\n<html lang=\"en\">\n<head>\n{head}\n</head>\n<body>\n{inner}\n</body>\n</html>"

def org_schema():
    return {"@context": "https://schema.org", "@type": "LodgingBusiness", "@id": SITE + "/#org", "name": BRAND,
            "alternateName": "Maltese Stays by Landlord Care", "url": SITE, "telephone": "+" + WA, "email": EMAIL,
            "image": img(HERO_PIC, 1200, 800), "priceRange": "€€",
            "address": {"@type": "PostalAddress", "streetAddress": ADDRESS["street"], "addressLocality": ADDRESS["locality"], "postalCode": ADDRESS["postal"], "addressCountry": "MT"},
            "areaServed": [{"@type": "City", "name": a["name"]} for a in AREAS],
            "parentOrganization": {"@type": "Organization", "name": "Landlord Care", "url": OWNER_SITE},
            "description": "Licensed holiday homes, apartments and guest house rooms across Malta, professionally managed by a local team. Book direct for the best price."}

def crumbs(items):
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": canon(p)} for i, (n, p) in enumerate(items)]}
    html_ = ' <span aria-hidden="true">&rsaquo;</span> '.join(f'<a href="{url(p)}">{esc(n)}</a>' if i < len(items) - 1 else esc(n) for i, (n, p) in enumerate(items))
    return f'<nav class="crumbs" aria-label="Breadcrumb">{html_}</nav>', ld

def faq_html(pairs):
    return '<div class="faq">' + "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in pairs) + "</div>"

def faq_schema(pairs):
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]}

def card(l):
    return f"""<a class="card" href="{url('properties/'+l['slug'])}" data-area="{l['area']}" data-type="{l['type']}">
<div class="ph"><img src="{img(l['pics'][0], 640, 480)}" alt="{esc(l['name'])}, {esc(l['locality'])}, Malta" loading="lazy" width="640" height="480"></div>
<div class="body"><span class="kind">{esc(l['kind'])}</span><h3>{esc(l['name'])}</h3>
<div class="loc"><span>{esc(l['locality'])}</span>{score_badge(l)}</div>
<div class="specs"><span>{l['acc']} guests</span><span>{l['beds']} bed{'s' if l['beds']>1 else ''}</span><span>{fmt_baths(l['baths'])} bath{'s' if float(l['baths'])>1 else ''}</span></div></div></a>"""

def cards(ls):
    return '<div class="grid">' + "".join(card(l) for l in ls) + "</div>"

# ---------- HOME ----------
HOME_FAQ = [
    ("Why should I book direct instead of through Airbnb or Booking.com?", "Direct bookings skip the platform fees, so we can offer our lowest rate for the same dates. You also talk to the local team from the first message, not a call centre."),
    ("Are your properties licensed?", "Yes. Every home and room we manage holds a Malta Tourism Authority holiday licence, and the licence number is displayed in the property as the law requires."),
    ("Who looks after me during my stay?", "A local team based in Malta, reachable on WhatsApp 24 hours a day for anything from a late check-in to a restaurant recommendation."),
    ("What is the best area to stay in Malta?", "Valletta for history and walking everywhere, Sliema and St Julian's for the seafront and restaurants, the Three Cities for an authentic local feel at a lower price, and Msida, Pietà or Ta' Xbiex for space, terraces and pools a few minutes from everything."),
    ("Do you offer airport transfers or long stays?", "Yes. Message us on WhatsApp after booking for a transfer. For stays of a month or more we can quote a special rate."),
]

def home():
    featured_ids = [21762, 21750, 26837, 21768, 21770, 22404, 21752, 25738, 21755]
    featured = [l for i in featured_ids for l in LISTINGS if l["id"] == i][:9]
    if len(featured) < 6:
        featured += [l for l in LISTINGS if l not in featured and l["type"] == "home"][: 9 - len(featured)]
    areas = "".join(f"""<a class="area" href="{url('areas/'+a['slug'])}"><img src="{img(next(l for l in LISTINGS if l['area']==a['slug'])['pics'][0], 520, 416)}" alt="Holiday rentals in {esc(a['name'])}, Malta" loading="lazy" width="520" height="416"><div><strong>{esc(a['name'])}</strong><small>{esc(a['short'])} &middot; {sum(1 for l in LISTINGS if l['area']==a['slug'])} stays</small></div></a>""" for a in AREAS if any(l['area']==a['slug'] for l in LISTINGS))
    body = f"""
<div class="hero"><img src="{img(HERO_PIC, 1800, 1000)}" alt="" width="1800" height="1000" fetchpriority="high">
<div class="wrap"><div class="eyebrow">Licensed holiday homes in Malta</div>
<h1>Stay in Malta. Book direct with the local team.</h1>
<p>{len(LISTINGS)} apartments, townhouses, penthouses and guest house rooms in Valletta, Sliema, St Julian's, the Three Cities and beyond. Professionally managed, licensed, and cheaper when you book here than on Airbnb or Booking.com.</p>
<div class="actions"><a class="btn btn-primary" href="{url('properties')}">See all properties</a><a class="btn btn-outline" style="border-color:#fff;color:#fff" href="{url('book-direct')}">Why book direct</a></div></div></div>

<section><div class="wrap"><div class="sec-head"><div><div class="eyebrow">Hand-picked</div><h2>Featured stays</h2></div><a href="{url('properties')}">All {len(LISTINGS)} properties &rarr;</a></div>{cards(featured)}</div></section>

<section class="alt"><div class="wrap"><div class="sec-head"><div><div class="eyebrow">Where to stay</div><h2>Choose your corner of Malta</h2></div><p>Every area has its own pace. Pick yours.</p></div><div class="areas">{areas}</div></div></section>

<section><div class="wrap"><div class="eyebrow">Book direct</div><h2>Three reasons to book here instead of on a platform</h2>
<div class="why">
<div><div class="num">1</div><h3>Best price, always</h3><p>No platform commission means our direct rate is the lowest you will find for the same dates. </p></div>
<div><div class="num">2</div><h3>A real local team</h3><p>Landlord Care has managed homes in Malta for over four years. The people who answer your WhatsApp are the same people who look after the property.</p></div>
<div><div class="num">3</div><h3>Licensed and inspected</h3><p>Every property holds a Malta Tourism Authority licence. Professional cleaning, hotel-quality linen and 24/7 support come as standard.</p></div>
</div></div></section>

<section class="alt"><div class="wrap"><div class="eyebrow">Good to know</div><h2>Questions guests ask us</h2>{faq_html(HOME_FAQ)}</div></section>
"""
    schema = {"@context": "https://schema.org", "@graph": [org_schema(), {"@type": "WebSite", "url": SITE, "name": BRAND, "publisher": {"@id": SITE + "/#org"}}, faq_schema(HOME_FAQ)]}
    write("", page("", "Maltese Stays | Book direct holiday homes in Malta", "Book direct licensed holiday apartments, townhouses, penthouses and guest house rooms across Malta. Managed by a local team, best price when you book here.", body, schema, active=""))

# ---------- PROPERTIES INDEX ----------
def properties():
    crumb_html, crumb_ld = crumbs([("Home", ""), ("All properties", "properties")])
    area_btns = "".join(f'<button data-f="area" data-v="{a["slug"]}" aria-pressed="false">{esc(a["name"])}</button>' for a in AREAS)
    body = f"""<div class="hero hero-small"><img src="{img(HERO_PIC2, 1800, 700)}" alt="" width="1800" height="700"><div class="wrap">{crumb_html.replace('class="crumbs"','class="crumbs" style="color:#cfe0ff"')}<h1>All holiday homes and rooms in Malta</h1><p>{len(LISTINGS)} licensed stays across Malta. Filter by area or type, open any property and check live availability.</p></div></div>
<section><div class="wrap">
<div class="filters" id="filters"><button data-f="area" data-v="all" aria-pressed="true">All areas</button>{area_btns}<span class="sep"></span><button data-f="type" data-v="all" aria-pressed="true">Any type</button><button data-f="type" data-v="home" aria-pressed="false">Entire homes</button><button data-f="type" data-v="room" aria-pressed="false">Private rooms</button></div>
<p id="count" style="color:var(--slate)"></p>
{cards(LISTINGS)}
</div></section>
<script>
(function(){{var st={{area:'all',type:'all'}};var cards=[].slice.call(document.querySelectorAll('.card[data-area]'));var btns=[].slice.call(document.querySelectorAll('#filters button'));function apply(){{var n=0;cards.forEach(function(c){{var ok=(st.area==='all'||c.dataset.area===st.area)&&(st.type==='all'||c.dataset.type===st.type);c.hidden=!ok;if(ok)n++}});document.getElementById('count').textContent=n+' of '+cards.length+' stays';btns.forEach(function(b){{b.setAttribute('aria-pressed',st[b.dataset.f]===b.dataset.v?'true':'false')}})}}btns.forEach(function(b){{b.addEventListener('click',function(){{st[b.dataset.f]=b.dataset.v;apply()}})}});var h=location.hash.replace('#','');if(h){{if(['home','room'].indexOf(h)>-1)st.type=h;else st.area=h}}apply()}})();
</script>"""
    schema = {"@context": "https://schema.org", "@graph": [crumb_ld, {"@type": "ItemList", "name": "Holiday homes in Malta", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": canon("properties/" + l["slug"]), "name": l["name"]} for i, l in enumerate(LISTINGS)]}]}
    write("properties", page("properties", "All holiday homes and rooms in Malta | Maltese Stays", f"Browse {len(LISTINGS)} licensed holiday apartments, townhouses, penthouses and private rooms in Valletta, Sliema, St Julian's, the Three Cities, Msida, St Paul's Bay, Marsaskala and Rabat. Book direct.", body, schema, active="properties"))

# ---------- PROPERTY PAGES ----------
def property_page(l):
    a = AREA_BY[l["area"]]
    crumb_html, crumb_ld = crumbs([("Home", ""), (a["name"], "areas/" + a["slug"]), (l["name"], "properties/" + l["slug"])])
    gal = "".join(f'<a href="{img(p, 1600, 1200, "c_limit")}" target="_blank" rel="noopener"><img src="{img(p, 900, 675) if i == 0 else img(p, 600, 450)}" alt="{esc(l["name"])}, photo {i+1}" {"" if i == 0 else "loading=\"lazy\""} width="{900 if i==0 else 600}" height="{675 if i==0 else 450}"></a>' for i, p in enumerate(l["pics"][:5]))
    hl = "".join(f"<li>{esc(h)}</li>" for h in l["highlights"])
    tags = "".join(f"<span>{esc(t)}</span>" for t in l["good_for"])
    note = f'<p class="note">{esc(l["note"])}</p>' if l.get("note") else ""
    group = GROUP_BY.get(l.get("group"))
    group_html = ""
    if group:
        others = [o for o in LISTINGS if o.get("group") == group["slug"] and o["id"] != l["id"]]
        group_html = f"""<h2 style="font-size:1.5rem">Part of {esc(group['name'])}</h2><p>{esc(group['intro'])}</p><p><a href="{url('guest-houses/'+group['slug'])}">See all rooms in this guest house &rarr;</a></p>"""
    similar = [o for o in LISTINGS if o["area"] == l["area"] and o["id"] != l["id"] and o.get("group") != l.get("group")][:3]
    if len(similar) < 3:
        similar += [o for o in LISTINGS if o["id"] != l["id"] and o not in similar and o["type"] == l["type"]][: 3 - len(similar)]
    faq = [
        (f"How do I book {l['name']}?", f"Click Check availability, choose your dates and pay securely on our booking site."),
        ("What is included?", "Fresh linen and towels, a fully equipped kitchen" + (" shared with other guests" if l["type"] == "room" else "") + ", WiFi, air conditioning and 24/7 support from our local team on WhatsApp."),
        ("Is the property licensed?", "Yes. It holds a Malta Tourism Authority holiday licence and the number is displayed inside the property."),
        ("How far is it from the airport?", f"{a['name']} is roughly {('20 minutes' if l['area'] in ('marsaskala','three-cities') else '30 to 40 minutes' if l['area'] in ('st-pauls-bay','rabat-mdina') else '25 to 30 minutes')} from Malta International Airport by taxi. We can arrange a transfer on request."),
    ]
    body = f"""<section style="padding-top:1.5rem"><div class="wrap">{crumb_html}
<div class="eyebrow">{esc(l['kind'])} in {esc(l['locality'])}</div>
<h1>{esc(l['name'])}</h1>
<div class="specs-big"><span><b>{l['acc']}</b> guests</span><span><b>{l['beds']}</b> bedroom{'s' if l['beds']>1 else ''}</span><span><b>{fmt_baths(l['baths'])}</b> bathroom{'s' if float(l['baths'])>1 else ''}</span>{('<span>' + score_badge(l) + ' on Airbnb</span>') if l.get('score') else ''}</div>
<div class="gallery">{gal}</div>
<div class="prop"><div class="main">
<p style="font-size:1.1rem">{esc(l['intro'])}</p>
<div class="tags">{tags}</div>
<h2 style="font-size:1.5rem">Highlights</h2><ul class="hl">{hl}</ul>
<h2 style="font-size:1.5rem">Sleeping arrangements</h2><p>{esc(l['sleeps'])}</p>
<h2 style="font-size:1.5rem">The neighbourhood</h2><p>{esc(l['nearby'])}</p><p><a href="{url('areas/'+a['slug'])}">More about staying in {esc(a['name'])} &rarr;</a></p>
{note}{group_html}
<h2 style="font-size:1.5rem">Questions about this stay</h2>{faq_html(faq)}
</div>
<aside class="bookbox"><strong style="font-family:var(--display);font-size:1.3rem;color:var(--navy)">Book direct and save</strong>
<small>Our lowest rate is always here. No platform fees, and you deal directly with our local team.</small>
<a class="btn btn-primary" href="{book_url(l)}" rel="noopener">Check availability</a>
<a class="btn btn-wa" href="{WA_URL}" rel="noopener">{WA_ICON} Ask on WhatsApp</a>
<small>Licensed by the Malta Tourism Authority. Local team available 24/7.</small></aside>
</div></div></section>
<section class="alt"><div class="wrap"><div class="sec-head"><h2 style="font-size:1.6rem">You may also like</h2><a href="{url('properties')}">All properties &rarr;</a></div>{cards(similar)}</div></section>"""
    schema = {"@context": "https://schema.org", "@graph": [crumb_ld, {
        "@type": "VacationRental" if l["type"] == "home" else "LodgingBusiness", "@id": canon("properties/" + l["slug"]) + "#stay",
        "name": l["name"], "description": l["intro"], "url": canon("properties/" + l["slug"]),
        "image": [img(p, 1200, 900) for p in l["pics"][:5]],
        "address": {"@type": "PostalAddress", "addressLocality": l["locality"], "addressRegion": "Malta", "addressCountry": "MT"},
        "geo": {"@type": "GeoCoordinates", "latitude": l["lat"], "longitude": l["lng"]},
        "numberOfRooms": l["beds"], "numberOfBedrooms": l["beds"], "numberOfBathroomsTotal": l["baths"],
        "occupancy": {"@type": "QuantitativeValue", "maxValue": l["acc"]},
        "amenityFeature": [{"@type": "LocationFeatureSpecification", "name": h, "value": True} for h in l["highlights"]],
        "petsAllowed": False, "checkinTime": "15:00", "checkoutTime": "10:00",
        "containedInPlace": {"@type": "Place", "name": l["locality"] + ", Malta"},
        "brand": {"@id": SITE + "/#org"}, "potentialAction": {"@type": "ReserveAction", "target": book_url(l)},
        **({"aggregateRating": {"@type": "AggregateRating", "ratingValue": l["score"], "bestRating": 5, "ratingCount": 1}} if False else {})
    }, faq_schema(faq)]}
    title = f"{l['name']} | {l['kind']} in {l['locality']}, Malta"
    meta = f"{l['intro'][:150].rsplit(' ',1)[0]}. Sleeps {l['acc']}. Licensed, locally managed. Book direct for the best price."
    write("properties/" + l["slug"], page("properties/" + l["slug"], title, meta, body, schema, og_image=img(l["pics"][0], 1200, 630), active="properties"))

# ---------- AREAS ----------
def areas_index():
    crumb_html, crumb_ld = crumbs([("Home", ""), ("Areas", "areas")])
    items = ""
    for a in AREAS:
        ls = [l for l in LISTINGS if l["area"] == a["slug"]]
        if not ls:
            continue
        items += f"""<a class="area" href="{url('areas/'+a['slug'])}"><img src="{img(ls[0]['pics'][0], 520, 416)}" alt="Holiday rentals in {esc(a['name'])}, Malta" loading="lazy" width="520" height="416"><div><strong>{esc(a['name'])}</strong><small>{esc(a['short'])} &middot; {len(ls)} stays</small></div></a>"""
    body = f"""<section><div class="wrap">{crumb_html}<div class="eyebrow">Where to stay in Malta</div><h1>Areas we cover</h1><p style="font-size:1.1rem">Malta is small, but each town has a different feel. Here is where our homes are and who each area suits.</p><div class="areas" style="margin-top:1.5rem">{items}</div></div></section>"""
    write("areas", page("areas", "Where to stay in Malta: areas and neighbourhoods | Maltese Stays", "Valletta, Sliema, St Julian's, the Three Cities, Msida and Pietà, St Paul's Bay, Marsaskala, Rabat and Mdina. Which area of Malta suits you, with licensed holiday homes in each.", body, {"@context": "https://schema.org", "@graph": [crumb_ld]}, active="areas"))

def area_page(a):
    ls = [l for l in LISTINGS if l["area"] == a["slug"]]
    if not ls:
        print(f"  area {a['slug']} has no listings; page skipped")
        return
    crumb_html, crumb_ld = crumbs([("Home", ""), ("Areas", "areas"), (a["name"], "areas/" + a["slug"])])
    why = "".join(f"<li>{esc(w)}</li>" for w in a["why"])
    tips = "".join(f"<li>{esc(t)}</li>" for t in a["tips"])
    groups_here = [g for g in GROUPS if g["area"] == a["slug"]]
    gh = ""
    if groups_here:
        gh = "<h2 style='font-size:1.5rem'>Guest houses in this area</h2><ul class='check'>" + "".join(f'<li><a href="{url("guest-houses/"+g["slug"])}">{esc(g["name"])}</a></li>' for g in groups_here) + "</ul>"
    body = f"""<div class="hero hero-small"><img src="{img(ls[0]['pics'][0], 1800, 800)}" alt="" width="1800" height="800"><div class="wrap"><div class="eyebrow">{esc(a['short'])}</div><h1>{esc(a['h1'])}</h1><p>{len(ls)} licensed {'stay' if len(ls)==1 else 'stays'} in {esc(a['name'])}, managed by our local team. Book direct for the best price.</p></div></div>
<section><div class="wrap">{crumb_html}<div class="two"><div><h2>About {esc(a['name'])}</h2><p style="font-size:1.08rem">{esc(a['intro'])}</p></div>
<div><h3>Why stay here</h3><ul class="check">{why}</ul><h3>Our tips</h3><ul class="check">{tips}</ul>{gh}</div></div></div></section>
<section class="alt"><div class="wrap"><div class="sec-head"><h2>Our stays in {esc(a['name'])}</h2><a href="{url('properties')}">All properties &rarr;</a></div>{cards(ls)}</div></section>
<section><div class="wrap"><h2>Questions about {esc(a['name'])}</h2>{faq_html(a['faq'])}</div></section>"""
    schema = {"@context": "https://schema.org", "@graph": [crumb_ld, faq_schema(a["faq"]), {"@type": "ItemList", "name": f"Holiday rentals in {a['name']}", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": canon("properties/" + l["slug"]), "name": l["name"]} for i, l in enumerate(ls)]}]}
    write("areas/" + a["slug"], page("areas/" + a["slug"], f"{a['h1']} | Book direct", a["meta"], body, schema, og_image=img(ls[0]["pics"][0], 1200, 630), active="areas"))

# ---------- GUEST HOUSES ----------
def guest_houses():
    crumb_html, crumb_ld = crumbs([("Home", ""), ("Guest houses", "guest-houses")])
    blocks = ""
    for g in GROUPS:
        ls = [l for l in LISTINGS if l.get("group") == g["slug"]]
        blocks += f"""<div style="margin-bottom:3rem"><div class="sec-head"><div><div class="eyebrow">{esc(AREA_BY[g['area']]['name'])}</div><h2 style="font-size:1.7rem"><a href="{url('guest-houses/'+g['slug'])}" style="text-decoration:none;color:inherit">{esc(g['name'])}</a></h2></div><a href="{url('guest-houses/'+g['slug'])}">About this house &rarr;</a></div><p>{esc(g['intro'])}</p>{cards(ls)}</div>"""
    body = f"""<section><div class="wrap">{crumb_html}<div class="eyebrow">Private rooms, shared spaces</div><h1>Guest houses in Malta</h1><p style="font-size:1.1rem;max-width:70ch">Private ensuite rooms in three characterful houses: a family-run guest house in Cospicua, a renovated palazzo in Senglea and a townhouse in Sliema. The right choice for couples and solo travellers who want a local base at a sensible price.</p>{blocks}</div></section>"""
    write("guest-houses", page("guest-houses", "Guest houses and private rooms in Malta | Maltese Stays", "Private ensuite rooms in a family guest house in Cospicua, Jungle Palazzo in Senglea and a Sliema townhouse. Licensed, locally managed, book direct for the best price.", body, {"@context": "https://schema.org", "@graph": [crumb_ld]}, active="guest-houses"))

def group_page(g):
    ls = [l for l in LISTINGS if l.get("group") == g["slug"]]
    a = AREA_BY[g["area"]]
    crumb_html, crumb_ld = crumbs([("Home", ""), ("Guest houses", "guest-houses"), (g["name"], "guest-houses/" + g["slug"])])
    shared = "".join(f"<li>{esc(s)}</li>" for s in g["shared"])
    body = f"""<div class="hero hero-small"><img src="{img(ls[0]['pics'][1], 1800, 800)}" alt="" width="1800" height="800"><div class="wrap"><div class="eyebrow">{esc(a['name'])}</div><h1>{esc(g['h1'])}</h1><p>{len(ls)} private rooms, each with its own bathroom. Book direct for the best price.</p></div></div>
<section><div class="wrap">{crumb_html}<div class="two"><div><h2>The house</h2><p style="font-size:1.08rem">{esc(g['intro'])}</p><p><a href="{url('areas/'+a['slug'])}">More about {esc(a['name'])} &rarr;</a></p></div><div><h3>Shared spaces and services</h3><ul class="check">{shared}</ul><a class="btn btn-wa" href="{WA_URL}" rel="noopener">{WA_ICON} Ask about group bookings</a></div></div></div></section>
<section class="alt"><div class="wrap"><h2>Rooms</h2>{cards(ls)}</div></section>"""
    schema = {"@context": "https://schema.org", "@graph": [crumb_ld, {"@type": "LodgingBusiness", "name": g["name"], "description": g["intro"], "url": canon("guest-houses/" + g["slug"]), "image": img(ls[0]["pics"][0], 1200, 900), "address": {"@type": "PostalAddress", "addressLocality": ls[0]["locality"], "addressCountry": "MT"}, "geo": {"@type": "GeoCoordinates", "latitude": ls[0]["lat"], "longitude": ls[0]["lng"]}, "numberOfRooms": len(ls), "parentOrganization": {"@id": SITE + "/#org"}}]}
    write("guest-houses/" + g["slug"], page("guest-houses/" + g["slug"], f"{g['h1']} | Book direct", g["meta"], body, schema, og_image=img(ls[0]["pics"][0], 1200, 630), active="guest-houses"))

# ---------- BOOK DIRECT ----------
BD_FAQ = [
    ("Is it safe to book directly on your website?", "Yes. Payments go through our booking system with card processing by a regulated provider, and you receive a confirmation email with the full details of your stay straight away."),
    ("What is your cancellation policy?", "Each property shows its cancellation terms on the booking page before you pay. Most of our homes offer free cancellation up to a set number of days before arrival."),
    ("Can I pay in instalments or on arrival?", "Payment is taken online at the time of booking. For stays of a month or more, contact us on WhatsApp and we can agree a schedule."),
    ("Do I get the same service as on Airbnb?", "Better. You deal with our local team from the first message, we can hold dates while you sort flights, and we can arrange transfers, early check-in or extra beds without a platform in the middle."),
]

def book_direct():
    crumb_html, crumb_ld = crumbs([("Home", ""), ("Why book direct", "book-direct")])
    body = f"""<section><div class="wrap">{crumb_html}<div class="eyebrow">Book direct</div><h1>The same homes, a better price, a real person on the other end</h1>
<div class="two" style="margin-top:1.5rem"><div><p style="font-size:1.1rem">Airbnb and Booking.com charge guests and hosts a commission on every stay. When you book on this site that commission disappears, and we pass the difference to you.</p>
<ul class="check"><li>Our lowest rate for every date, guaranteed</li><li>Talk to the local team on WhatsApp before and during your stay</li><li>Transfers, early check-in, extra beds and long-stay rates arranged directly</li><li>Secure online payment and instant confirmation</li></ul>
<div style="display:flex;gap:.8rem;flex-wrap:wrap"><a class="btn btn-primary" href="{url('properties')}">Find your stay</a><a class="btn btn-wa" href="{WA_URL}" rel="noopener">{WA_ICON} Ask us anything</a></div></div>
<div><h3>How it works</h3><ol style="padding-left:1.2rem;display:grid;gap:.6rem"><li>Choose a property and click <b>Check availability</b>.</li><li>Pick your dates and number of guests on our booking site.</li><li>Pay securely. Your confirmation and check-in details arrive by email.</li><li>Message us on WhatsApp for anything else, any time.</li></ol></div></div></div></section>
<section class="alt"><div class="wrap"><h2>Questions about booking direct</h2>{faq_html(BD_FAQ)}</div></section>"""
    write("book-direct", page("book-direct", "Why book direct with Maltese Stays | Best price in Malta", "Book your Malta holiday home directly and skip platform fees: lowest rate guaranteed, and a local team on WhatsApp 24/7.", body, {"@context": "https://schema.org", "@graph": [crumb_ld, faq_schema(BD_FAQ)]}, active="book-direct"))

# ---------- ABOUT / CONTACT ----------
def about():
    crumb_html, crumb_ld = crumbs([("Home", ""), ("About us", "about")])
    body = f"""<section><div class="wrap">{crumb_html}<div class="eyebrow">About</div><h1>A small Malta-based team that looks after every home as if it were ours</h1>
<div class="two" style="margin-top:1.5rem"><div><p style="font-size:1.1rem">Maltese Stays is the guest brand of Landlord Care, a boutique short-let management company founded in Malta over four years ago. We manage around thirty homes for their owners, from Valletta townhouses to penthouses with pools, and we deliberately keep the portfolio small so that we can look after each one properly.</p>
<p>The team lives in Malta. We set up each home, photograph it, keep it maintained, and answer guests ourselves. Every property holds a Malta Tourism Authority holiday licence, is professionally cleaned between stays, and comes with hotel-quality linen and a local contact available around the clock.</p>
<p>Own a property in Malta? See <a href="{OWNER_SITE}" rel="noopener">landlord.care</a> for our management service.</p></div>
<div><h3>What every stay includes</h3><ul class="check"><li>Malta Tourism Authority holiday licence</li><li>Professional cleaning and fresh linen</li><li>Fully equipped kitchen and WiFi</li><li>Self check-in on most properties</li><li>Local team on WhatsApp 24/7</li><li>Best price when you book direct</li></ul></div></div></div></section>"""
    write("about", page("about", "About Maltese Stays | Local hosts in Malta", "Maltese Stays is the guest brand of Landlord Care, a boutique short-let management company based in Malta for over four years. Licensed homes, local team, direct booking.", body, {"@context": "https://schema.org", "@graph": [crumb_ld, org_schema()]}, active="about"))

def contact():
    crumb_html, crumb_ld = crumbs([("Home", ""), ("Contact", "contact")])
    body = f"""<section><div class="wrap">{crumb_html}<div class="eyebrow">Contact</div><h1>Talk to the team in Malta</h1>
<div class="two" style="margin-top:1.5rem"><div><p style="font-size:1.1rem">The fastest way to reach us is WhatsApp. We reply within minutes during the day and we are reachable 24 hours a day for guests who are staying with us.</p>
<p><b>WhatsApp and phone:</b> <a href="{WA_URL}" rel="noopener">{PHONE_DISPLAY}</a><br><b>Email:</b> <a href="mailto:{EMAIL}">{EMAIL}</a><br><b>Office:</b> {ADDRESS['street']}, {ADDRESS['locality']} {ADDRESS['postal']}, Malta</p>
<div style="display:flex;gap:.8rem;flex-wrap:wrap"><a class="btn btn-wa" href="{WA_URL}" rel="noopener">{WA_ICON} Open WhatsApp</a><a class="btn btn-outline" href="mailto:{EMAIL}">Send an email</a></div></div>
<div><h3>Before you message</h3><ul class="check"><li>Availability and prices are live on each property page under <b>Check availability</b></li><li>Group of more than six? Tell us the dates and we will combine homes or rooms</li><li>Stays of a month or more get a special rate: ask us</li><li>Airport transfers can be arranged for any booking</li></ul></div></div></div></section>"""
    write("contact", page("contact", "Contact Maltese Stays | WhatsApp the local team in Malta", "Contact the Maltese Stays team in Malta on WhatsApp or email for bookings, group stays, long stays and airport transfers.", body, {"@context": "https://schema.org", "@graph": [crumb_ld, org_schema()]}, active="contact"))

def not_found():
    body = f"""<section><div class="wrap"><h1>That page is not here</h1><p>Use the menu above, or start from all properties.</p><a class="btn btn-primary" href="{url('properties')}">All properties</a></div></section>"""
    with open(os.path.join(OUT, "404.html"), "w", encoding="utf-8") as f:
        f.write(page("404", "Page not found", "Page not found", body).replace('<meta name="robots" content="index,follow,max-image-preview:large">', '<meta name="robots" content="noindex">'))

# ---------- SITEMAP / ROBOTS / LLMS ----------
def extras():
    paths = ["", "properties", "areas", "guest-houses", "book-direct", "about", "contact"] + [f"areas/{a['slug']}" for a in AREAS if any(l['area']==a['slug'] for l in LISTINGS)] + [f"guest-houses/{g['slug']}" for g in GROUPS] + [f"properties/{l['slug']}" for l in LISTINGS]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in paths:
        pri = "1.0" if p == "" else "0.9" if p.startswith("areas/") or p == "properties" else "0.8"
        sm += f"  <url><loc>{canon(p)}</loc><lastmod>{TODAY}</lastmod><priority>{pri}</priority></url>\n"
    sm += "</urlset>\n"
    open(os.path.join(OUT, "sitemap.xml"), "w").write(sm)
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    llms = f"# {BRAND}\n\n> Licensed holiday homes, apartments, penthouses and guest house rooms across Malta, managed by Landlord Care, a boutique short-let management company based in Sliema, Malta. Guests book directly at {SITE} for the lowest rate. Contact: WhatsApp {PHONE_DISPLAY}, {EMAIL}.\n\n## Areas\n"
    for a in AREAS:
        llms += f"- [{a['name']}]({canon('areas/'+a['slug'])}): {a['short']}. {sum(1 for l in LISTINGS if l['area']==a['slug'])} stays.\n"
    llms += "\n## Properties\n"
    for l in LISTINGS:
        llms += f"- [{l['name']}]({canon('properties/'+l['slug'])}): {l['kind']} in {l['locality']}, sleeps {l['acc']}, {l['beds']} bedroom(s). {l['intro'][:140].rsplit(' ',1)[0]}.\n"
    llms += f"\n## Guest houses\n" + "".join(f"- [{g['name']}]({canon('guest-houses/'+g['slug'])})\n" for g in GROUPS)
    llms += f"\n## Other\n- [Why book direct]({canon('book-direct')})\n- [About]({canon('about')})\n- [Contact]({canon('contact')})\n- Owners: property management at {OWNER_SITE}\n"
    open(os.path.join(OUT, "llms.txt"), "w", encoding="utf-8").write(llms)
    if not PREVIEW:
        open(os.path.join(OUT, "CNAME"), "w").write(SITE.replace("https://", "") + "\n")
        open(os.path.join(OUT, ".nojekyll"), "w").write("")

# ---------- RUN ----------
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
home(); properties(); areas_index(); guest_houses(); book_direct(); about(); contact(); not_found(); extras()
for l in LISTINGS: property_page(l)
for a in AREAS: area_page(a)
for g in GROUPS: group_page(g)
n = sum(len(f) for _, _, f in os.walk(OUT))
print(f"built {n} files in {OUT}")
