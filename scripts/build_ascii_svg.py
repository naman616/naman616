"""
build_ascii_svg.py

Renders assets/ascii_art.txt into two crisp, scalable SVGs:
  - assets/ascii_art_dark.svg   (dark terminal card, for dark-mode viewers)
  - assets/ascii_art_light.svg  (light terminal card, for light-mode viewers)

Every row is stretched to an identical textLength, so columns stay
pixel-perfect regardless of which monospace font the viewer's browser
substitutes.

Re-run this any time assets/ascii_art.txt changes:

    python scripts/build_ascii_svg.py

README.md selects between the two automatically at render time using a
<picture> element with prefers-color-scheme media queries -- GitHub's
standard technique for theme-adaptive images (more reliable than a single
SVG with an internal media query, since some renderers strip <style>
media queries out of images fetched via <img src>).
"""

import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(__file__)
TXT_PATH = os.path.join(HERE, "..", "assets", "ascii_art.txt")
DARK_SVG_PATH = os.path.join(HERE, "..", "assets", "ascii_art_dark.svg")
LIGHT_SVG_PATH = os.path.join(HERE, "..", "assets", "ascii_art_light.svg")

CHAR_W = 7.2     # px per column at 1x scale
CHAR_H = 13.6    # px per row at 1x scale
FONT_SIZE = 13   # px

THEMES = {
    "dark": {
        "path": DARK_SVG_PATH,
        "bg": "#0d1117",     # GitHub dark-mode code-block background
        "fg": "#d7dde3",
    },
    "light": {
        "path": LIGHT_SVG_PATH,
        "bg": "#f6f8fa",     # GitHub light-mode code-block background
        "fg": "#24292f",
    },
}


def render_svg(lines, cols, width, height, bg, fg):
    text_elements = []
    for i, line in enumerate(lines):
        y = (i + 1) * CHAR_H - (CHAR_H - FONT_SIZE) / 2 - 2
        text_elements.append(
            f'<text x="0" y="{y:.2f}" textLength="{width:.2f}" '
            f'lengthAdjust="spacingAndGlyphs" xml:space="preserve" '
            f'class="ascii-row">{escape(line)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.2f} {height:.2f}"
     width="{width:.0f}" height="{height:.0f}" font-family="'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace">
  <style>
    .ascii-row {{
      font-size: {FONT_SIZE}px;
      fill: {fg};
      white-space: pre;
    }}
  </style>
  <rect x="0" y="0" width="{width:.2f}" height="{height:.2f}" fill="{bg}"/>
{chr(10).join(text_elements)}
</svg>
'''


def main():
    with open(TXT_PATH) as f:
        raw_lines = f.read().splitlines()

    cols = max(len(l) for l in raw_lines)
    rows = len(raw_lines)
    lines = [l.ljust(cols) for l in raw_lines]

    width = cols * CHAR_W
    height = rows * CHAR_H

    for name, theme in THEMES.items():
        svg = render_svg(lines, cols, width, height, theme["bg"], theme["fg"])
        with open(theme["path"], "w") as f:
            f.write(svg)
        print(f"Wrote {theme['path']} ({cols}x{rows} grid, {width:.0f}x{height:.0f}px)")


if __name__ == "__main__":
    main()
