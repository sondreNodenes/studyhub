"""Tiny helpers for StudyHub lecture figures (plain SVG, no dependencies).

Usage in a figure script:
    import sys; sys.path.insert(0, '<this folder>'); from svgkit import *
    b = [T(400, 22, 'Title', 'middle', 14, '700')]
    b += [node(100, 100, 'a'), node(250, 100, 'b'), arrow(100, 100, 250, 100)]
    svg('content/<course>/img/name.svg', 800, 300, b)
    shot('content/<course>/img/name.svg', '/tmp/name.png')   # then look at the PNG

House style: 800 px wide viewBox, Helvetica, title centred at y=22 (14 px bold), body text 11-12 px,
labels in slate (#334155 / #475569), accents blue #2563eb, green #16a34a, red #dc2626, amber #d97706,
purple #7c3aed. Light fills (#eff6ff, #dcfce7, #fde68a) for highlighted cells. Keep text >= 10 px.
"""
import math, os, subprocess, tempfile


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def T(x, y, s, a='start', sz=12, w='400', fill='#1a1f2b', extra=''):
    """Text. a = start | middle | end. For code or aligned columns pass extra=MONO."""
    return f'<text x="{x}" y="{y}" text-anchor="{a}" font-size="{sz}" font-weight="{w}" fill="{fill}" {extra}>{esc(s)}</text>'


MONO = 'font-family="Menlo, monospace" xml:space="preserve"'   # keeps repeated spaces


def R(x, y, w, h, fill, stroke, rx=6, sw=1.5, dash=False):
    d = ' stroke-dasharray="5 4"' if dash else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def L(x1, y1, x2, y2, col='#334155', sw=1.6, dash=False, mk=None):
    """Line; mk = marker id from COLS ('a' slate, 'g' green, 'r' red, 'b' blue, 'o' amber, 'p' purple) for an arrowhead."""
    d = ' stroke-dasharray="5 4"' if dash else ''
    m = f' marker-end="url(#{mk})"' if mk else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{sw}"{d}{m}/>'


def poly(pts, col, sw=2, dash=False):
    d = ' stroke-dasharray="6 4"' if dash else ''
    return f'<polyline fill="none" stroke="{col}" stroke-width="{sw}"{d} points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + '"/>'


def node(x, y, lab, fill='#ef4444', r=20, tc='#fff', sz=14):
    """Graph node: filled circle with a centred label."""
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="#7f1d1d" stroke-width="1"/>' + T(x, y + 5, lab, 'middle', sz, '700', tc)


def arrow(x1, y1, x2, y2, col='#334155', mk='a', r1=22, r2=24, off=0, sw=1.8, dash=False):
    """Arrow between two node centres, trimmed by the node radii. off shifts it sideways (use +off both ways for a <-> pair)."""
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy); ux, uy = dx / d, dy / d; nx, ny = -uy * off, ux * off
    return L(x1 + ux * r1 + nx, y1 + uy * r1 + ny, x2 - ux * r2 + nx, y2 - uy * r2 + ny, col, sw, dash, mk)


def loop(x, y, col='#334155', mk='a'):
    """Self-loop above a node at (x, y)."""
    return f'<path d="M{x-12},{y-17} C{x-40},{y-65} {x+40},{y-65} {x+12},{y-19}" fill="none" stroke="{col}" stroke-width="1.8" marker-end="url(#{mk})"/>'


COLS = [('a', '#334155'), ('g', '#16a34a'), ('r', '#dc2626'), ('b', '#2563eb'), ('o', '#d97706'), ('p', '#7c3aed')]
DEFS = '<defs>' + ''.join(f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for i, c in COLS) + '</defs>'


def svg(path, W, H, body):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">\n{DEFS}\n' + '\n'.join(body) + '\n</svg>\n')


CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def shot(svg_path, png_path, W=800, H=450):
    """Render an SVG to PNG with headless Chrome so you can look at it (overlaps, clipped text)."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', f'--user-data-dir={tmp}', f'--window-size={W},{H}',
                        f'--screenshot={os.path.abspath(png_path)}', 'file://' + os.path.abspath(svg_path)],
                       capture_output=True, timeout=60)
    return png_path
