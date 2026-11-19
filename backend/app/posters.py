"""
Procedural poster + backdrop generator.

Every film gets a deterministic, unique, cinematic SVG poster derived from its genres and id,
so the app works fully offline with zero licensing issues. To use real artwork instead,
store a TMDB poster URL in `Movie.poster_url` and return it from `serializers.movie_dict`.
"""
import hashlib
import random
import textwrap
from xml.sax.saxutils import escape

# genre -> (hue A, hue B)  HSL hues
PALETTE = {
    "Action": (8, 28), "Adventure": (28, 45), "Animation": (190, 300), "Biography": (35, 20),
    "Comedy": (42, 14), "Crime": (350, 255), "Drama": (215, 265), "Family": (165, 50),
    "Fantasy": (270, 175), "History": (30, 12), "Horror": (355, 280), "Music": (305, 200),
    "Mystery": (250, 190), "Romance": (338, 12), "Sci-Fi": (195, 260), "Thriller": (205, 350),
    "War": (95, 30), "Western": (28, 8),
}
PRIORITY = ["Horror", "Sci-Fi", "Animation", "Fantasy", "War", "Crime", "Romance", "Action", "Mystery",
            "Thriller", "Music", "Biography", "Western", "Comedy", "Adventure", "Family", "History", "Drama"]


def _rng(movie_id: int, salt: str = "") -> random.Random:
    return random.Random(int(hashlib.md5(f"{movie_id}{salt}".encode()).hexdigest()[:12], 16))


def _primary(genres):
    for g in PRIORITY:
        if g in genres:
            return g
    return "Drama"


def _motif(kind: str, r: random.Random, w: int, h: int, c1: str, c2: str) -> str:
    out = []
    cx, cy = w * r.uniform(0.35, 0.65), h * r.uniform(0.30, 0.42)
    if kind == "Sci-Fi":
        for i in range(7):
            rad = 40 + i * 38
            out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{rad}" fill="none" stroke="{c2}" stroke-opacity="{0.55 - i*0.07:.2f}" stroke-width="{1.4 if i%2 else 0.7}"/>')
        out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="34" fill="url(#orb)"/>')
        for _ in range(60):
            out.append(f'<circle cx="{r.uniform(0,w):.0f}" cy="{r.uniform(0,h*0.75):.0f}" r="{r.uniform(0.5,1.6):.1f}" fill="#fff" fill-opacity="{r.uniform(0.3,0.9):.2f}"/>')
    elif kind == "Action":
        for _ in range(9):
            x = r.uniform(-60, w); wd = r.uniform(10, 60)
            out.append(f'<polygon points="{x:.0f},{h} {x+wd:.0f},{h} {x+wd+260:.0f},0 {x+240:.0f},0" fill="{c2}" fill-opacity="{r.uniform(0.05,0.2):.2f}"/>')
        out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="90" fill="url(#orb)" fill-opacity="0.85"/>')
    elif kind in ("Horror", "Thriller", "Mystery"):
        for i in range(14):
            x = r.uniform(0, w); hh = r.uniform(h*0.2, h*0.7)
            out.append(f'<rect x="{x:.0f}" y="0" width="{r.uniform(2,9):.0f}" height="{hh:.0f}" fill="{c2}" fill-opacity="{r.uniform(0.06,0.22):.2f}"/>')
        out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{70 if kind=="Horror" else 55}" fill="#000" fill-opacity="0.55"/>')
        out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{70 if kind=="Horror" else 55}" fill="none" stroke="{c2}" stroke-width="2" stroke-opacity="0.8"/>')
    elif kind == "Romance":
        for dx, col in ((-38, c1), (38, c2)):
            out.append(f'<circle cx="{cx+dx:.0f}" cy="{cy:.0f}" r="85" fill="{col}" fill-opacity="0.45"/>')
        out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="30" fill="#fff" fill-opacity="0.35"/>')
    elif kind == "Animation":
        for _ in range(18):
            rad = r.uniform(10, 54)
            out.append(f'<circle cx="{r.uniform(0,w):.0f}" cy="{r.uniform(0,h*0.7):.0f}" r="{rad:.0f}" fill="{r.choice([c1,c2,"#fff"])}" fill-opacity="{r.uniform(0.12,0.38):.2f}"/>')
    elif kind in ("Crime", "Biography", "War", "Western"):
        for i in range(16):
            y = i * (h * 0.7 / 16)
            out.append(f'<rect x="0" y="{y:.0f}" width="{w}" height="{r.uniform(2,10):.0f}" fill="{c2}" fill-opacity="{r.uniform(0.04,0.2):.2f}"/>')
        out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="64" fill="{c2}" fill-opacity="0.75"/>')
    elif kind in ("Fantasy", "Adventure", "Family", "History"):
        pts = []
        for layer, op in enumerate((0.25, 0.4, 0.65)):
            base = h * (0.5 + layer * 0.12)
            pts_l = [f"0,{h}"]
            x = 0
            while x <= w + 60:
                pts_l.append(f"{x:.0f},{base - r.uniform(20, 120 - layer*22):.0f}")
                x += r.uniform(40, 90)
            pts_l.append(f"{w},{h}")
            out.append(f'<polygon points="{" ".join(pts_l)}" fill="#000" fill-opacity="{op}"/>')
        out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="52" fill="url(#orb)"/>')
    else:  # Drama / Comedy / Music: sun over horizon
        out.append(f'<circle cx="{cx:.0f}" cy="{h*0.46:.0f}" r="100" fill="url(#orb)" fill-opacity="0.9"/>')
        out.append(f'<rect x="0" y="{h*0.46:.0f}" width="{w}" height="{h}" fill="#000" fill-opacity="0.45"/>')
        for i in range(6):
            out.append(f'<rect x="{cx-110+i*8:.0f}" y="{h*0.46+i*13:.0f}" width="{220-i*16}" height="3" fill="{c2}" fill-opacity="{0.5-i*0.07:.2f}"/>')
    return "".join(out)


def _title_lines(title: str, width: int):
    title = title.split(":")[0] if len(title) > 26 and ":" in title else title
    lines = textwrap.wrap(title.upper(), width=width)[:4]
    return lines or [title.upper()]


def poster_svg(movie: dict) -> str:
    w, h = 400, 600
    genres = movie["genres"]
    kind = _primary(genres)
    ha, hb = PALETTE.get(kind, (215, 265))
    r = _rng(movie["id"])
    ha += r.randint(-10, 10); hb += r.randint(-10, 10)
    c1, c2 = f"hsl({ha},75%,52%)", f"hsl({hb},80%,62%)"
    d1, d2 = f"hsl({ha},60%,10%)", f"hsl({hb},65%,17%)"
    lines = _title_lines(movie["title"], 13 if len(movie["title"]) < 40 else 15)
    size = 46 if max(len(l) for l in lines) <= 9 else 38 if max(len(l) for l in lines) <= 12 else 32
    ty = 400 - (len(lines) - 1) * size * 0.5
    tspans = "".join(
        f'<tspan x="200" dy="{0 if i == 0 else size * 1.08:.0f}">{escape(l)}</tspan>' for i, l in enumerate(lines)
    )
    director = escape(movie["director"].split("|")[0].upper())
    cast = escape("  /  ".join(movie["cast"][:2]).upper())
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0.6" y2="1"><stop offset="0" stop-color="{d2}"/><stop offset="1" stop-color="{d1}"/></linearGradient>
<radialGradient id="orb"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".35" stop-color="{c2}"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient>
<radialGradient id="glow" cx=".5" cy=".3" r=".8"><stop offset="0" stop-color="{c1}" stop-opacity=".55"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient>
<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".35" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".92"/></linearGradient>
<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="{movie['id']}"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .09 0"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#bg)"/>
<rect width="{w}" height="{h}" fill="url(#glow)"/>
{_motif(kind, r, w, h, c1, c2)}
<rect width="{w}" height="{h}" fill="url(#fade)"/>
<rect width="{w}" height="{h}" filter="url(#grain)"/>
<rect x="14" y="14" width="{w-28}" height="{h-28}" fill="none" stroke="#fff" stroke-opacity=".14"/>
<text x="200" y="{ty:.0f}" text-anchor="middle" font-family="Georgia,'Times New Roman',serif" font-weight="700" font-size="{size}" letter-spacing="3" fill="#fff" style="paint-order:stroke" stroke="#000" stroke-opacity=".25" stroke-width="3">{tspans}</text>
<line x1="150" x2="250" y1="{ty + len(lines)*size*1.08 + 4:.0f}" y2="{ty + len(lines)*size*1.08 + 4:.0f}" stroke="{c2}" stroke-width="2"/>
<text x="200" y="{ty + len(lines)*size*1.08 + 30:.0f}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="11" letter-spacing="4" fill="#fff" fill-opacity=".85">{movie['year']}  ·  {escape(kind.upper())}</text>
<text x="200" y="548" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="9" letter-spacing="1.8" fill="#fff" fill-opacity=".6">{cast}</text>
<text x="200" y="568" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="9.5" letter-spacing="3" fill="#fff" fill-opacity=".9">A FILM BY {director}</text>
</svg>'''


def backdrop_svg(movie: dict) -> str:
    w, h = 1600, 800
    kind = _primary(movie["genres"])
    ha, hb = PALETTE.get(kind, (215, 265))
    r = _rng(movie["id"], "bd")
    ha += r.randint(-10, 10); hb += r.randint(-10, 10)
    c1, c2 = f"hsl({ha},75%,52%)", f"hsl({hb},80%,62%)"
    d1, d2 = f"hsl({ha},55%,8%)", f"hsl({hb},60%,14%)"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{d2}"/><stop offset="1" stop-color="{d1}"/></linearGradient>
<radialGradient id="orb"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".35" stop-color="{c2}"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient>
<radialGradient id="glow" cx=".72" cy=".35" r=".7"><stop offset="0" stop-color="{c1}" stop-opacity=".6"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#bg)"/><rect width="{w}" height="{h}" fill="url(#glow)"/>
<g transform="translate(560 0) scale(1.3)">{_motif(kind, r, 1000, 560, c1, c2)}</g>
</svg>'''
