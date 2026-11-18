#!/usr/bin/env python3
"""Turn a font into scripts/glyphs.json: one SVG outline and advance width per character.

build.py draws its lettering from that file, so the generated images carry their own
handwriting and need no font at view time. Only rerun this to change the typeface:

    uv run --with fonttools --with brotli scripts/extract_glyphs.py Excalifont-Regular.woff2

The outlines in glyphs.json come from Excalifont, Copyright (c) 2024 by Excalidraw,
SIL Open Font License 1.1 (scripts/OFL.txt).
"""

import json
import string
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

CHARS = string.digits + string.ascii_letters + string.punctuation + " ·–—’…•×"


def main():
    font = TTFont(sys.argv[1])
    cmap, glyph_set = font.getBestCmap(), font.getGlyphSet()
    glyphs = {}
    for char in CHARS:
        name = cmap.get(ord(char))
        if name is None:
            raise SystemExit(f"font has no glyph for {char!r}")
        pen = SVGPathPen(glyph_set, ntos=lambda value: str(round(value)))
        glyph_set[name].draw(pen)
        glyphs[char] = [round(glyph_set[name].width), pen.getCommands()]
    out = Path(__file__).with_name("glyphs.json")
    out.write_text(json.dumps({"unitsPerEm": font["head"].unitsPerEm, "glyphs": glyphs}, ensure_ascii=False) + "\n")
    print(f"wrote {len(glyphs)} glyphs to {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
