#!/usr/bin/env python3
"""Draw the profile README artwork (assets/*.svg) as whiteboard sketches.

Every image is written twice, once per GitHub colour scheme, and the README
picks one with <picture>. The contribution calendar comes from the GitHub
GraphQL API.

    GH_TOKEN=$(gh auth token) python3 scripts/build.py
"""

import json
import math
import os
import urllib.request
import zlib
from datetime import date
from pathlib import Path

from sketch import Pen, Sketch, smooth, text_width

LOGIN = "krax1337"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

# Excalidraw's pens and fills. levels shade the calendar from a quiet day to a busy one.
THEMES = {
    "light": {
        "ink": "#1e1e1e", "soft": "#868e96", "grid": "#ced4da",
        "red": "#e03131", "blue": "#1971c2", "green": "#2f9e44",
        "sky": "#a5d8ff", "sun": "#ffec99", "mint": "#b2f2bb", "lilac": "#d0bfff", "ash": "#ced4da",
        "note": "#fff3bf", "levels": ("#8ce99a", "#51cf66", "#37b24d", "#2b8a3e"),
    },
    "dark": {
        "ink": "#e3e3e3", "soft": "#8b949e", "grid": "#3d444d",
        "red": "#ff8787", "blue": "#74c0fc", "green": "#69db7c",
        "sky": "#1c5d99", "sun": "#8f6f00", "mint": "#2b7a3d", "lilac": "#5a3fb5", "ash": "#495057",
        "note": "#4a3d07", "levels": ("#1f6b33", "#2f9e44", "#51cf66", "#8ce99a"),
    },
}

CHECKLIST = [
    (True, "k8s on bare metal + cloud"),
    (True, "GitOps, IaC, signed images"),
    (True, "small tools: Go, Rust, TS"),
    (False, "sleep"),
]

# Left to right; they all stand on HOST.
STACK = [
    ("write", "sky", ["Go", "Rust", "TypeScript", "Python"]),
    ("ship", "sun", ["Terraform", "Ansible", "Argo CD", "GitHub Actions"]),
    ("run", "mint", ["Kubernetes", "Cilium", "Helm"]),
    ("observe", "lilac", ["Prometheus", "Grafana"]),
]
HOST = ["AWS", "Cloudflare", "Talos"]
# Scribbled above one column; it needs a short one to leave room.
STACK_NOTE = ("observe", ["tells me before", "the users do"])


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
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def underline(s, x, y, width, weight=2.4):
    s.curve([(x, y), (x + width * 0.5, y - 4), (x + width + 4, y + 1)], s.c["red"], weight)


# --- hero ---------------------------------------------------------------------

ROW = 290  # centre line of the pipeline


def sticky_note(s, x, y):
    w, h = 276, 154
    s.raw(f'<g transform="rotate(2.5 {x + w / 2} {y + h / 2})">')
    s.rect(x, y, w, h, solid=s.c["note"], radius=3, width=1.5)
    for i, (done, line) in enumerate(CHECKLIST):
        base = y + 40 + i * 31
        s.rect(x + 18, base - 14, 15, 15, radius=2, width=1.4)
        if done:
            s.line(x + 21, base - 8, x + 25.5, base - 2, s.c["green"], 2.4)
            s.line(x + 25.5, base - 2, x + 39, base - 21, s.c["green"], 2.4)
        s.text(line, x + 46, base, 17)
    s.raw("</g>")


def figure(s, x, ground):
    """Stick figure with headphones, standing on ground."""
    head = ground - 78
    s.ellipse(x, head, 24, 24)
    s.curve([(x - 13, head + 2), (x - 10, head - 12), (x + 10, head - 12), (x + 13, head + 2)], width=2.6)
    for side in (-13.5, 13.5):
        s.line(x + side, head - 2, x + side, head + 7, width=5)
    s.line(x, head + 12, x, ground - 28)
    s.line(x, ground - 56, x - 17, ground - 36)
    s.line(x, ground - 56, x + 22, ground - 46)
    s.line(x, ground - 28, x - 13, ground)
    s.line(x, ground - 28, x + 13, ground)


def stage(s, x, label, fill):
    """Shaded box on the pipeline. Returns its right edge."""
    w = text_width(label, 22) + 44
    s.rect(x, ROW - 27, w, 54, fill=s.c[fill])
    s.text(label, x + w / 2, ROW + 8, 22, anchor="middle")
    return x + w


def hop(s, x1, x2, label):
    s.arrow([(x1 + 6, ROW), (x2 - 6, ROW)])
    s.text(label, (x1 + x2) / 2, ROW - 11, 15, s.c["soft"], anchor="middle")


def hero(c):
    s = Sketch(880, 440, c, seed=11, tempo=0.45)

    width = s.text("Asanali Bulatov", 8, 82, 58, wobble=1, pace=0.09)
    underline(s, 10, 101, width)
    s.text("Senior DevOps / Site Reliability Engineer", 10, 138, 23)
    s.text(f"{LOGIN} · Kazakhstan · UTC+5", 10, 167, 17, c["soft"])

    sticky_note(s, 584, 26)

    figure(s, 56, ROW + 42)
    s.text("me", 56, ROW + 66, 17, anchor="middle")
    hop(s, 84, 156, "git push")
    edge = stage(s, 156, "git", "sky")
    hop(s, edge, edge + 72, "build")
    edge = stage(s, edge + 72, "CI", "sun")
    hop(s, edge, edge + 126, "signed image")
    edge = stage(s, edge + 126, "registry", "lilac")
    cluster = edge + 62
    hop(s, edge, cluster, "sync")
    s.rect(cluster, ROW - 58, 160, 116, dash="8 9", radius=14)
    s.text("cluster", cluster + 14, ROW - 34, 17)
    for i in range(3):
        s.rect(cluster + 15 + i * 46, ROW - 14, 38, 50, fill=c["mint"], gap=6)

    back = [(cluster + 12, ROW + 62), (cluster - 60, ROW + 108), (400, ROW + 126), (160, ROW + 108), (90, ROW + 48)]
    s.arrow(back)
    s.text("metrics, logs, alerts (ideally none)", 400, ROW + 114, 16, c["soft"], anchor="middle")

    s.text("unsigned? rejected.", edge - 136, ROW + 62, 16, c["red"])
    s.arrow([(edge + 14, ROW + 54), (edge + 32, ROW + 40), (edge + 33, ROW + 12)], c["red"], 1.6, head=8)
    s.text("boring on purpose", 866, ROW + 94, 16, c["blue"], anchor="end")
    s.arrow([(cluster + 104, ROW + 80), (cluster + 102, ROW + 64)], c["blue"], 1.6, head=8)

    # A commit doing the rounds once the drawing is finished.
    route = f"M86 {ROW}L{cluster} {ROW}L{cluster + 50} {ROW + 20}L" + smooth(back)[1:] + f"L86 {ROW}"
    begin = f"{s.clock + 0.8:.1f}s"
    s.raw(
        f'<path class="live" d="{Pen(5).ellipse(0, 0, 11, 11)[0]}" fill="{c["red"]}" stroke="{c["ink"]}" '
        f'stroke-width="1.2" opacity="0"><set attributeName="opacity" to="1" begin="{begin}"/>'
        f'<animateMotion dur="12s" begin="{begin}" repeatCount="indefinite" path="{route}"/></path>'
    )
    return s.svg(
        "Asanali Bulatov, Senior DevOps / Site Reliability Engineer. Whiteboard sketch: me, git push, git, "
        "build, CI, signed image, registry, sync, cluster; metrics, logs and alerts come back to me."
    )


# --- stack --------------------------------------------------------------------

def stack(c):
    s = Sketch(880, 292, c, seed=23)
    column, gap, floor = 190, 34, 206
    for i, (name, fill, tools) in enumerate(STACK):
        x = 8 + i * (column + gap)
        top = floor - 72 - 28 * len(tools)
        s.rect(x, top, column, floor - top, fill=c[fill])
        width = s.text(name, x + 20, top + 40, 27)
        s.line(x + 20, top + 49, x + 23 + width, top + 48, width=1.5)
        for row, tool in enumerate(tools):
            s.text(tool, x + 20, top + 82 + row * 28, 19.5)
        if i:
            s.arrow([(x - gap + 5, floor - 60), (x - 5, floor - 60)], head=8)
        if name == STACK_NOTE[0]:
            for row, line in enumerate(STACK_NOTE[1]):
                s.text(line, x + 56, top - 48 + row * 20, 16, c["blue"])
            s.arrow([(x + 48, top - 40), (x + 31, top - 28), (x + 29, top - 6)], c["blue"], 1.6, head=8)
    s.rect(8, floor + 16, 862, 58, fill=c["ash"])
    s.text("host:  " + "  ·  ".join(HOST), 440, floor + 53, 23, anchor="middle")
    label = "The stack: " + "; ".join(f'{name}: {", ".join(tools)}' for name, _, tools in STACK)
    return s.svg(f'{label}; all of it on {", ".join(HOST)}.')


# --- year ---------------------------------------------------------------------

def shade(pen, x, y, size, level):
    """One calendar day: a boxed square, hatched closer the busier the day. Returns (outline, hatching)."""
    corners = [(x + dx + pen.jitter(0.5), y + dy + pen.jitter(0.5)) for dx, dy in ((0, 0), (size, 0), (size, size), (0, size))]
    outline = "M" + "L".join(f"{px:.1f} {py:.1f}" for px, py in corners) + "Z"
    if not level:
        return outline, ""
    inner = [(x + 1, y + 1), (x + size - 1, y + 1), (x + size - 1, y + size - 1), (x + 1, y + size - 1)]
    return outline, pen.hachure(inner, (5.0, 3.6, 2.7, 2.0)[level - 1], ticks=True)[0]


def year(c, calendar):
    weeks = calendar["weeks"]
    days = [(i, day) for i, week in enumerate(weeks) for day in week["contributionDays"]]
    counts = [day["contributionCount"] for _, day in days]
    # Quartiles of the active days, so one huge day cannot flatten the rest.
    active = sorted(n for n in counts if n)
    cuts = [active[len(active) * q // 4] for q in (1, 2, 3)] if active else []
    run = longest = end = 0
    for i, n in enumerate(counts):
        run = run + 1 if n else 0
        if run > longest:
            longest, end = run, i
    best_week, best = max(days, key=lambda item: item[1]["contributionCount"])

    s = Sketch(880, 280, c, seed=37)
    pitch, cell, gx, gy = 14.6, 11, 64, 122
    bottom = gy + 6 * pitch + cell

    total = f'{calendar["totalContributions"]:,}'
    width = s.text(total, 8, 62, 50, wobble=1)
    s.text("contributions in the last year", 8 + width + 18, 62, 21)
    s.text(f"{len(active)} of {len(counts)} days active", 858, 62, 18, c["soft"], anchor="end")

    grid, hatching, month, labels = "", [""] * 4, None, []
    for i, day in days:
        level = bool(day["contributionCount"]) + sum(day["contributionCount"] > cut for cut in cuts)
        pen = Pen(zlib.crc32(day["date"].encode()))
        outline, lines = shade(pen, gx + i * pitch, gy + day["weekday"] * pitch, cell, level)
        grid += outline
        if level:
            hatching[level - 1] += lines
    s.raw(f'<path d="{grid}" stroke="{c["grid"]}" stroke-width=".9"/>')
    for level, lines in enumerate(hatching):
        s.raw(f'<path d="{lines}" stroke="{c["levels"][level]}" stroke-width="{1 + level * 0.15:.2f}"/>')

    for i, week in enumerate(weeks):
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != month and i < len(weeks) - 2:
            if month is not None or first.day <= 7:
                x = gx + i * pitch
                labels.append((x, x + s.text(MONTHS[first.month - 1], x, bottom + 18, 14, c["soft"])))
            month = first.month
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        s.text(name, gx - 9, gy + row * pitch + 9.5, 13, c["soft"], anchor="end")

    if longest > 1:
        x1 = gx + days[end - longest + 1][0] * pitch - 1
        x2 = gx + days[end][0] * pitch + cell + 1
        y = gy - 9
        for a, b in (((x1, y + 6), (x1, y)), ((x1, y), (x2, y)), ((x2, y), (x2, y + 6))):
            s.line(*a, *b, c["blue"], 1.6)
        note = f"{longest} days in a row"
        half = text_width(note, 16) / 2
        s.text(note, min(max((x1 + x2) / 2, half + 8), 872 - half), y - 8, 16, c["blue"], anchor="middle")

    # Legend on the left, the note about the best day right of it.
    x = gx + s.text("less", gx, bottom + 44, 13, c["soft"]) + 7
    for level in range(1, 5):
        outline, lines = shade(Pen(level), x, bottom + 34, cell, level)
        s.raw(f'<path d="{outline}" stroke="{c["grid"]}" stroke-width=".9"/>')
        s.raw(f'<path d="{lines}" stroke="{c["levels"][level - 1]}" stroke-width="{1 + (level - 1) * 0.15:.2f}"/>')
        x += pitch
    s.text("more", x + 3, bottom + 44, 13, c["soft"])

    when = date.fromisoformat(best["date"])
    note = f'{best["contributionCount"]:,} on {MONTHS[when.month - 1]} {when.day}'
    bx, by = gx + best_week * pitch + cell / 2, gy + best["weekday"] * pitch + cell / 2
    s.ellipse(bx, by, 23, 23, c["red"], 1.6)
    wide = text_width(note, 16)
    left = bx - 30 - wide if bx > 440 else max(bx + 30, 224)
    s.text(note, left, bottom + 46, 16, c["red"])
    tail = left + wide + 6 if bx > 440 else left - 6
    # The arrow climbs to the circled day straight up through a gap between the month names.
    gate = next(
        (x for step in range(13) for x in (bx - step * 6, bx + step * 6) if not any(a - 9 < x < b + 9 for a, b in labels)),
        bx,
    )
    route = [(tail, bottom + 41), (gate, bottom + 30), (gate, bottom + 5), ((gate + 3 * bx) / 4, by + 15)]
    s.arrow(route, c["red"], 1.6, head=8)

    return s.svg(
        f"{total} contributions in the last year, {len(active)} of {len(counts)} days active, "
        f"longest streak {longest} days, best day {note}."
    )


# --- headings -------------------------------------------------------------------

def title(c, text):
    width = text_width(text, 30)
    s = Sketch(math.ceil(width) + 14, 48, c, seed=zlib.crc32(text.encode()))
    s.text(text, 4, 32, 30, wobble=0.6)
    underline(s, 5, 42, width, 2)
    return s.svg(text)


def main():
    calendar = fetch()
    ASSETS.mkdir(exist_ok=True)
    for name, c in THEMES.items():
        files = {
            "hero": hero(c),
            "stack": stack(c),
            "year": year(c, calendar),
            "title-upstream": title(c, "Upstream"),
            "title-stack": title(c, "The stack"),
            "title-year": title(c, "Last 12 months"),
        }
        for stem, svg in files.items():
            (ASSETS / f"{stem}-{name}.svg").write_text(svg)
    print(f"wrote {len(list(ASSETS.glob('*.svg')))} files to {ASSETS}")


if __name__ == "__main__":
    main()
