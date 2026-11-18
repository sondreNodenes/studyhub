"""Typeset mathematical indices in SVG text labels when bundling StudyHub.

Keep code labels and existing tspan markup intact. No external fonts or network.
The SVGs remain editable source assets; build.py packages the typeset copy.
"""
import html
import re
import xml.etree.ElementTree as ET

_NAMES = {'sigma': 'σ', 'Sigma': 'Σ', 'mu': 'μ', 'rho': 'ρ', 'delta': 'δ',
          'theta': 'θ', 'lambda': 'λ', 'sum': 'Σ', 'grad': '∇'}
_WORDS = 'PVEP|ETP|MAPE|MSE|MAD|CSL|ROP|Sigma|sigma|lambda|argmin|argmax|theta|delta|grad|rho|sum|mu|PD|FI|VS|TC|EP|dw|hC|DC|bias|lr'
_BASE = re.compile(r'(?<![^\W\d_])(?<!_)(' + _WORDS + r'|[Δ∇][²³]?[A-Za-z]|[A-Za-zΑ-ωŷȳℓ])[\u0300-\u036f′\'²³]*(?=[_^])', re.UNICODE)
_TAG = '{http://www.w3.org/2000/svg}'


def _group(text, start):
    """Index/exponent and the position immediately after it, or None."""
    if start >= len(text):
        return None
    op = text[start]
    if op in '{(':
        close = '}' if op == '{' else ')'
        depth, end = 1, start + 1
        while end < len(text) and depth:
            depth += (text[end] == op) - (text[end] == close)
            end += 1
        return (text[start+1:end-1], end) if depth == 0 else None
    m = re.match(r'-?[A-Za-z0-9Α-ω]+(?![A-Za-z0-9Α-ω_])', text[start:])
    return (m[0], start+len(m[0])) if m else None


def _label(text):
    result, cursor = [], 0
    for match in _BASE.finditer(text):
        if match.start() < cursor:
            continue
        base = text[match.start():match.end()]
        result += [html.escape(text[cursor:match.start()], quote=False), html.escape(_NAMES.get(base, base), quote=False)]
        cursor = match.end()
        while cursor < len(text) and text[cursor] in '_^':
            kind = 'sub' if text[cursor] == '_' else 'super'
            group = _group(text, cursor+1)
            if not group:
                break
            content, cursor = group
            result.append(f'<tspan baseline-shift="{kind}" font-size="75%">{_label(content)}</tspan>')
    result.append(html.escape(text[cursor:], quote=False))
    return ''.join(result)


def typeset_svg(source):
    """Return a packaged SVG, preserving attributes and all non-text markup."""
    # Determine inherited monospace/code labels without reserialising the source.
    root = ET.fromstring(source)
    labels = list(root.iter(_TAG+'text'))
    protect = []

    def walk(node, mono=False):
        attr = ' '.join((node.get('font-family', ''), node.get('style', ''))).lower()
        mono = mono or any(x in attr for x in ('monospace', 'menlo', 'courier'))
        if node.tag == _TAG+'text':
            protect.append(mono or len(node) > 0)
        for child in node:
            walk(child, mono)
    walk(root)
    count = 0

    def replace(match):
        nonlocal count
        skip = protect[count] if count < len(protect) else True
        count += 1
        if skip:
            return match[0]
        return match[1] + _label(html.unescape(match[2])) + match[3]
    # Existing tspans count as one text element too, keeping protection aligned.
    return re.sub(r'(<text\b[^>]*>)([\s\S]*?)(</text>)', replace, source)
