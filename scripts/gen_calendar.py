#!/usr/bin/env python3
"""Generate an animated contribution calendar SVG that matches your GitHub profile graph
(calendar year, Jan-Dec) and keep the hero.svg stats in sync.

Usage: python scripts/gen_calendar.py <github-username> [calendar.svg] [hero.svg]

If env GH_PAT is set (classic token with `read:user`), the GitHub GraphQL API is used and
PRIVATE contributions are included - the numbers then match what you see when logged in.
Without it, the public profile page is used (public contributions only).
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date

user = sys.argv[1] if len(sys.argv) > 1 else "msrajput12"
out = sys.argv[2] if len(sys.argv) > 2 else "contributions.svg"
hero = sys.argv[3] if len(sys.argv) > 3 else "hero.svg"
PALETTE = "blue"  # "blue" (matches the card theme) or "github" (green like GitHub)

today = date.today()
year = today.year
FROM, TO = f"{year}-01-01", f"{year}-12-31"
token = os.environ.get("GH_PAT", "").strip()


def fetch_graphql():
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
      contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{
      date contributionCount contributionLevel weekday}}}}}}"""
    body = json.dumps({"query": query, "variables": {
        "login": user, "from": f"{FROM}T00:00:00Z", "to": f"{TO}T23:59:59Z"}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "User-Agent": "calendar-generator"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in data:
        raise RuntimeError(data["errors"])
    lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    res = []
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            res.append(dict(date=d["date"], row=d["weekday"], col=wi,
                            level=lv.get(d["contributionLevel"], 0), count=d["contributionCount"]))
    return res


def fetch_html():
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions?from={FROM}&to={TO}",
        headers={"User-Agent": "Mozilla/5.0 (calendar-generator)"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    cells = {}
    for td in re.finditer(r"<td\b[^>]*ContributionCalendar-day[^>]*>", html):
        tag = td.group(0)
        d = re.search(r'data-date="([\d-]+)"', tag)
        i = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
        lv = re.search(r'data-level="(\d)"', tag)
        if d and i and lv:
            cells[f"contribution-day-component-{i.group(1)}-{i.group(2)}"] = dict(
                date=d.group(1), row=int(i.group(1)), col=int(i.group(2)), level=int(lv.group(1)), count=0)
    for tip in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        m = re.match(r"\s*(\d+)\s+contribution", tip.group(2))
        if tip.group(1) in cells and m:
            cells[tip.group(1)]["count"] = int(m.group(1))
    return list(cells.values())


private = False
days = None
if token:
    try:
        days = fetch_graphql()
        private = True
    except Exception as exc:
        print("GraphQL failed, falling back to public page:", exc)
if not days:
    days = fetch_html()
days = sorted(days, key=lambda c: c["date"])
if not days:
    sys.exit("No contribution data found")

past = [c for c in days if c["date"] <= today.isoformat()]
total = sum(c["count"] for c in days)
active = sum(1 for c in past if c["count"] > 0)
best = max(past, key=lambda c: c["count"])
streak = longest = 0
for c in past:
    streak = streak + 1 if c["count"] > 0 else 0
    longest = max(longest, streak)

# --- layout ----------------------------------------------------------------
W, H = 1200, 400
Y0, PITCH, SZ = 150, 16, 13
cols = max(c["col"] for c in days) + 1
X0 = int((W - cols * PITCH) / 2) + 22
PALETTES = {
    "blue": ["#111c2e", "#1d4e89", "#2879bd", "#3999df", "#69b8ff"],
    "github": ["#151b23", "#0e4429", "#006d32", "#26a641", "#39d353"],
}
COLORS = PALETTES[PALETTE]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

rects, month_first = [], {}
for c in days:
    x, y = X0 + c["col"] * PITCH, Y0 + c["row"] * PITCH
    delay = round(c["col"] * 0.03 + c["row"] * 0.01, 2)
    cls = f"c l{c['level']}" + (" hot" if c["level"] >= 3 else "")
    n = c["count"]
    label = f'{n} contribution{"s" if n != 1 else ""} on {c["date"]}'
    rects.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{SZ}" height="{SZ}" rx="3" '
                 f'style="animation-delay:{delay}s"><title>{label}</title></rect>')
    month_first.setdefault(int(c["date"][5:7]), c["col"])
month_lbls = "".join(f'<text x="{X0 + col * PITCH}" y="{Y0 - 12}">{MONTHS[m - 1]}</text>'
                     for m, col in month_first.items())

cur = past[-1]
tx, ty = X0 + cur["col"] * PITCH, Y0 + cur["row"] * PITCH
best_d = date.fromisoformat(best["date"]).strftime("%b %d").upper()
upd = today.strftime("%d %b %Y").upper() + (" · INCLUDES PRIVATE" if private else "")

legend_x = X0 + cols * PITCH - 5 * (SZ + 3) - 70
legend = "".join(
    f'<rect x="{legend_x + 40 + i * (SZ + 3)}" y="{Y0 + 7 * PITCH + 8}" width="{SZ}" height="{SZ}" rx="3" fill="{col}"/>'
    for i, col in enumerate(COLORS))

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{user} contribution calendar {year}">
<defs>
<pattern id="g" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="#172236"/></pattern>
<linearGradient id="s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3999df" stop-opacity="0"/><stop offset=".5" stop-color="#3999df" stop-opacity=".12"/><stop offset="1" stop-color="#3999df" stop-opacity="0"/></linearGradient>
<clipPath id="k"><rect width="{W}" height="{H}" rx="26"/></clipPath>
</defs>
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
.c{{animation:pop .6s ease-out backwards;transform-box:fill-box;transform-origin:center}}
.l0{{fill:{COLORS[0]}}}.l1{{fill:{COLORS[1]}}}.l2{{fill:{COLORS[2]}}}.l3{{fill:{COLORS[3]}}}.l4{{fill:{COLORS[4]}}}
@keyframes pop{{from{{opacity:0;transform:scale(.4)}}to{{opacity:1;transform:scale(1)}}}}
.hot{{animation:pop .6s ease-out backwards,glow 3s ease-in-out 1.8s infinite}}
@keyframes glow{{0%,100%{{opacity:1}}50%{{opacity:.6}}}}
.now{{animation:ring 1.8s ease-in-out infinite}}
@keyframes ring{{0%,100%{{opacity:.2}}50%{{opacity:1}}}}
.fu{{animation:fu .8s ease-out backwards}}
@keyframes fu{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
</style>
<g clip-path="url(#k)">
<rect width="{W}" height="{H}" fill="#080d18"/><rect width="{W}" height="{H}" fill="url(#g)"/>
<rect x="-300" width="300" height="{H}" fill="url(#s)"><animate attributeName="x" values="-300;{W}" dur="8s" repeatCount="indefinite"/></rect>
</g>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="25" fill="none" stroke="#24344c"/>

<g fill="#93a8c9" font-size="15">
<text x="48" y="55" letter-spacing="4">OPEN-SOURCE SIGNAL</text>
<text x="{W - 48}" y="55" text-anchor="end">@{user} / {year}</text>
</g>
<text x="48" y="95" fill="#3999df" font-size="13" letter-spacing="4">{total} CONTRIBUTIONS IN {year}</text>
<text x="{W - 48}" y="95" text-anchor="end" fill="#44566f" font-size="11" letter-spacing="2">UPDATED {upd}</text>

<g fill="#6f84a6" font-size="11" letter-spacing="1">{month_lbls}</g>
<g fill="#6f84a6" font-size="11"><text x="{X0 - 44}" y="{Y0 + 1 * PITCH + 11}">MON</text><text x="{X0 - 44}" y="{Y0 + 3 * PITCH + 11}">WED</text><text x="{X0 - 44}" y="{Y0 + 5 * PITCH + 11}">FRI</text></g>

{chr(10).join(rects)}

<rect class="now" x="{tx - 2}" y="{ty - 2}" width="{SZ + 4}" height="{SZ + 4}" rx="5" fill="none" stroke="#69b8ff" stroke-width="1.5"/>

<g fill="#6f84a6" font-size="11"><text x="{legend_x}" y="{Y0 + 7 * PITCH + 19}">LESS</text><text x="{legend_x + 40 + 5 * (SZ + 3) + 4}" y="{Y0 + 7 * PITCH + 19}">MORE</text></g>
{legend}

<line x1="48" y1="300" x2="{W - 48}" y2="300" stroke="#29364b"/>
<g class="fu" style="animation-delay:1.2s">
<g fill="#94a8c7" font-size="13" letter-spacing="2"><text x="50" y="335">CONTRIBUTIONS</text><text x="330" y="335">ACTIVE DAYS</text><text x="610" y="335">LONGEST STREAK</text><text x="910" y="335">BEST DAY</text></g>
<g fill="#e8efff" font-size="35"><text x="50" y="378">{total}</text><text x="330" y="378">{active}</text><text x="610" y="378">{longest}<tspan font-size="14" fill="#94a8c7"> days</tspan></text><text x="910" y="378">{best["count"]}<tspan font-size="14" fill="#94a8c7"> on {best_d}</tspan></text></g>
</g>
</svg>
'''
open(out, "w", encoding="utf-8").write(svg)
print(f"{out}: {total} contributions in {year} ({'incl. private' if private else 'public only'}), "
      f"{active} active days, longest streak {longest}, best {best['count']} on {best['date']}")


# --- keep hero.svg stats (repos / stars / contributions / followers) in sync ---
def _api(path):
    headers = {"User-Agent": "calendar-generator", "Accept": "application/vnd.github+json"}
    tk = os.environ.get("GITHUB_TOKEN") or token
    if tk:
        headers["Authorization"] = f"Bearer {tk}"
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://api.github.com" + path, headers=headers), timeout=30))


if os.path.exists(hero):
    vals = {"s-contrib": total}
    try:
        info = _api(f"/users/{user}")
        repos = _api(f"/users/{user}/repos?per_page=100&type=owner")
        vals.update({"s-repos": info["public_repos"],
                     "s-stars": sum(r.get("stargazers_count", 0) for r in repos),
                     "s-followers": info["followers"]})
    except Exception as exc:  # never fail the whole run because of stats
        print("repo/follower stats skipped:", exc)
    text = open(hero, encoding="utf-8").read()
    for key, val in vals.items():
        text = re.sub(rf'(<text id="{key}"[^>]*>)[^<]*(</text>)', rf"\g<1>{val}\g<2>", text)
    open(hero, "w", encoding="utf-8").write(text)
    print("hero stats:", vals)