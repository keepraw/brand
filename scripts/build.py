#!/usr/bin/env python3
"""Regenerate every Keepraw logo asset from the geometry defined below.

Requires: fonttools, brotli, Google Chrome (headless) and ImageMagick `convert`.
The wordmark is set in Inter (SIL OFL 1.1); pass the variable font with --font.

    python3 scripts/build.py --font path/to/Inter-roman.var.woff2
"""
import argparse, os, re, shutil, subprocess
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

INK, PAPER, RAW = "#20231f", "#f5f4ef", "#c8553d"
# The mark lives on a 128 x 128 grid: a flame whose body is a circle (r 38 at 64,80)
# and an ember (r 13.5 at 64,82).
FLAME = "M68 10C72 34 102 48 102 80A38 38 0 0 1 26 80C26 62 34 50 44 38C45 48 49 54 56 57C53 40 58 24 68 10Z"
EMBER = (64, 82, 13.5)
WORD, WEIGHT = "Keepraw", 650
CHROME = os.environ.get("CHROME", "google-chrome")

ap = argparse.ArgumentParser()
ap.add_argument("--font", required=True)
args = ap.parse_args()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.abspath(args.font)
os.chdir(ROOT)

font = instantiateVariableFont(TTFont(FONT), {"wght": WEIGHT})
gs, cmap, upm = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm


def word(text, size, x0, base, track=-0.01):
    s, x, d = size / upm, x0, []
    for ch in text:
        g = cmap[ord(ch)]
        pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, base)))
        d.append(pen.getCommands())
        x += gs[g].width * s + track * size
    return " ".join(d), x - track * size


def mark(fg, acc, t=""):
    cx, cy, r = EMBER
    g = f'<path fill="{fg}" d="{FLAME}"/><circle cx="{cx}" cy="{cy}" r="{r}" fill="{acc}"/>'
    return f'<g transform="{t}">{g}</g>' if t else g


def cutout(fg):
    # One colour only: the ember is cut out of the flame rather than filled.
    cx, cy, r = EMBER
    hole = f"M{n(cx - r)} {n(cy)}a{n(r)} {n(r)} 0 1 0 {n(2 * r)} 0a{n(r)} {n(r)} 0 1 0 {n(-2 * r)} 0Z"
    return f'<path fill="{fg}" fill-rule="evenodd" d="{FLAME}{hole}"/>'


def n(v):
    return f"{v:g}"


def svg(vb, body, bg=None, rx=0, label="Keepraw"):
    x, y, w, h = vb
    r = f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{rx}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{n(x)} {n(y)} {n(w)} {n(h)}" width="{n(w)}" height="{n(h)}" '
            f'role="img" aria-label="{label}"><title>{label}</title>{r}{body}</svg>\n')


TILE = "translate(7.68 7.68) scale(.88)"
AVATAR = "translate(16 16) scale(.75)"
LOCK = "translate(-22 6.4) scale(.9)"
o = {}
o["mark"] = svg((0, 0, 128, 128), mark(INK, RAW))
o["mark-on-dark"] = svg((0, 0, 128, 128), mark(PAPER, RAW))
o["mark-mono-ink"] = svg((0, 0, 128, 128), mark(INK, PAPER))
o["mark-mono-white"] = svg((0, 0, 128, 128), mark("#ffffff", INK))
o["mark-cutout-ink"] = svg((0, 0, 128, 128), cutout(INK))
o["mark-cutout-white"] = svg((0, 0, 128, 128), cutout("#ffffff"))
o["icon-dark"] = svg((0, 0, 128, 128), mark(PAPER, RAW, TILE), INK, 28)
o["icon-light"] = svg((0, 0, 128, 128), mark(INK, RAW, TILE), PAPER, 28)
o["avatar-dark"] = svg((0, 0, 128, 128), mark(PAPER, RAW, AVATAR), INK)
o["avatar-light"] = svg((0, 0, 128, 128), mark(INK, RAW, AVATAR), PAPER)
wd, wx = word(WORD, 76, 86, 89)
LW = round(wx)
for tag, fg, bg in (("light", INK, None), ("dark", PAPER, None), ("light-bg", INK, PAPER), ("dark-bg", PAPER, INK)):
    pad = 28 if bg else 0
    o[f"lockup-{tag}"] = svg((-pad, -pad / 2, LW + 2 * pad, 128 + pad), mark(fg, RAW, LOCK) + f'<path fill="{fg}" d="{wd}"/>', bg)
sd, sx = word(WORD, 44, 0, 0)
SW = round(sx)
for tag, fg in (("light", INK), ("dark", PAPER)):
    o[f"stacked-{tag}"] = svg((0, 0, SW, 178), mark(fg, RAW, f"translate({n(SW / 2 - 64)} 0)") + f'<path fill="{fg}" transform="translate(0 166)" d="{sd}"/>')

for d in ("logo/svg", "logo/png", "favicon", "docs"):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
for k, v in o.items():
    open(f"logo/svg/keepraw-{k}.svg", "w").write(v)
open("favicon/favicon.svg", "w").write(o["icon-dark"])


def shot(html, out, w, h, transparent=False):
    open("_r.html", "w").write(html)
    cmd = [CHROME, "--headless", "--no-sandbox", "--hide-scrollbars", f"--screenshot={ROOT}/{out}", f"--window-size={w},{h}"]
    if transparent:
        cmd.append("--default-background-color=00000000")
    subprocess.run(cmd + [f"file://{ROOT}/_r.html"], capture_output=True, check=True)
    os.remove("_r.html")


def png(name, size):
    w, h = map(float, re.search(r'viewBox="([^"]+)"', o[name]).group(1).split()[2:])
    shot(f'<body style="margin:0;background:transparent"><img src="logo/svg/keepraw-{name}.svg" style="display:block;height:1024px">',
         "_r.png", round(1024 * w / h), 1024, True)
    subprocess.run(["convert", "_r.png", "-filter", "Lanczos", "-resize", f"x{size}", f"logo/png/keepraw-{name}-{size}.png"], check=True)
    os.remove("_r.png")


for name, size in (("icon-dark", 16), ("icon-dark", 32), ("icon-dark", 48), ("icon-dark", 180), ("icon-dark", 192), ("icon-dark", 512),
                   ("icon-light", 512), ("avatar-dark", 1024), ("avatar-light", 1024), ("mark", 1024), ("mark-on-dark", 1024),
                   ("lockup-light", 512), ("lockup-dark", 512), ("lockup-light-bg", 512), ("lockup-dark-bg", 512),
                   ("stacked-light", 1024), ("stacked-dark", 1024)):
    png(name, size)
P = "logo/png/keepraw-icon-dark-"
subprocess.run(["convert", f"{P}16.png", f"{P}32.png", f"{P}48.png", "favicon/favicon.ico"], check=True)
shutil.copy(f"{P}180.png", "favicon/apple-touch-icon.png")

# ---- documentation figures (docs/) -------------------------------------------------
FONT = 'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"'
MONO = 'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"'


def doc(name, w, h, body, bg=PAPER):
    open(f"docs/{name}.svg", "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{name}">'
        f'<rect width="{w}" height="{h}" rx="16" fill="{bg}"/>{body}</svg>\n')


# construction
grid = "".join(f'<path d="M{i} 0V128M0 {i}H128" stroke="{INK}" stroke-opacity=".10" stroke-width=".25"/>' for i in range(0, 129, 8))
cx, cy, r = EMBER
cons = (f'<g transform="translate(48 40) scale(3.5)">{grid}{mark(INK, RAW)}'
        f'<g fill="none" stroke="{RAW}" stroke-width=".6" stroke-dasharray="2 2"><circle cx="64" cy="80" r="38"/><path d="M64 0V128M0 80H128"/></g>'
        f'<circle cx="64" cy="80" r="1.2" fill="{PAPER}"/></g>'
        f'<g {FONT} font-size="15" fill="{INK}">'
        f'<text x="540" y="96" font-weight="600">Flame</text><text x="540" y="118" fill-opacity=".7">Body is a circle, r 38 at (64, 80).</text>'
        f'<text x="540" y="138" fill-opacity=".7">Tip at (68, 10), leaning 4 units right.</text>'
        f'<text x="540" y="196" font-weight="600">Ember</text><text x="540" y="218" fill-opacity=".7">Circle, r 13.5 at (64, 82).</text>'
        f'<text x="540" y="238" fill-opacity=".7">Sits 2 units below the body centre.</text>'
        f'<text x="540" y="296" font-weight="600">Grid</text><text x="540" y="318" fill-opacity=".7">128 x 128, lines every 8 units.</text>'
        f'<text x="540" y="338" fill-opacity=".7">Mark spans x 26-102, y 10-118.</text></g>')
doc("construction", 860, 528, cons)

# clear space: x = ember diameter in the lockup
X = 2 * r * 0.9
ex, ey = 64 * .9 - 22, 82 * .9 + 6.4
clear = (f'<g transform="translate({n(60 + X)} {n(40 + X)})">'
         f'<rect x="{n(-X)}" y="{n(-X)}" width="{n(LW + 2 * X)}" height="{n(128 + 2 * X)}" fill="none" stroke="{RAW}" stroke-width="1" stroke-dasharray="4 4"/>'
         f'<rect width="{LW}" height="128" fill="none" stroke="{INK}" stroke-opacity=".25" stroke-width="1"/>'
         f'{mark(INK, RAW, LOCK)}<path fill="{INK}" d="{wd}"/>'
         + "".join(f'<circle cx="{n(a)}" cy="{n(b)}" r="{n(X / 2)}" fill="{RAW}" fill-opacity=".35"/>'
                   for a, b in ((-X / 2, 64), (LW + X / 2, 64), (LW / 2, -X / 2), (LW / 2, 128 + X / 2)))
         + f'</g><text x="{n(60 + X)}" y="{n(40 + 2 * X + 128 + 34)}" {FONT} font-size="15" fill="{INK}" fill-opacity=".7">'
           f'Keep a margin of x on every side, where x is the diameter of the ember.</text>')
doc("clearspace", round(LW + 2 * X + 120), round(128 + 2 * X + 130), clear, "#ffffff")

# palette
sw = ""
for i, (nm, hx, fg, rgb, role) in enumerate((("Ink", INK, PAPER, "32, 35, 31", "Flame, text, dark surfaces"),
                                              ("Paper", PAPER, INK, "245, 244, 239", "Backgrounds, flame on dark"),
                                              ("Raw sienna", RAW, "#ffffff", "200, 85, 61", "The ember only"))):
    x = 24 + i * 276
    stroke = f' stroke="{INK}" stroke-opacity=".15"' if hx == PAPER else ""
    sw += (f'<rect x="{x}" y="24" width="260" height="172" rx="12" fill="{hx}"{stroke}/>'
           f'<text x="{x + 20}" y="60" {FONT} font-size="18" font-weight="600" fill="{fg}">{nm}</text>'
           f'<text x="{x + 20}" y="88" {MONO} font-size="15" fill="{fg}">{hx}</text>'
           f'<text x="{x + 20}" y="110" {MONO} font-size="13" fill="{fg}" fill-opacity=".8">rgb({rgb})</text>'
           f'<text x="{x + 20}" y="174" {FONT} font-size="13" fill="{fg}" fill-opacity=".8">{role}</text>')
doc("palette", 860, 220, sw, "#ffffff")

# misuse
cases = (("Do not recolour", f'<path fill="#2f6fde" d="{FLAME}"/><circle cx="{cx}" cy="{cy}" r="{r}" fill="#ffd23f"/>', PAPER),
         ("Do not stretch", f'<g transform="translate(-25.6 0) scale(1.4 1)">{mark(INK, RAW)}</g>', PAPER),
         ("Do not rotate or flip", f'<g transform="rotate(24 64 64)">{mark(INK, RAW)}</g>', PAPER),
         ("Do not remove the ember", f'<path fill="{INK}" d="{FLAME}"/>', PAPER),
         ("Do not use low contrast", mark("#4a4d49", RAW), INK))
bad = ""
for i, (cap, body, bg) in enumerate(cases):
    x = 20 + i * 166
    bad += (f'<rect x="{x}" y="20" width="156" height="156" rx="12" fill="{bg}"/>'
            f'<g transform="translate({x + 30} 50) scale(.75)">{body}</g>'
            f'<g transform="translate({x + 132} 44)"><circle r="12" fill="#b3261e"/><path d="M-5 -5L5 5M5 -5L-5 5" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/></g>'
            f'<text x="{x + 78}" y="202" text-anchor="middle" {FONT} font-size="13" fill="{INK}">{cap}</text>')
doc("misuse", 860, 224, bad, "#ffffff")

# overview sheet
C = lambda k, h, bg: f'<div class="c" style="background:{bg}"><img src="logo/svg/keepraw-{k}.svg" style="height:{h}px"></div>'
sizes = "".join(f'<img src="logo/png/keepraw-icon-dark-{s}.png" style="height:{h}px">' for s, h in ((512, 128), (192, 64), (48, 48), (32, 32), (16, 16)))
shot(f'''<meta charset=utf-8><style>body{{margin:0;padding:40px 40px 20px;background:#e9e7e0;width:1320px}}.r{{display:flex;gap:20px;margin-bottom:20px}}
.c{{flex:1;display:flex;align-items:center;justify-content:center;padding:36px;border-radius:14px;gap:18px}}</style>
<div class="r">{C("mark", 260, PAPER)}{C("mark-on-dark", 260, INK)}</div>
<div class="r">{C("lockup-light", 110, PAPER)}{C("lockup-dark", 110, INK)}</div>
<div class="r">{C("stacked-light", 170, "#fff")}{C("stacked-dark", 170, INK)}<div class="c" style="background:#fff;align-items:flex-end">{sizes}
<img src="logo/svg/keepraw-icon-light.svg" style="height:128px"><img src="logo/svg/keepraw-avatar-dark.svg" style="height:128px;border-radius:50%"></div></div>''',
     "docs/overview.png", 1400, 900)
print("built", len(o), "svg variants")
