#!/usr/bin/env python3
"""Generate the profile README artwork (assets/*.svg).

Every image is written twice, once per GitHub colour scheme, and the README
picks one with <picture>. The contribution calendar comes from the GitHub
GraphQL API.

    GH_TOKEN=$(gh auth token) python3 scripts/build.py
"""

import json
import os
import urllib.request
from datetime import date
from html import escape
from math import cos, pi, sin
from pathlib import Path

LOGIN = "krax1337"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

THEMES = {
    "dark": {
        "surface": "#0f141b",
        "border": "#232b36",
        "fg": "#e6edf3",
        "muted": "#8b949e",
        "dot": "#2b3440",
        "empty": 0.07,
        "glow": 0.22,
        "acc": ("#34d399", "#22d3ee", "#818cf8"),
    },
    "light": {
        "surface": "#f8fafc",
        "border": "#d8dee4",
        "fg": "#1f2328",
        "muted": "#59636e",
        "dot": "#c9d1d9",
        "empty": 0.07,
        "glow": 0.16,
        "acc": ("#059669", "#0891b2", "#4f46e5"),
    },
}

# Bottom layer first. marks are line paths on the 128-unit top face of a layer.
STACK = [
    ("host", ["AWS", "Cloudflare", "Talos"],
     [[(k, 8), (k, 120)] for k in (32, 64, 96)] + [[(8, k), (120, k)] for k in (32, 64, 96)]),
    ("run", ["Kubernetes", "Cilium", "Helm"],
     [[(x, y), (x + 14, y), (x + 14, y + 14), (x, y + 14), (x, y)] for x in (25, 57, 89) for y in (25, 57, 89)]),
    ("ship", ["Terraform", "Ansible", "Argo CD", "GitHub Actions"],
     [p for y in (36, 64, 92) for p in ([(22, y), (104, y)], [(92, y - 10), (104, y), (92, y + 10)])]),
    ("observe", ["Prometheus", "Grafana"],
     [[(64 - r, 64 - r), (64 + r, 64 - r), (64 + r, 64 + r), (64 - r, 64 + r), (64 - r, 64 - r)] for r in (12, 30, 48)]),
    ("write", ["Go", "Rust", "TypeScript", "Python"],
     [[(x, y), (x + n, y)] for y, x, n in ((26, 18, 58), (45, 32, 74), (64, 32, 42), (83, 32, 60), (102, 18, 34))]),
]

ROLES = [
    "Kubernetes on bare metal and in the cloud",
    "GitOps, IaC and signed supply chains",
    "Small sharp tools in Go, Rust and TypeScript",
]


def fetch():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("set GH_TOKEN (e.g. GH_TOKEN=$(gh auth token))")
    query = f"""{{
      user(login: "{LOGIN}") {{
        contributionsCollection {{ contributionCalendar {{
          totalContributions
          weeks {{ contributionDays {{ date contributionCount weekday }} }}
        }} }}
      }}
    }}"""
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": f"{LOGIN}-profile"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if body.get("errors"):
        raise SystemExit(f"GitHub API: {body['errors']}")
    return body["data"]


def mix(stops, t):
    """Colour at t in [0, 1] along a list of hex stops."""
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    a, b = (tuple(int(s[k:k + 2], 16) for k in (1, 3, 5)) for s in stops[i:i + 2])
    return "#" + "".join(f"{round(x + (y - x) * (t - i)):02x}" for x, y in zip(a, b))


def gradient(gid, acc, x1, x2):
    stops = "".join(
        f'<stop offset="{i / (len(acc) - 1):g}" stop-color="{c}"/>' for i, c in enumerate(acc)
    )
    return (
        f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
        f'x1="{x1}" y1="0" x2="{x2}" y2="0">{stops}</linearGradient>'
    )


def frame(w, h, t, label, defs, body, radius=14):
    """Rounded surface with a hairline border; body is clipped to it."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
        f'<defs><clipPath id="clip"><rect width="{w}" height="{h}" rx="{radius}"/></clipPath>{defs}</defs>'
        f'<g clip-path="url(#clip)"><rect width="{w}" height="{h}" fill="{t["surface"]}"/>{body}</g>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{radius - .5}" fill="none" '
        f'stroke="{t["border"]}"/></svg>\n'
    )


# --- hero -------------------------------------------------------------------

def hero(t):
    w, h = 880, 300
    a1, a2, a3 = t["acc"]
    cx, cy, ring_r = 690, 150, 88

    hub = (cx, cy)
    ring = [
        (round(cx + ring_r * cos(pi * (a - 90) / 180), 1), round(cy + ring_r * sin(pi * (a - 90) / 180), 1))
        for a in range(0, 360, 60)
    ]
    outer = {"registry": (838, 62), "edge": (846, 178), "metrics": (806, 266), "alerts": (566, 262), "git": (548, 52)}
    links = [(1, "registry"), (1, "edge"), (2, "edge"), (2, "metrics"), (3, "metrics"), (4, "alerts"), (5, "git"), (0, "git")]

    def line(p, q, opacity):
        return (
            f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="url(#acc)" '
            f'stroke-width="1.2" stroke-opacity="{opacity}"/>'
        )

    edges = "".join(line(hub, n, 0.5) for n in ring)
    edges += "".join(line(ring[i], ring[(i + 1) % 6], 0.34) for i in range(6))
    edges += "".join(line(ring[i], outer[o], 0.22) for i, o in links)

    routes = [
        ([outer["git"], ring[5], hub], 3.6, 0.0),
        ([hub, ring[1], outer["registry"]], 3.2, 0.9),
        ([outer["edge"], ring[2], hub], 3.4, 1.7),
        ([hub, ring[3], outer["metrics"]], 3.8, 0.4),
        ([hub, ring[4], outer["alerts"]], 4.2, 2.3),
        ([ring[0], ring[1], ring[2], ring[3]], 5.0, 1.2),
        ([ring[3], ring[4], ring[5], ring[0]], 5.0, 3.1),
        ([outer["git"], ring[0], hub], 4.0, 2.6),
    ]
    packets = ""
    for i, (points, dur, begin) in enumerate(routes):
        path = "M" + " L".join(f"{x},{y}" for x, y in points)
        packets += (
            f'<circle r="2.8" fill="{mix(t["acc"], i / (len(routes) - 1))}" opacity="0">'
            f'<animateMotion dur="{dur}s" begin="{begin}s" repeatCount="indefinite" path="{path}"/>'
            f'<animate attributeName="opacity" dur="{dur}s" begin="{begin}s" repeatCount="indefinite" '
            f'values="0;1;1;0" keyTimes="0;.12;.88;1"/></circle>'
        )

    nodes = "".join(
        f'<circle cx="{x}" cy="{y}" r="6.5" fill="{t["surface"]}" stroke="url(#acc)" stroke-width="1.5"/>'
        f'<circle cx="{x}" cy="{y}" r="2.2" fill="url(#acc)"/>'
        for x, y in ring
    )
    for name, (x, y) in outer.items():
        left = x < cx
        nodes += (
            f'<circle cx="{x}" cy="{y}" r="4" fill="{t["surface"]}" stroke="{t["muted"]}" stroke-width="1.2"/>'
            f'<text x="{x + (9 if left else -9)}" y="{y + 3.5}" font-family="{MONO}" font-size="10" '
            f'fill="{t["muted"]}" text-anchor="{"start" if left else "end"}">{name}</text>'
        )
    hexagon = " ".join(
        f"{cx + 17 * cos(pi * (a - 90) / 180):.1f},{cy + 17 * sin(pi * (a - 90) / 180):.1f}" for a in range(0, 360, 60)
    )
    pulses = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="17" fill="none" stroke="{a2}" stroke-width="1.2" opacity="0">'
        f'<animate attributeName="r" values="17;46" dur="3.2s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values=".55;0" dur="3.2s" begin="{b}s" repeatCount="indefinite"/></circle>'
        for b in (0, 1.6)
    )
    nodes += (
        f'{pulses}<polygon points="{hexagon}" fill="{t["surface"]}" stroke="url(#acc)" stroke-width="1.8" '
        f'stroke-linejoin="round"/><circle cx="{cx}" cy="{cy}" r="5" fill="url(#acc)"/>'
    )

    # Negative delays put every line at its own phase of one shared 12 s cycle; the first starts visible.
    roles = "".join(
        f'<text class="role{"" if i else " first"}" style="animation-delay:{4 * i - 12 if i else 0}s" x="48" y="238" '
        f'font-family="{MONO}" font-size="13.5" fill="{t["muted"]}"><tspan fill="{a2}">&#8250;</tspan> '
        f"{escape(r)}</text>"
        for i, r in enumerate(ROLES)
    )

    defs = (
        gradient("acc", t["acc"], 520, 860)
        + gradient("name", t["acc"], 48, 430)
        + f'<radialGradient id="g1"><stop offset="0" stop-color="{a1}" stop-opacity="{t["glow"]}"/>'
        f'<stop offset="1" stop-color="{a1}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="g2"><stop offset="0" stop-color="{a3}" stop-opacity="{t["glow"]}"/>'
        f'<stop offset="1" stop-color="{a3}" stop-opacity="0"/></radialGradient>'
        f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1.1" fill="{t["dot"]}"/></pattern>'
        '<radialGradient id="fade" gradientUnits="userSpaceOnUse" cx="690" cy="150" r="420">'
        '<stop offset=".25" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        f'<mask id="vignette"><rect width="{w}" height="{h}" fill="url(#fade)"/></mask>'
        "<style>"
        ".role{opacity:0;animation:role 12s infinite}.first{opacity:1}"
        "@keyframes role{0%,28%{opacity:1;transform:none}32%{opacity:0;transform:translateY(-7px)}"
        "33%,96%{opacity:0;transform:translateY(7px)}100%{opacity:1;transform:none}}"
        ".beat{animation:beat 2.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}"
        "@keyframes beat{0%,100%{opacity:.35;transform:scale(1)}50%{opacity:0;transform:scale(2.6)}}"
        "@media (prefers-reduced-motion:reduce){.role,.beat{animation:none}"
        ".motion{display:none}}"
        "</style>"
    )
    body = (
        f'<circle cx="640" cy="60" r="260" fill="url(#g1)"><animateTransform attributeName="transform" '
        f'type="translate" values="0 0;60 40;-30 70;0 0" dur="26s" repeatCount="indefinite"/></circle>'
        f'<circle cx="820" cy="280" r="240" fill="url(#g2)"><animateTransform attributeName="transform" '
        f'type="translate" values="0 0;-70 -40;20 -80;0 0" dur="31s" repeatCount="indefinite"/></circle>'
        f'<rect width="{w}" height="{h}" fill="url(#dots)" mask="url(#vignette)"/>'
        f'{edges}<g class="motion">{packets}</g>{nodes}'
        f'<circle class="beat" cx="54" cy="66" r="4" fill="{a1}"/><circle cx="54" cy="66" r="4" fill="{a1}"/>'
        f'<text x="68" y="70.5" font-family="{MONO}" font-size="12.5" fill="{t["muted"]}">'
        f"{LOGIN} · Kazakhstan · UTC+5</text>"
        f'<text x="46" y="140" font-family="{SANS}" font-size="50" font-weight="800" letter-spacing="-1.5" '
        f'fill="url(#name)">Asanali Bulatov</text>'
        f'<text x="48" y="178" font-family="{SANS}" font-size="19" font-weight="500" fill="{t["fg"]}">'
        "Senior DevOps / Site Reliability Engineer</text>"
        f'<rect x="48" y="200" width="44" height="3" rx="1.5" fill="url(#name)"/>'
        f"{roles}"
    )
    return frame(w, h, t, "Asanali Bulatov, Senior DevOps / Site Reliability Engineer", defs, body, radius=18)


# --- stack --------------------------------------------------------------------

def stack(t):
    """The stack as an exploded isometric drawing: one slab per layer, labelled on the right."""
    w, h = 880, 348
    side, depth, gap = 140, 12, 54
    kx, ky = 0.866, 0.21
    ox, oy = 196, 30 + gap * (len(STACK) - 1)
    half = side * kx
    text_x = ox + half + 96

    def at(x, y, z, drop=0):
        return f"{ox + (x - y) * kx:.1f},{oy + (x + y) * ky - z + drop:.1f}"

    rows = [oy + side * ky - gap * i for i in range(len(STACK))]
    out = "".join(
        f'<line x1="{x:.1f}" y1="{rows[0]:.1f}" x2="{x:.1f}" y2="{rows[-1]:.1f}" stroke="{t["muted"]}" '
        'stroke-opacity=".4" stroke-dasharray="2 4"/>'
        for x in (ox - half, ox + half)
    )
    labels = ""
    for i, (name, tools, marks) in enumerate(STACK):
        z, color, y = gap * i, mix(t["acc"], 1 - i / (len(STACK) - 1)), rows[i]
        a, b, c, d = at(0, 0, z), at(side, 0, z), at(side, side, z), at(0, side, z)
        b2, c2, d2 = at(side, 0, z, depth), at(side, side, z, depth), at(0, side, z, depth)
        top = f"{a} {b} {c} {d}"
        lines = "".join(
            f'<polyline points="{" ".join(at(x * side / 128, py * side / 128, z) for x, py in path)}" fill="none" stroke="{color}" '
            'stroke-opacity=".6" stroke-width="1.1" stroke-linejoin="round" stroke-linecap="round"/>'
            for path in marks
        )
        out += (
            f'<polygon points="{a} {b} {b2} {c2} {d2} {d}" fill="{t["surface"]}"/>'
            f'<polygon points="{d} {c} {c2} {d2}" fill="{color}" fill-opacity=".34"/>'
            f'<polygon points="{c} {b} {b2} {c2}" fill="{color}" fill-opacity=".2"/>'
            f'<polygon points="{top}" fill="{color}" fill-opacity=".1"/>'
            f'<polygon class="pulse" style="animation-delay:{i * 0.45:.2f}s" points="{top}" fill="{color}" opacity="0"/>'
            f'{lines}<path d="M{a} L{b} L{c} L{d} Z M{d} L{d2} L{c2} L{b2} L{b} M{c} L{c2}" fill="none" '
            f'stroke="{color}" stroke-width="1.2" stroke-linejoin="round"/>'
        )
        labels += (
            f'<circle cx="{ox + half:.1f}" cy="{y:.1f}" r="2.6" fill="{color}"/>'
            f'<line x1="{ox + half + 8:.1f}" y1="{y:.1f}" x2="{text_x - 12:.1f}" y2="{y:.1f}" stroke="{t["muted"]}" '
            'stroke-opacity=".55"/>'
            f'<text x="{text_x:.1f}" y="{y + 4.5:.1f}" font-family="{MONO}" font-size="11" fill="{color}">{i + 1:02d}</text>'
            f'<text x="{text_x + 28:.1f}" y="{y + 5:.1f}" font-family="{SANS}" font-size="15" font-weight="700" '
            f'fill="{t["fg"]}">{name}</text>'
            f'<text x="{text_x + 28:.1f}" y="{y + 23:.1f}" font-family="{MONO}" font-size="12.5" fill="{t["muted"]}">'
            f'{escape(" · ".join(tools))}</text>'
        )
    defs = (
        "<style>.pulse{animation:pulse 6s ease-out infinite}"
        "@keyframes pulse{0%,30%,100%{opacity:0}7%{opacity:.42}}"
        "@media (prefers-reduced-motion:reduce){.pulse{animation:none}}</style>"
    )
    label = "The stack, bottom up: " + "; ".join(f'{name}: {", ".join(tools)}' for name, tools, _ in STACK)
    return frame(w, h, t, label, defs, out + labels)


# --- activity -----------------------------------------------------------------

OPACITY = (0, 0.3, 0.52, 0.76, 1)
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def activity(calendar, t):
    w, h = 880, 236
    weeks = calendar["weeks"]
    cell, pitch = 11, 14.6
    gx, gy = (w - len(weeks) * pitch + (pitch - cell)) / 2 + 12, 96

    days = [d for week in weeks for d in week["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    # Quartiles of the active days, so one huge day cannot flatten the rest.
    active = sorted(c for c in counts if c)
    cuts = [active[len(active) * q // 4] for q in (1, 2, 3)] if active else []
    longest = streak = 0
    for c in counts:
        streak = streak + 1 if c else 0
        longest = max(longest, streak)
    best = max(days, key=lambda d: d["contributionCount"])
    best_day = date.fromisoformat(best["date"])
    stats = [
        (f"{sum(1 for c in counts if c)}/{len(counts)}", "active days"),
        (f"{longest} days", "longest streak"),
        (f'{best["contributionCount"]:,}', f"best day, {MONTHS[best_day.month - 1]} {best_day.day}"),
    ]

    columns, labels, month = "", "", None
    for i, week in enumerate(weeks):
        x = gx + i * pitch
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != month and i < len(weeks) - 2:
            if month is not None or first.day <= 7:
                labels += (
                    f'<text x="{x:.1f}" y="{gy - 9}" font-family="{MONO}" font-size="10" fill="{t["muted"]}">'
                    f"{MONTHS[first.month - 1]}</text>"
                )
            month = first.month
        color, cells = mix(t["acc"], i / (len(weeks) - 1)), ""
        for d in week["contributionDays"]:
            level = bool(d["contributionCount"]) + sum(d["contributionCount"] > c for c in cuts)
            fill = f'fill="{color}" fill-opacity="{OPACITY[level]}"' if level else f'fill="{t["fg"]}" fill-opacity="{t["empty"]}"'
            cells += f'<rect x="{x:.1f}" y="{gy + d["weekday"] * pitch:.1f}" width="{cell}" height="{cell}" rx="2.6" {fill}/>'
        columns += f'<g class="col" style="animation-delay:{i * 0.05:.2f}s">{cells}</g>'

    weekdays = "".join(
        f'<text x="{gx - 10:.1f}" y="{gy + row * pitch + 9:.1f}" font-family="{MONO}" font-size="9.5" '
        f'fill="{t["muted"]}" text-anchor="end">{name}</text>'
        for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )
    right = gx + len(weeks) * pitch - (pitch - cell)
    stat_text = ""
    for i, (value, label) in enumerate(reversed(stats)):
        x = right - i * 150
        stat_text += (
            f'<text x="{x:.1f}" y="40" font-family="{SANS}" font-size="17" font-weight="700" fill="{t["fg"]}" '
            f'text-anchor="end">{value}</text>'
            f'<text x="{x:.1f}" y="58" font-family="{MONO}" font-size="10.5" fill="{t["muted"]}" '
            f'text-anchor="end">{label}</text>'
        )
    ly = gy + 7 * pitch + 8
    legend = (
        f'<text x="{right - 106:.1f}" y="{ly + 9:.1f}" font-family="{MONO}" font-size="9.5" '
        f'fill="{t["muted"]}" text-anchor="end">less</text>'
        f'<text x="{right:.1f}" y="{ly + 9:.1f}" font-family="{MONO}" font-size="9.5" '
        f'fill="{t["muted"]}" text-anchor="end">more</text>'
        f'<rect x="{right - 99:.1f}" y="{ly:.1f}" width="{cell}" height="{cell}" rx="2.6" fill="{t["fg"]}" '
        f'fill-opacity="{t["empty"]}"/>'
    ) + "".join(
        f'<rect x="{right - 99 + level * 14:.1f}" y="{ly:.1f}" width="{cell}" height="{cell}" rx="2.6" '
        f'fill="{t["acc"][1]}" fill-opacity="{OPACITY[level]}"/>'
        for level in range(1, 5)
    )
    total = f'{calendar["totalContributions"]:,}'
    defs = (
        gradient("acc", t["acc"], gx - 30, gx + 150)
        + "<style>.col{animation:sweep 9s linear infinite}"
        "@keyframes sweep{0%,12%,100%{opacity:1}5%{opacity:.4}}"
        "@media (prefers-reduced-motion:reduce){.col{animation:none}}</style>"
    )
    body = (
        f'<text x="{gx - 31:.1f}" y="48" font-family="{SANS}" font-size="34" font-weight="800" letter-spacing="-1" '
        f'fill="url(#acc)">{total}</text>'
        f'<text x="{gx - 30:.1f}" y="68" font-family="{MONO}" font-size="11" fill="{t["muted"]}">'
        "contributions in the last year</text>"
        f"{stat_text}{labels}{weekdays}{columns}{legend}"
    )
    return frame(w, h, t, f"{total} contributions in the last year", defs, body)


def main():
    data = fetch()
    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
    ASSETS.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        files = {
            "hero": hero(t),
            "stack": stack(t),
            "activity": activity(calendar, t),
        }
        for stem, svg in files.items():
            (ASSETS / f"{stem}-{name}.svg").write_text(svg)
    print(f"wrote {len(list(ASSETS.glob('*.svg')))} files to {ASSETS}")


if __name__ == "__main__":
    main()
