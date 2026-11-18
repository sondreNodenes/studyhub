#!/usr/bin/env python3
"""Turn lecture notebooks (Jupyter / RISE slideshows) into a slide PDF for the StudyHub slide pane.

Usage
  python3 engine/nb2pdf.py OUT.pdf NOTEBOOK[:FIRST[:LAST]] [NOTEBOOK[:FIRST[:LAST]] ...]

  FIRST / LAST are cell indexes (inclusive, 0-based) to take only part of a notebook, so several
  notebooks can be stitched into one deck. A new page starts at every RISE "slide"/"subslide" cell
  and at every markdown heading. Cells marked "skip" or "notes" are left out. Images referenced
  from the notebook folder are embedded. Needs Google Chrome (for printing) and internet the first
  time (the Markdown renderer is loaded from a CDN).
"""
import base64, html, json, mimetypes, os, re, subprocess, sys, tempfile

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
MAX_OUT_LINES = 30


def embed_images(text, base):
    def data_uri(rel):
        p = os.path.join(base, rel)
        if not os.path.isfile(p):
            return rel
        mt = mimetypes.guess_type(p)[0] or 'image/png'
        with open(p, 'rb') as f:
            return 'data:%s;base64,%s' % (mt, base64.b64encode(f.read()).decode())
    text = re.sub(r'(src=["\'])(?!https?:|data:)([^"\']+)(["\'])', lambda m: m.group(1) + data_uri(m.group(2)) + m.group(3), text)
    text = re.sub(r'(!\[[^\]]*\]\()(?!https?:|data:)([^)\s]+)(\))', lambda m: m.group(1) + data_uri(m.group(2)) + m.group(3), text)
    return text


def strip_emoji(s):
    return re.sub('[\U00010000-\U0010FFFF]', '', s)


def clip(text):
    lines = text.rstrip('\n').split('\n')
    if len(lines) > MAX_OUT_LINES:
        lines = lines[:MAX_OUT_LINES] + ['... (%d more lines)' % (len(lines) - MAX_OUT_LINES)]
    return '\n'.join(lines)


def outputs_html(cell, base):
    parts = []
    for o in cell.get('outputs', []):
        if o.get('output_type') == 'stream':
            parts.append('<pre class="out">%s</pre>' % html.escape(clip(''.join(o.get('text', '')))))
        elif o.get('output_type') in ('execute_result', 'display_data'):
            d = o.get('data', {})
            if 'image/png' in d:
                parts.append('<img class="outimg" src="data:image/png;base64,%s">' % ''.join(d['image/png']).replace('\n', ''))
            elif 'text/html' in d:
                parts.append('<div class="outhtml">%s</div>' % embed_images(''.join(d['text/html']), base))
            elif 'text/plain' in d:
                parts.append('<pre class="out">%s</pre>' % html.escape(clip(''.join(d['text/plain']))))
        elif o.get('output_type') == 'error':
            parts.append('<pre class="out err">%s: %s</pre>' % (html.escape(o.get('ename', '')), html.escape(o.get('evalue', ''))))
    return ''.join(parts)


def slides_from(spec):
    path, first, last = (spec.split(':') + [None, None])[:3]
    nb = json.load(open(path, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(path))
    cells = nb['cells']
    lo = int(first) if first else 0
    hi = int(last) if last else len(cells) - 1
    slides, cur = [], []
    for c in cells[lo:hi + 1]:
        kind = c.get('metadata', {}).get('slideshow', {}).get('slide_type', '-')
        if kind in ('skip', 'notes'):
            continue
        src = strip_emoji(''.join(c['source']))
        if not src.strip() and not c.get('outputs'):
            continue
        heading = c['cell_type'] == 'markdown' and src.lstrip().startswith('#')
        if cur and (kind in ('slide', 'subslide') or heading):
            slides.append(cur)
            cur = []
        if c['cell_type'] == 'markdown':
            cur.append({'md': embed_images(src, base)})
        else:
            cur.append({'code': src, 'out': outputs_html(c, base)})
    if cur:
        slides.append(cur)
    return slides


PAGE = '''<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<style>
@page { size: 13.333in 7.5in; margin: 0.45in 0.6in; }
body { font: 17px/1.45 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1a1f2b; margin: 0; }
.slide { break-before: page; }
.slide:first-child { break-before: auto; }
h1 { font-size: 34px; margin: .2em 0 .4em; } h2 { font-size: 28px; margin: .2em 0 .4em; } h3 { font-size: 24px; margin: .1em 0 .4em; color: #1d4ed8; }
p, li { margin: .25em 0; } img { max-width: 100%; max-height: 4.4in; }
code { font-family: Menlo, Consolas, monospace; font-size: .88em; background: #f1f5f9; padding: 0 3px; border-radius: 3px; }
pre { font: 13px/1.35 Menlo, Consolas, monospace; white-space: pre-wrap; word-break: break-word; margin: .4em 0; padding: 8px 12px; border-radius: 6px; }
pre.code { background: #f1f5f9; border-left: 4px solid #2563eb; }
pre.out { background: #fff; border: 1px solid #e2e8f0; color: #334155; }
pre.err { color: #b91c1c; }
.outhtml { font-size: 13px; overflow: hidden; max-height: 4in; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 4px 10px; margin: .4em 0; }
.outhtml h1, .outhtml h2, .outhtml h3 { font-size: 15px; color: inherit; margin: .2em 0; } .outhtml p { margin: .1em 0; } .outhtml table { border-collapse: collapse; } .outhtml td, .outhtml th { border: 1px solid #e2e8f0; padding: 2px 6px; }
table { border-collapse: collapse; margin: .4em 0; } td, th { border: 1px solid #cbd5e1; padding: 4px 10px; text-align: left; }
center { display: block; text-align: center; }
</style></head><body><div id="deck"></div>
<script>
const SLIDES = __DATA__;
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
document.getElementById('deck').innerHTML = SLIDES.map(s => '<div class="slide">' + s.map(c =>
  c.md !== undefined ? marked.parse(c.md) : '<pre class="code">' + esc(c.code) + '</pre>' + c.out).join('') + '</div>').join('');
</script></body></html>'''


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    slides = []
    for spec in sys.argv[2:]:
        slides += slides_from(spec)
    page = PAGE.replace('__DATA__', json.dumps(slides).replace('</', '<\\/'))
    with tempfile.TemporaryDirectory() as tmp:
        h = os.path.join(tmp, 'deck.html')
        with open(h, 'w', encoding='utf-8') as f:
            f.write(page)
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', '--virtual-time-budget=15000',
                        '--user-data-dir=' + os.path.join(tmp, 'chrome'), '--print-to-pdf=' + out, 'file://' + h],
                       capture_output=True, timeout=180)
    print('%s: %d slides' % (out, len(slides)) if os.path.exists(out) else 'failed to write ' + out)


if __name__ == '__main__':
    main()
