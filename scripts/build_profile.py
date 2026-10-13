#!/usr/bin/env python3
"""Build the whole GitHub profile (README + every SVG) from LIVE GitHub data.

Usage:  python scripts/build_profile.py <github-username>

Env (all optional):
  GITHUB_TOKEN  - provided automatically inside GitHub Actions (higher API rate limit)
  GH_PAT        - classic token with `read:user`: includes PRIVATE contributions in the calendar
  PROFILE_FIXTURE - path to a JSON file to use instead of the GitHub API (offline testing)
"""
import html
import json
import math
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER = sys.argv[1] if len(sys.argv) > 1 else "msrajput12"
TOKEN = os.environ.get("GH_PAT", "").strip()
API_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip() or TOKEN
FIXTURE = os.environ.get("PROFILE_FIXTURE", "")

# ---- tweakables --------------------------------------------------------------
PALETTE = "blue"                       # calendar colours: "blue" or "github"
FALLBACK_BIO = "Build useful things. Share the work in public."
MAX_PROJECTS = 6
FACE_BOX = (0.164, 0.03, 0.735, 0.77)  # (left, top, right, bottom) of the avatar used for the ASCII face
# ------------------------------------------------------------------------------

LANG_COLORS = {"Python": "#3572A5", "Swift": "#F05138", "Java": "#b07219", "JavaScript": "#f1e05a",
               "TypeScript": "#3178c6", "C++": "#f34b7d", "C": "#8a8a8a", "C#": "#178600", "Go": "#00ADD8",
               "Rust": "#dea584", "Kotlin": "#A97BFF", "HTML": "#e34c26", "CSS": "#663399",
               "Shell": "#89e051", "Dart": "#00B4AB", "PHP": "#4F5D95", "Ruby": "#701516"}
SNIPPETS = {
    "Python": ["def build(idea):", "    return ship(idea)"],
    "Swift": ["func build(_ idea: String) {", "    ship(idea)", "}"],
    "Java": ["static void build(String idea) {", "    ship(idea);", "}"],
    "JavaScript": ["const build = (idea) => {", "  return ship(idea);", "};"],
    "TypeScript": ["const build = (idea: string) => {", "  return ship(idea);", "};"],
    "C++": ["void build(string idea) {", "    ship(idea);", "}"],
    "C": ["void build(char *idea) {", "    ship(idea);", "}"],
    "Go": ["func build(idea string) {", "    ship(idea)", "}"],
    "Rust": ["fn build(idea: &str) {", "    ship(idea);", "}"],
    "Kotlin": ["fun build(idea: String) {", "    ship(idea)", "}"],
    "HTML": ["<main>", "  <h1>build(idea)</h1>", "</main>"],
    "Shell": ["build() {", "  ship \"$1\"", "}"],
}
DEFAULT_SNIPPET = ["// build(idea)", "// ship(idea)"]

esc = lambda s: html.escape(str(s), quote=False)


def short(s, n):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def rel(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    d = (datetime.now(timezone.utc) - dt).days
    if d < 1:
        return "today"
    if d == 1:
        return "yesterday"
    if d < 14:
        return f"{d} days ago"
    if d < 60:
        return f"{d // 7} weeks ago"
    if d < 365:
        return f"{d // 30} months ago"
    y = d // 365
    return f"{y} year{'s' if y > 1 else ''} ago"


def http(url, headers=None, data=None, binary=False):
    h = {"User-Agent": "profile-builder"}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=30) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", "ignore")


def api(path):
    h = {"Accept": "application/vnd.github+json"}
    if API_TOKEN:
        h["Authorization"] = f"Bearer {API_TOKEN}"
    return json.loads(http("https://api.github.com" + path, h))


# =============================== DATA =========================================
def load_data():
    if FIXTURE:
        return json.load(open(FIXTURE, encoding="utf-8"))
    info = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner&sort=pushed")
    return {"info": info, "repos": repos}


def avatar_image(url):
    from PIL import Image
    import io
    if url.startswith("/"):
        return Image.open(url).convert("RGB")
    sep = "&" if "?" in url else "?"
    return Image.open(io.BytesIO(http(url + sep + "s=460", binary=True))).convert("RGB")


# =============================== FACE =========================================
def face_fragment(img, cx=930, cy=285, cols=52, rows=44, cw=5.8, ch=8.35, rmax=178):
    import numpy as np
    from PIL import Image, ImageDraw
    g = img.convert("L")
    side = min(g.size)
    g = g.crop((0, 0, side, side))
    m = Image.new("L", g.size, 0)
    pad = int(side * 0.04)
    ImageDraw.Draw(m).ellipse((pad, pad, side - pad, side - pad), fill=255)
    g = Image.composite(g, Image.new("L", g.size, 0), m)
    l, t, r, b = FACE_BOX
    g = g.crop((int(l * side), int(t * side), int(r * side), int(b * side)))
    a = np.asarray(g.resize((cols, rows), Image.BOX)).astype(float) / 255
    a = np.clip(a / max(np.percentile(a, 99.5), 1e-6), 0, 1) ** 0.5
    ramp = [None, ".", ":", "+", "#"]
    th = [0.2, 0.34, 0.5, 0.68]
    x0, y0 = cx - cols * cw / 2, cy - rows * ch / 2
    out = []
    for r_ in range(rows):
        by = {1: [], 2: [], 3: [], 4: []}
        for c_ in range(cols):
            lv = sum(a[r_, c_] >= t_ for t_ in th)
            x, y = x0 + c_ * cw + cw / 2, y0 + r_ * ch + ch
            if lv == 0 or math.hypot(x - cx, y - ch / 2 - cy) > rmax:
                continue
            by[lv].append((round(x, 1), ramp[lv]))
        d = min(7, r_ * 8 // rows)
        yy = round(y0 + r_ * ch + ch, 1)
        for lv, items in by.items():
            if items:
                xs = " ".join(str(int(x) if x == int(x) else x) for x, _ in items)
                out.append(f'<text class="a l{lv} d{d}" y="{yy}" x="{xs}">{"".join(c for _, c in items)}</text>')
    return "<g>\n  " + "\n  ".join(out) + "\n</g>"


def get_face(info):
    frag_path = os.path.join(ROOT, "assets", "face.svgfrag")
    try:
        frag = face_fragment(avatar_image(info["avatar_url"]))
        open(frag_path, "w", encoding="utf-8").write(frag)
        print("face: generated from avatar")
        return frag
    except Exception as exc:
        print("face: using saved fragment (", exc, ")")
        return open(frag_path, encoding="utf-8").read()


# ============================== CALENDAR ======================================
def fetch_calendar(year, today):
    FROM, TO = f"{year}-01-01", f"{year}-12-31"
    private = False
    days = None
    if TOKEN:
        try:
            q = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
              contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{
              date contributionCount contributionLevel weekday}}}}}}"""
            body = json.dumps({"query": q, "variables": {"login": USER, "from": f"{FROM}T00:00:00Z",
                                                          "to": f"{TO}T23:59:59Z"}}).encode()
            data = json.loads(http("https://api.github.com/graphql",
                                   {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}, body))
            if "errors" in data:
                raise RuntimeError(data["errors"])
            lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
            days = []
            for wi, w in enumerate(data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]):
                for d in w["contributionDays"]:
                    days.append(dict(date=d["date"], row=d["weekday"], col=wi,
                                     level=lv.get(d["contributionLevel"], 0), count=d["contributionCount"]))
            private = True
        except Exception as exc:
            print("calendar: GraphQL failed, using public page:", exc)
    if not days:
        page = http(f"https://github.com/users/{USER}/contributions?from={FROM}&to={TO}")
        cells = {}
        for td in re.finditer(r"<td\b[^>]*ContributionCalendar-day[^>]*>", page):
            tag = td.group(0)
            d = re.search(r'data-date="([\d-]+)"', tag)
            i = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
            lv = re.search(r'data-level="(\d)"', tag)
            if d and i and lv:
                cells[f"contribution-day-component-{i.group(1)}-{i.group(2)}"] = dict(
                    date=d.group(1), row=int(i.group(1)), col=int(i.group(2)), level=int(lv.group(1)), count=0)
        for tip in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
            m = re.match(r"\s*(\d+)\s+contribution", tip.group(2))
            if tip.group(1) in cells and m:
                cells[tip.group(1)]["count"] = int(m.group(1))
        days = list(cells.values())
    days.sort(key=lambda c: c["date"])
    if not days:
        raise RuntimeError("no calendar data")
    return days, private


def calendar_svg(days, private, year, today):
    past = [c for c in days if c["date"] <= today.isoformat()]
    total = sum(c["count"] for c in days)
    active = sum(1 for c in past if c["count"] > 0)
    best = max(past, key=lambda c: c["count"])
    streak = longest = 0
    for c in past:
        streak = streak + 1 if c["count"] > 0 else 0
        longest = max(longest, streak)
    W, H, Y0, PITCH, SZ = 1200, 400, 150, 16, 13
    cols = max(c["col"] for c in days) + 1
    X0 = int((W - cols * PITCH) / 2) + 22
    COLORS = {"blue": ["#111c2e", "#1d4e89", "#2879bd", "#3999df", "#69b8ff"],
              "github": ["#151b23", "#0e4429", "#006d32", "#26a641", "#39d353"]}[PALETTE]
    MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    rects, first = [], {}
    for c in days:
        x, y = X0 + c["col"] * PITCH, Y0 + c["row"] * PITCH
        delay = round(c["col"] * 0.03 + c["row"] * 0.01, 2)
        cls = f"c l{c['level']}" + (" hot" if c["level"] >= 3 else "")
        n = c["count"]
        rects.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{SZ}" height="{SZ}" rx="3" style="animation-delay:{delay}s">'
                     f'<title>{n} contribution{"s" if n != 1 else ""} on {c["date"]}</title></rect>')
        first.setdefault(int(c["date"][5:7]), c["col"])
    months = "".join(f'<text x="{X0 + col * PITCH}" y="{Y0 - 12}">{MONTHS[m - 1]}</text>' for m, col in first.items())
    cur = past[-1]
    tx, ty = X0 + cur["col"] * PITCH, Y0 + cur["row"] * PITCH
    best_d = date.fromisoformat(best["date"]).strftime("%b %d").upper()
    upd = today.strftime("%d %b %Y").upper() + (" · INCLUDES PRIVATE" if private else "")
    lx = X0 + cols * PITCH - 5 * (SZ + 3) - 70
    legend = "".join(f'<rect x="{lx + 40 + i * (SZ + 3)}" y="{Y0 + 7 * PITCH + 8}" width="{SZ}" height="{SZ}" rx="3" fill="{col}"/>'
                     for i, col in enumerate(COLORS))
    css = (".c{animation:pop .6s ease-out backwards;transform-box:fill-box;transform-origin:center}"
           f".l0{{fill:{COLORS[0]}}}.l1{{fill:{COLORS[1]}}}.l2{{fill:{COLORS[2]}}}.l3{{fill:{COLORS[3]}}}.l4{{fill:{COLORS[4]}}}"
           "@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}"
           ".hot{animation:pop .6s ease-out backwards,glow 3s ease-in-out 1.8s infinite}"
           "@keyframes glow{0%,100%{opacity:1}50%{opacity:.6}}"
           ".now{animation:ring 1.8s ease-in-out infinite}@keyframes ring{0%,100%{opacity:.2}50%{opacity:1}}")
    body = f'''<g fill="#93a8c9" font-size="15"><text x="48" y="55" letter-spacing="4">OPEN-SOURCE SIGNAL</text><text x="{W-48}" y="55" text-anchor="end">@{esc(USER)} / {year}</text></g>
<text x="48" y="95" fill="#3999df" font-size="13" letter-spacing="4">{total} CONTRIBUTIONS IN {year}</text>
<text x="{W-48}" y="95" text-anchor="end" fill="#44566f" font-size="11" letter-spacing="2">UPDATED {upd}</text>
<g fill="#6f84a6" font-size="11" letter-spacing="1">{months}</g>
<g fill="#6f84a6" font-size="11"><text x="{X0-44}" y="{Y0+27}">MON</text><text x="{X0-44}" y="{Y0+59}">WED</text><text x="{X0-44}" y="{Y0+91}">FRI</text></g>
{chr(10).join(rects)}
<rect class="now" x="{tx-2}" y="{ty-2}" width="{SZ+4}" height="{SZ+4}" rx="5" fill="none" stroke="#69b8ff" stroke-width="1.5"/>
<g fill="#6f84a6" font-size="11"><text x="{lx}" y="{Y0+7*PITCH+19}">LESS</text><text x="{lx+40+5*(SZ+3)+4}" y="{Y0+7*PITCH+19}">MORE</text></g>
{legend}
<line x1="48" y1="300" x2="{W-48}" y2="300" stroke="#29364b"/>
<g class="fu" style="animation-delay:1.2s">
<g fill="#94a8c7" font-size="13" letter-spacing="2"><text x="50" y="335">CONTRIBUTIONS</text><text x="330" y="335">ACTIVE DAYS</text><text x="610" y="335">LONGEST STREAK</text><text x="910" y="335">BEST DAY</text></g>
<g fill="#e8efff" font-size="35"><text x="50" y="378">{total}</text><text x="330" y="378">{active}</text><text x="610" y="378">{longest}<tspan font-size="14" fill="#94a8c7"> days</tspan></text><text x="910" y="378">{best["count"]}<tspan font-size="14" fill="#94a8c7"> on {best_d}</tspan></text></g></g>'''
    return frame(W, H, body, css), total


# ============================== SVG FRAME =====================================
BASE_CSS = """text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.fu{animation:fu .8s ease-out backwards}@keyframes fu{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.p{animation:pl 2.4s ease-in-out infinite}@keyframes pl{0%,100%{opacity:.35}50%{opacity:1}}
.bl{animation:bl 1.1s steps(2,start) infinite}@keyframes bl{to{opacity:0}}
"""


def frame(w, h, body, css="", rx=26, scan=True):
    sc = (f'<rect x="-300" width="300" height="{h}" fill="url(#s)"><animate attributeName="x" values="-300;{w}" dur="8s" repeatCount="indefinite"/></rect>' if scan else "")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
<pattern id="g" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="#172236"/></pattern>
<linearGradient id="r" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2879bd"/><stop offset="1" stop-color="#7668bd"/></linearGradient>
<linearGradient id="nm" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f0f5ff"/><stop offset="1" stop-color="#9eb8df"/></linearGradient>
<linearGradient id="s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3999df" stop-opacity="0"/><stop offset=".5" stop-color="#3999df" stop-opacity=".14"/><stop offset="1" stop-color="#3999df" stop-opacity="0"/></linearGradient>
<clipPath id="k"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>
</defs>
<style>{BASE_CSS}{css}</style>
<g clip-path="url(#k)"><rect width="{w}" height="{h}" fill="#080d18"/><rect width="{w}" height="{h}" fill="url(#g)"/>{sc}</g>
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="{rx-1}" fill="none" stroke="#24344c"/>
{body}
</svg>
'''


def head(w, left, right, y=55):
    return (f'<g fill="#93a8c9" font-size="15"><text x="48" y="{y}" letter-spacing="4">{left}</text>'
            f'<text x="{w-48}" y="{y}" text-anchor="end">{right}</text></g>')


# ================================= BUILD ======================================
def main():
    today = date.today()
    data = load_data()
    info, repos_all = data["info"], data["repos"]
    login = info.get("login", USER)
    name = (info.get("name") or login).strip()
    bio = (info.get("bio") or "").strip() or FALLBACK_BIO

    repos = [r for r in repos_all if not r.get("fork") and not r.get("archived")]
    is_profile = lambda r: r["name"].lower() == login.lower()
    others = [r for r in repos if not is_profile(r)]
    stars = sum(r.get("stargazers_count", 0) for r in repos)

    # languages (by number of repos, profile repo excluded)
    langs = {}
    for r in others:
        if r.get("language"):
            langs.setdefault(r["language"], []).append(r)
    top_langs = sorted(langs.items(), key=lambda kv: (-len(kv[1]), -max(datetime.fromisoformat(x["pushed_at"].replace("Z", "+00:00")).timestamp() for x in kv[1])))[:3]

    # projects: stars, then recent push; profile repo fills any remaining slot
    others_sorted = sorted(others, key=lambda r: (-r.get("stargazers_count", 0), -datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")).timestamp()))
    projects = (others_sorted + [r for r in repos if is_profile(r)])[:MAX_PROJECTS]

    # ---- calendar
    total = None
    try:
        days, private = fetch_calendar(today.year, today)
        cal_svg, total = calendar_svg(days, private, today.year, today)
        write("contributions.svg", cal_svg)
    except Exception as exc:
        print("calendar skipped:", exc)

    # ---- hero
    parts = name.split()
    n1, n2 = (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (name, "")
    longest = max(len(n1), len(n2), 1)
    nsize = int(min(83, 470 / (0.6 * longest)))
    typing = " / ".join(l for l, _ in top_langs) or "Developer"
    tw = int(len(typing) * 14.2) + 10
    tpl = open(os.path.join(ROOT, "templates", "hero.tpl"), encoding="utf-8").read()
    hero = tpl
    for k, v in {"HEADER": f"{esc(n1.upper())} / LIVING IDENTITY", "LOGIN": esc(login), "NAME1": esc(n1),
                 "NAME2": esc(n2), "NAMESIZE": nsize, "TYPING": esc(typing), "TW": tw, "CX": 50 + tw,
                 "TAGLINE": esc(short(bio, 60)), "S_REPOS": info.get("public_repos", len(repos)), "S_STARS": stars,
                 "S_CONTRIB": total if total is not None else "–", "S_FOLLOWERS": info.get("followers", 0),
                 "FACE": get_face(info)}.items():
        hero = hero.replace("{{" + k + "}}", str(v))
    write("hero.svg", hero)

    # ---- about
    latest = max(others, key=lambda r: r["pushed_at"]) if others else None
    now_txt = f"Last push: {latest['name']} · {rel(latest['pushed_at'])}" if latest else "Building something new"
    rows = [("whoami", f"{name} · @{login}"),
            ("stack", " · ".join(l for l, _ in top_langs) or "—"),
            ("now", now_txt), ("mission", bio)]
    rows = [(c, short(o, 54)) for c, o in rows]
    W, H = 1200, 390
    b = head(W, "ABOUT / WHOAMI", f"@{esc(login)}")
    for i, (cmd, out_) in enumerate(rows):
        y = 118 + i * 66
        b += (f'<g class="fu" style="animation-delay:{round(0.3 + i * 0.5, 2)}s">'
              f'<text x="60" y="{y}" font-size="15" fill="#3999df"><tspan fill="#5d7aa3">$ </tspan>{cmd}</text>'
              f'<text x="60" y="{y+28}" font-size="21" fill="#e8efff">{esc(out_)}</text></g>')
    b += f'<rect class="bl" x="{60 + len(rows[-1][1]) * 12.6 + 6:.0f}" y="{118 + 3 * 66 + 12}" width="11" height="20" fill="#69b8ff"/>'
    cx, cy = 990, 215
    initials = "".join(p[0] for p in parts[:2]).upper() or login[:2].upper()
    b += f'''<circle cx="{cx}" cy="{cy}" r="120" fill="#0c1424" fill-opacity=".85" stroke="#1d304b"/>
<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="28s" repeatCount="indefinite"/><circle cx="{cx}" cy="{cy}" r="104" fill="none" stroke="url(#r)" stroke-width="1.5" stroke-dasharray="170 30 70 30"/><circle cx="{cx}" cy="{cy-104}" r="4.5" fill="#69b8ff"/></g>
<g><animateTransform attributeName="transform" type="rotate" from="360 {cx} {cy}" to="0 {cx} {cy}" dur="45s" repeatCount="indefinite"/><circle cx="{cx}" cy="{cy}" r="86" fill="none" stroke="#213650" stroke-dasharray="2 10"/><circle cx="{cx+86}" cy="{cy}" r="3.5" fill="#8271c7"/></g>
<text x="{cx}" y="{cy+20}" text-anchor="middle" font-size="58" font-weight="bold" fill="url(#nm)">{esc(initials)}</text>
<circle cx="{cx+56}" cy="{cy+58}" r="5" fill="#3ddc97" class="p"/>'''
    write("about.svg", frame(W, H, b))

    # ---- stack
    W, H = 1200, 400
    b = head(W, "TECH STACK", "LANGUAGES FROM MY REPOS")
    n = max(len(top_langs), 1)
    gap, cw, y0, chh = 24, int((1104 - 24 * (n - 1)) / n), 100, 240
    counted = sum(len(v) for _, v in top_langs) or 1
    for i, (lname, rs) in enumerate(top_langs):
        x = 48 + i * (cw + gap)
        col = LANG_COLORS.get(lname, "#6f84a6")
        per = 2 * (cw - 2 + chh - 2)
        bar_w = cw - 56
        used = short(" · ".join(r["name"] for r in rs), int(bar_w / 8.6))
        b += f'''<g class="fu" style="animation-delay:{round(0.3 + i * 0.3, 2)}s">
<rect x="{x}" y="{y0}" width="{cw}" height="{chh}" rx="16" fill="#0c1424" fill-opacity=".9" stroke="#1d304b"/>
<rect x="{x+1}" y="{y0+1}" width="{cw-2}" height="{chh-2}" rx="15" fill="none" stroke="url(#r)" stroke-width="1.5" stroke-dasharray="150 {per-150}"><animate attributeName="stroke-dashoffset" values="0;-{per}" dur="7s" begin="{i}s" repeatCount="indefinite"/></rect>
<circle class="p" cx="{x+32}" cy="{y0+40}" r="7" fill="{col}" style="animation-delay:{i*.5}s"/>
<text x="{x+52}" y="{y0+49}" font-size="28" font-weight="bold" fill="#e8efff">{esc(lname)}</text>
<text x="{x+cw-28}" y="{y0+47}" text-anchor="end" font-size="12" letter-spacing="2" fill="#94a8c7">{len(rs)} REPO{"S" if len(rs) != 1 else ""}</text>
<rect x="{x+28}" y="{y0+68}" width="{bar_w}" height="4" rx="2" fill="#172236"/>
<rect x="{x+28}" y="{y0+68}" width="{bar_w * len(rs) / counted:.0f}" height="4" rx="2" fill="{col}"><animate attributeName="width" from="0" to="{bar_w * len(rs) / counted:.0f}" dur="1.4s" fill="freeze"/></rect>
<text x="{x+28}" y="{y0+102}" font-size="11" letter-spacing="3" fill="#6f84a6">USED IN</text>
<text x="{x+28}" y="{y0+124}" font-size="15" fill="#c6d4ec">{esc(used)}</text>
<line x1="{x+28}" y1="{y0+144}" x2="{x+cw-28}" y2="{y0+144}" stroke="#29364b"/>'''
        for j, line in enumerate(SNIPPETS.get(lname, DEFAULT_SNIPPET)[:3]):
            ind = len(line) - len(line.lstrip())
            b += f'<text x="{x+28+ind*7.8:.0f}" y="{y0+172+j*22}" font-size="13" fill="#7192bd">{esc(line.strip())}</text>'
        b += "</g>"
    focus = f'{info.get("public_repos", len(repos))} public repos  ·  {stars} stars  ·  {info.get("followers", 0)} followers'
    b += f'<g class="fu" style="animation-delay:1.3s"><text x="50" y="372" font-size="12" letter-spacing="3" fill="#6f84a6">LIVE</text><text x="120" y="372" font-size="15" fill="#c6d4ec">{esc(focus)}</text></g>'
    write("stack.svg", frame(W, H, b))

    # ---- projects
    cards_dir = os.path.join(ROOT, "cards")
    os.makedirs(cards_dir, exist_ok=True)
    for f in os.listdir(cards_dir):
        if f.endswith(".svg"):
            os.remove(os.path.join(cards_dir, f))
    W, H = 590, 170
    for i, r in enumerate(projects):
        desc = short(r.get("description") or "No description yet.", 58)
        lang = r.get("language")
        col = LANG_COLORS.get(lang, "#6f84a6")
        per = 2 * (W - 2 + H - 2)
        lang_x = 56 + len(lang or "") * 8.4 + 28
        b = f'''<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="15" fill="none" stroke="url(#r)" stroke-width="1.5" stroke-dasharray="180 {per-180}"><animate attributeName="stroke-dashoffset" values="0;-{per}" dur="6s" begin="{i*1.2}s" repeatCount="indefinite"/></rect>
<path d="M34 34h7l2 2h9v13H34z" fill="none" stroke="#6f84a6" stroke-width="1.5" stroke-linejoin="round"/>
<text x="64" y="52" font-size="22" font-weight="bold" fill="#69b8ff">{esc(short(r["name"], 26))}</text>
<rect x="{W-112}" y="32" width="80" height="26" rx="13" fill="none" stroke="#29364b"/>
<text x="{W-72}" y="49" text-anchor="middle" font-size="11" letter-spacing="2" fill="#94a8c7">PUBLIC</text>
<text x="34" y="102" font-size="15" fill="#91a5c5">{esc(desc)}</text>'''
        if lang:
            b += f'<circle cx="40" cy="138" r="6" fill="{col}"/><text x="56" y="143" font-size="14" fill="#e5edfc">{esc(lang)}</text>'
        b += (f'<text x="{lang_x if lang else 34:.0f}" y="143" font-size="14" fill="#94a8c7">★ {r.get("stargazers_count", 0)}   forks {r.get("forks_count", 0)}</text>'
              f'<text x="{W-34}" y="143" text-anchor="end" font-size="11" letter-spacing="2" fill="#6f84a6">UPDATED {esc(rel(r["pushed_at"]).upper())}</text>')
        write(f"cards/{re.sub(r'[^A-Za-z0-9._-]', '_', r['name'])}.svg", frame(W, H, b, rx=16, scan=False))
    write("header-projects.svg", frame(1200, 90, head(1200, "SELECTED PROJECTS", f"{len(projects)} REPOSITORIES · @{esc(login)}", 52), rx=20))

    # ---- footer
    W, H = 1200, 220
    pts = []
    for x in range(48, W - 47, 8):
        t = (x - 48) / (W - 96)
        amp = 10 + 26 * math.sin(t * math.pi) ** 2
        pts.append(f"{x},{62 + amp * math.sin(x / 22.0) * (0.6 + 0.4 * math.sin(x / 71.0)):.1f}")
    b = f'''<polyline class="wv" points="{" ".join(pts)}" fill="none" stroke="url(#r)" stroke-width="2" stroke-linejoin="round"/>
<text x="{W/2}" y="136" text-anchor="middle" font-size="13" letter-spacing="6" fill="#3999df">THANKS FOR STOPPING BY</text>
<text x="{W/2}" y="172" text-anchor="middle" font-size="26" fill="#e8efff">Let's build something useful.</text>
<text x="{W/2}" y="200" text-anchor="middle" font-size="13" fill="#6f84a6">github.com/{esc(login)}</text>'''
    write("footer.svg", frame(W, H, b, css=".wv{animation:wp 3.5s ease-in-out infinite}@keyframes wp{0%,100%{opacity:.55}50%{opacity:1}}", rx=22))

    # ---- README
    cards = "\n".join(
        f'<a href="{esc(r["html_url"])}"><img src="cards/{re.sub(r"[^A-Za-z0-9._-]", "_", r["name"])}.svg" alt="{esc(r["name"])}" width="49%" /></a>'
        for r in projects)
    write("README.md", f'''<div align="center">

<img src="hero.svg" alt="{esc(name)} - GitHub profile banner" width="100%" />

<img src="about.svg" alt="About {esc(name)}" width="100%" />

<img src="stack.svg" alt="Tech stack" width="100%" />

<img src="header-projects.svg" alt="Selected projects" width="100%" />

{cards}

<img src="contributions.svg" alt="{esc(name)} GitHub contribution calendar" width="100%" />

<img src="footer.svg" alt="Thanks for stopping by" width="100%" />

</div>
''')
    print(f"done: {len(projects)} projects, languages={[l for l, _ in top_langs]}, stars={stars}, contributions={total}")


def write(rel_path, text):
    path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if rel_path.endswith(".svg"):
        import xml.dom.minidom as md
        md.parseString(text.encode("utf-8"))  # never write a broken SVG
    open(path, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
