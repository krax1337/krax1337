"""Hand-drawn SVG: wobbly strokes and hachure fills after rough.js, lettering from glyph outlines.

Everything is seeded, so the same drawing code always yields the same file.
"""

import json
import math
import random
from html import escape
from pathlib import Path

_FONT = json.loads(Path(__file__).with_name("glyphs.json").read_text())
UPM = _FONT["unitsPerEm"]
GLYPHS = _FONT["glyphs"]

HACHURE_ANGLE = -41


def text_width(text, size):
    return sum(GLYPHS[ch][0] for ch in text) * size / UPM


def _n(value):
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def _join(*points):
    return " ".join(f"{_n(x)} {_n(y)}" for x, y in points)


def _spline(points):
    """Catmull-Rom through points[1:-1]; the first and last only shape the ends."""
    d = "M" + _join(points[1])
    for i in range(1, len(points) - 2):
        p0, p1, p2, p3 = points[i - 1 : i + 3]
        d += "C" + _join(
            (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6),
            (p2[0] + (p1[0] - p3[0]) / 6, p2[1] + (p1[1] - p3[1]) / 6),
            p2,
        )
    return d


def smooth(points):
    """The exact curve a rough stroke through these points wobbles around."""
    return _spline([points[0], *points, points[-1]])


def rounded(x, y, w, h, r, steps=4):
    """Outline of a rounded rectangle as a polygon, clockwise from the top-left corner."""
    if not r:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    points = []
    for cx, cy, start in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for i in range(steps + 1):
            a = math.radians(start + 90 * i / steps)
            points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return points


class Pen:
    """Strokes drawn twice, the two passes missing each other a little, as rough.js does."""

    def __init__(self, seed, roughness=1.0):
        self.rng = random.Random(seed)
        self.roughness = roughness

    def jitter(self, amount, gain=1.0):
        return self.roughness * gain * amount * (2 * self.rng.random() - 1)

    def _pass(self, x1, y1, x2, y2, overlay, pinned):
        """One slightly bowed stroke as (start, control, control, end)."""
        length = math.hypot(x2 - x1, y2 - y1)
        gain = 1.0 if length < 200 else 0.4 if length > 500 else 1.233334 - 0.0016668 * length
        offset = min(2.0, length / 10)
        spread = offset / 2 if overlay else offset
        diverge = 0.2 + self.rng.random() * 0.2
        bow_x = self.jitter(2.0 * (y2 - y1) / 200, gain)
        bow_y = self.jitter(2.0 * (x1 - x2) / 200, gain)

        def j():
            return self.jitter(spread, gain)

        return (
            (x1, y1) if pinned else (x1 + j(), y1 + j()),
            (bow_x + x1 + (x2 - x1) * diverge + j(), bow_y + y1 + (y2 - y1) * diverge + j()),
            (bow_x + x1 + 2 * (x2 - x1) * diverge + j(), bow_y + y1 + 2 * (y2 - y1) * diverge + j()),
            (x2, y2) if pinned else (x2 + j(), y2 + j()),
        )

    def line(self, x1, y1, x2, y2, pinned=True, double=True):
        d = ""
        for overlay in (False, True)[: 1 + double]:
            start, *rest = self._pass(x1, y1, x2, y2, overlay, pinned)
            d += "M" + _join(start) + "C" + _join(*rest)
        return d, math.hypot(x2 - x1, y2 - y1) + 4

    def tick(self, x1, y1, x2, y2, wobble=0.9):
        """A stroke too short to bow: a straight line between two nudged ends."""
        start = (x1 + self.jitter(wobble), y1 + self.jitter(wobble))
        end = (x2 + self.jitter(wobble), y2 + self.jitter(wobble))
        return f"M{_join(start)}L{_join(end)}"

    def curve(self, points, double=True):
        def one(offset):
            ends = [points[0], *points, points[-1]]
            return _spline([(x + self.jitter(offset), y + self.jitter(offset)) for x, y in ends])

        d = one(1.2) + (one(1.83) if double else "")
        return d, sum(math.dist(a, b) for a, b in zip(points, points[1:])) * 1.1 + 4

    def _turn(self, start, control, end, amount):
        c1 = (start[0] + (control[0] - start[0]) * 2 / 3, start[1] + (control[1] - start[1]) * 2 / 3)
        c2 = (end[0] + (control[0] - end[0]) * 2 / 3, end[1] + (control[1] - end[1]) * 2 / 3)
        return [(x + self.jitter(amount), y + self.jitter(amount)) for x, y in (c1, c2)] + [end]

    @staticmethod
    def _sides(x, y, w, h, r):
        """Per side: where it starts, where it ends, and the corner that follows (control, end)."""
        return [
            ((x + r, y), (x + w - r, y), (x + w, y), (x + w, y + r)),
            ((x + w, y + r), (x + w, y + h - r), (x + w, y + h), (x + w - r, y + h)),
            ((x + w - r, y + h), (x + r, y + h), (x, y + h), (x, y + h - r)),
            ((x, y + h - r), (x, y + r), (x, y), (x + r, y)),
        ]

    def box(self, x, y, w, h, r):
        """Four double strokes, one per side, each ending in the corner that follows it."""
        strokes = []
        for a, b, control, c in self._sides(x, y, w, h, r):
            d, length = self.line(*a, *b)
            if r:
                for amount in (2.0, 2.3):
                    d += "M" + _join(b) + "C" + _join(*self._turn(b, control, c, amount * min(1.0, r / 16)))
            strokes.append((d, length + r * 1.6))
        return strokes

    def loop(self, x, y, w, h, r):
        """The same box as one unbroken single stroke, for dashed outlines."""
        d = "M" + _join((x + r, y))
        for a, b, control, c in self._sides(x, y, w, h, r):
            d += "C" + _join(*self._pass(*a, *b, True, True)[1:])
            if r:
                d += "C" + _join(*self._turn(b, control, c, min(1.0, r / 16)))
        return d + "Z"

    def ellipse(self, cx, cy, w, h):
        rx, ry = w / 2, h / 2
        steps = math.ceil(max(9, 9 / math.sqrt(200) * math.sqrt(2 * math.pi * math.sqrt((rx**2 + ry**2) / 2))))
        step = 2 * math.pi / steps
        rx += self.jitter(rx * 0.05)
        ry += self.jitter(ry * 0.05)
        wobble = min(1.0, max(w, h) / 40)

        def ring(offset, overlap):
            def at(angle, shrink=1.0):
                return (
                    self.jitter(offset) + cx + shrink * rx * math.cos(angle),
                    self.jitter(offset) + cy + shrink * ry * math.sin(angle),
                )

            start = self.jitter(0.5) - math.pi / 2
            points = [at(start - step, 0.9)]
            angle = start
            while angle < 2 * math.pi + start - 0.01:
                points.append(at(angle))
                angle += step
            points += [at(start + 2 * math.pi + overlap * 0.5), at(start + overlap, 0.98), at(start + overlap * 0.5, 0.9)]
            return _spline(points)

        overlap = step * self.roughness * (0.1 + self.rng.random() * 0.6)
        return ring(wobble, overlap) + ring(1.5 * wobble, 0), math.pi * (rx + ry) * 1.2

    def hachure(self, polygon, gap, angle=HACHURE_ANGLE, double=True, ticks=False):
        """Parallel strokes clipped to the polygon. ticks draws them as plain short lines."""
        a = math.radians(angle)
        cos, sin = math.cos(a), math.sin(a)
        turned = [(x * cos + y * sin, y * cos - x * sin) for x, y in polygon]
        edges = list(zip(turned, turned[1:] + turned[:1]))
        ys = [y for _, y in turned]
        d, longest, y = "", 0.0, min(ys) + gap / 2
        while y < max(ys):
            hits = sorted(
                x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                for (x1, y1), (x2, y2) in edges
                if (y1 <= y < y2) or (y2 <= y < y1)
            )
            for left, right in zip(hits[::2], hits[1::2]):
                ends = (left * cos - y * sin, left * sin + y * cos, right * cos - y * sin, right * sin + y * cos)
                if ticks:
                    d += self.tick(*ends, wobble=0.5)
                else:
                    stroke, length = self.line(*ends, pinned=False, double=double)
                    d, longest = d + stroke, max(longest, length)
            y += gap
        return d, longest


class Sketch:
    """One drawing. With a tempo every stroke and letter appears in the order it was drawn.

    tempo scales the time each one takes: 1 is unhurried, smaller is brisker, 0 is a still image.
    """

    def __init__(self, width, height, palette, seed, tempo=0.0):
        self.w, self.h, self.c = width, height, palette
        self.pen = Pen(seed)
        self.animate, self.tempo = bool(tempo), tempo
        self.clock = 0.0
        self.body = []
        self.used = set()

    # --- output -------------------------------------------------------------

    def _stroke(self, d, color, width, length=None, dash=None):
        attrs = f'd="{d}" stroke="{color}" stroke-width="{width}"'
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        if self.animate and (dash or length is None):
            attrs += self._fade()
            self.clock += 0.1 * self.tempo
        elif self.animate:
            took = min(max(length / 650, 0.1), 0.6) * self.tempo
            attrs += (
                f' class="d" style="--l:{math.ceil(length)};animation-delay:{self.clock:.2f}s;'
                f'animation-duration:{took:.2f}s"'
            )
            self.clock += took * 0.75
        return f"<path {attrs}/>"

    def _fade(self, at=None):
        if not self.animate:
            return ""
        return f' class="f" style="animation-delay:{self.clock if at is None else at:.2f}s"'

    def raw(self, markup):
        self.body.append(markup)

    def svg(self, label):
        defs = "".join(f'<path id="g{ord(ch)}" d="{GLYPHS[ch][1]}"/>' for ch in sorted(self.used))
        style = ""
        if self.animate:
            style = (
                "<style>.d{stroke-dasharray:var(--l);animation:d .3s ease-out backwards}"
                ".f,.g{animation:f .3s ease-out backwards}.g{animation-duration:.01s}"
                "@keyframes d{from{stroke-dashoffset:var(--l)}}@keyframes f{from{opacity:0}}"
                "@media (prefers-reduced-motion:reduce){.d,.f,.g{animation:none}.live{display:none}}</style>"
            )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
            f'height="{self.h}" role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
            f"<defs>{defs}</defs>{style}"
            f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">{"".join(self.body)}</g></svg>\n'
        )

    # --- strokes --------------------------------------------------------------

    def line(self, x1, y1, x2, y2, color=None, width=1.8, dash=None):
        d, length = self.pen.line(x1, y1, x2, y2, double=not dash)
        self.raw(self._stroke(d, color or self.c["ink"], width, length, dash))

    def curve(self, points, color=None, width=1.8):
        d, length = self.pen.curve(points)
        self.raw(self._stroke(d, color or self.c["ink"], width, length))

    def arrow(self, points, color=None, width=1.8, head=11):
        """Line or curve through the points with an open arrowhead at the last one."""
        color = color or self.c["ink"]
        if len(points) > 2:
            self.curve(points, color, width)
        else:
            self.line(*points[0], *points[1], color, width)
        (px, py), (x, y) = points[-2], points[-1]
        back = math.atan2(py - y, px - x)
        d = ""
        for side in (-1, 1):
            a = back + side * math.radians(24)
            d += self.pen.line(x + head * math.cos(a), y + head * math.sin(a), x, y)[0]
        self.raw(self._stroke(d, color, width, head + 4))

    def rect(self, x, y, w, h, fill=None, color=None, width=1.8, radius=None, dash=None, gap=7, solid=None):
        """Box with rounded corners. fill is a hachure colour, solid a flat one.

        The outline is drawn first and shaded afterwards, but the shading lies underneath.
        """
        color = color or self.c["ink"]
        r = min(min(w, h) * 0.25 if radius is None else radius, 32)
        started = self.clock
        if dash:
            outline = [self._stroke(self.pen.loop(x, y, w, h, r), color, width, dash=dash)]
        elif self.animate:
            outline = [self._stroke(d, color, width, length) for d, length in self.pen.box(x, y, w, h, r)]
        else:
            outline = [self._stroke("".join(d for d, _ in self.pen.box(x, y, w, h, r)), color, width)]
        if solid:
            self.raw(f'<path d="M{_join(*rounded(x, y, w, h, r))}Z" fill="{solid}"{self._fade(started)}/>')
        if fill:
            d, length = self.pen.hachure(rounded(x, y, w, h, r), gap)
            self.raw(self._stroke(d, fill, 1.0, length))
        self.body += outline

    def ellipse(self, cx, cy, w, h, color=None, width=1.8):
        d, length = self.pen.ellipse(cx, cy, w, h)
        self.raw(self._stroke(d, color or self.c["ink"], width, length))

    # --- lettering ------------------------------------------------------------

    def text(self, string, x, y, size, color=None, anchor="start", wobble=0.0, pace=0.012):
        """Write string with its baseline at y and return its width. wobble loosens the hand."""
        width = text_width(string, size)
        left = x - width * {"start": 0, "middle": 0.5, "end": 1}[anchor]
        scale = size / UPM
        out = [
            f'<g transform="translate({_n(left)} {_n(y)}) scale({scale:.4f} {-scale:.4f})" '
            f'fill="{color or self.c["ink"]}" stroke="none">'
        ]
        cursor = 0
        for ch in string:
            advance, outline = GLYPHS[ch]
            if outline:
                self.used.add(ch)
                if wobble:
                    place = (
                        f' transform="translate({cursor} {round(self.pen.jitter(16 * wobble))}) '
                        f'rotate({self.pen.jitter(2.4 * wobble):.1f})"'
                    )
                else:
                    place = f' x="{cursor}"'
                timing = ""
                if self.animate:
                    timing = f' class="g" style="animation-delay:{self.clock:.2f}s"'
                    self.clock += pace * self.tempo
                out.append(f'<use href="#g{ord(ch)}"{place}{timing}/>')
            cursor += advance
        self.raw("".join(out) + "</g>")
        return width
