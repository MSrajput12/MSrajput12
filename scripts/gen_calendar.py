#!/usr/bin/env python3
"""Generate an animated GitHub contribution calendar SVG (no token needed).

Usage: python scripts/gen_calendar.py <github-username> [output.svg]
"""
import re
import sys
import urllib.request
from datetime import date

user = sys.argv[1] if len(sys.argv) > 1 else "msrajput12"
out = sys.argv[2] if len(sys.argv) > 2 else "contributions.svg"

req = urllib.request.Request(
    f"https://github.com/users/{user}/contributions",
    headers={"User-Agent": "Mozilla/5.0 (calendar-generator)"},
)
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")

# --- parse cells -----------------------------------------------------------
cells = {}
for td in re.finditer(r"<td\b[^>]*ContributionCalendar-day[^>]*>", html):
    tag = td.group(0)
    d = re.search(r'data-date="([\d-]+)"', tag)
    i = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
    lv = re.search(r'data-level="(\d)"', tag)
    if d and i and lv:
        cells[f"contribution-day-component-{i.group(1)}-{i.group(2)}"] = dict(
            date=d.group(1), row=int(i.group(1)), col=int(i.group(2)),
            level=int(lv.group(1)), count=0)

for tip in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
    cid, text = tip.group(1), tip.group(2)
    m = re.match(r"\s*(\d+)\s+contribution", text)
    if cid in cells and m:
        cells[cid]["count"] = int(m.group(1))

days = sorted(cells.values(), key=lambda c: c["date"])
if not days:
    sys.exit("No contribution data found")

total = sum(c["count"] for c in days)
active = sum(1 for c in days if c["count"] > 0)
best = max(days, key=lambda c: c["count"])
streak = longest = 0
for c in days:
    streak = streak + 1 if c["count"] > 0 else 0
    longest = max(longest, streak)

# --- layout ----------------------------------------------------------------
W, H = 1200, 400
X0, Y0, PITCH, SZ = 92, 150, 16, 13
cols = max(c["col"] for c in days) + 1
COLORS = ["#111c2e", "#1d4e89", "#2879bd", "#3999df", "#69b8ff"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

rects, month_lbls, last_month = [], [], None
for c in days:
    x = X0 + c["col"] * PITCH
    y = Y0 + c["row"] * PITCH
    delay = round(c["col"] * 0.03 + c["row"] * 0.01, 2)
    cls = f"c l{c['level']}" + (" hot" if c["level"] >= 3 else "")
    rects.append(
        f'<rect class="{cls}" x="{x}" y="{y}" width="{SZ}" height="{SZ}" rx="3" '
        f'style="animation-delay:{delay}s"><title>{c["count"]} on {c["date"]}</title></rect>'
    )
    month = int(c["date"][5:7])
    if c["row"] == 0 and month != last_month:
        month_lbls.append(f'<text x="{x}" y="{Y0 - 12}">{MONTHS[month - 1]}</text>')
        last_month = month

today = days[-1]
tx, ty = X0 + today["col"] * PITCH, Y0 + today["row"] * PITCH
best_d = date.fromisoformat(best["date"]).strftime("%b %d").upper()
upd = date.today().strftime("%d %b %Y").upper()

legend_x = X0 + cols * PITCH - 5 * (SZ + 3) - 70
legend = "".join(
    f'<rect x="{legend_x + 40 + i * (SZ + 3)}" y="{Y0 + 7 * PITCH + 8}" width="{SZ}" height="{SZ}" rx="3" fill="{col}"/>'
    for i, col in enumerate(COLORS)
)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{user} contribution calendar">
<defs>
<pattern id="g" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="#172236"/></pattern>
<linearGradient id="s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3999df" stop-opacity="0"/><stop offset=".5" stop-color="#3999df" stop-opacity=".22"/><stop offset="1" stop-color="#3999df" stop-opacity="0"/></linearGradient>
<clipPath id="k"><rect width="{W}" height="{H}" rx="26"/></clipPath>
</defs>
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
.c{{animation:pop .6s ease-out backwards}}
.l0{{fill:{COLORS[0]}}}.l1{{fill:{COLORS[1]}}}.l2{{fill:{COLORS[2]}}}.l3{{fill:{COLORS[3]}}}.l4{{fill:{COLORS[4]}}}
@keyframes pop{{from{{opacity:0;transform:scale(.4)}}to{{opacity:1;transform:scale(1)}}}}
.c{{transform-box:fill-box;transform-origin:center}}
.hot{{animation:pop .6s ease-out backwards,glow 3s ease-in-out 1.8s infinite}}
@keyframes glow{{0%,100%{{opacity:1}}50%{{opacity:.55}}}}
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
<text x="{W - 48}" y="55" text-anchor="end">@{user} / LAST 12 MONTHS</text>
</g>
<text x="48" y="95" fill="#3999df" font-size="13" letter-spacing="4">CONTRIBUTION CALENDAR</text>

<g fill="#6f84a6" font-size="11" letter-spacing="1">{"".join(month_lbls)}</g>
<g fill="#6f84a6" font-size="11"><text x="48" y="{Y0 + 1 * PITCH + 11}">MON</text><text x="48" y="{Y0 + 3 * PITCH + 11}">WED</text><text x="48" y="{Y0 + 5 * PITCH + 11}">FRI</text></g>

{chr(10).join(rects)}

<rect class="now" x="{tx - 2}" y="{ty - 2}" width="{SZ + 4}" height="{SZ + 4}" rx="5" fill="none" stroke="#69b8ff" stroke-width="1.5"/>

<g fill="#6f84a6" font-size="11"><text x="{legend_x}" y="{Y0 + 7 * PITCH + 19}">LESS</text><text x="{legend_x + 40 + 5 * (SZ + 3) + 4}" y="{Y0 + 7 * PITCH + 19}">MORE</text></g>
{legend}

<line x1="48" y1="300" x2="{W - 48}" y2="300" stroke="#29364b"/>
<g class="fu" style="animation-delay:1.2s">
<g fill="#94a8c7" font-size="13" letter-spacing="2"><text x="50" y="335">CONTRIBUTIONS</text><text x="330" y="335">ACTIVE DAYS</text><text x="610" y="335">LONGEST STREAK</text><text x="910" y="335">BEST DAY</text></g>
<g fill="#e8efff" font-size="35"><text x="50" y="378">{total}</text><text x="330" y="378">{active}</text><text x="610" y="378">{longest}<tspan font-size="14" fill="#94a8c7"> days</tspan></text><text x="910" y="378">{best["count"]}<tspan font-size="14" fill="#94a8c7"> on {best_d}</tspan></text></g>
</g>
<text x="{W - 48}" y="95" text-anchor="end" fill="#44566f" font-size="11" letter-spacing="2">UPDATED {upd}</text>
</svg>
'''
open(out, "w", encoding="utf-8").write(svg)
print(f"{out}: {total} contributions, {active} active days, longest streak {longest}, best {best['count']} on {best['date']}")