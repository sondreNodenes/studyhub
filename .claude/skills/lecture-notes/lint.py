#!/usr/bin/env python3
"""Check a StudyHub lecture file for format errors and the quality rules in SKILL.md.

Usage:  python3 lint.py content/<course>/NN-name.md [more files ...]
Exit code 1 if there are ERRORS (the app would drop or mis-grade something); WARNINGS are quality hints.
"""
import itertools, math, os, re, sys
from statistics import NormalDist
_N = NormalDist()

HERE = os.path.dirname(os.path.abspath(__file__))
STUDYHUB = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ROOT = os.path.dirname(STUDYHUB)                    # folder above StudyHub (pdf: paths are relative to it)
RESERVED = re.compile(r'^(highlight|explain|example|flash|quiz|question)', re.I)
ACR_OK = {'PDF', 'URL', 'HTML', 'CSS', 'CPU', 'GPU', 'RAM', 'API', 'SQL', 'JSON', 'CSV', 'XML', 'HTTP', 'USA', 'UK', 'EU',
          'AI', 'ML', 'OK', 'ID', 'IP', 'IT', 'PC', 'TV', 'GB', 'MB', 'KB', 'TB', 'CEO', 'II', 'III', 'IV', 'VI', 'VII', 'NB',
          'TRUE', 'FALSE', 'NOT', 'AND', 'OR', 'US', 'USD', 'EUR', 'RMB', 'CNY', 'NOK', 'HIV', 'DNA', 'IEEE', 'ACM', 'AWS', 'NVIDIA', 'HPE', 'EMC', 'AMD', 'SAP', 'UPS', 'DHL', 'IKEA'}
GEN_FNS = {'sqrt': math.sqrt, 'log': math.log, 'ln': math.log, 'exp': math.exp, 'pow': pow, 'abs': abs, 'min': min,
           'max': max, 'round': round, 'floor': math.floor, 'ceil': math.ceil, 'PI': math.pi,
           'normcdf': lambda x: _N.cdf(x), 'normpdf': lambda x: _N.pdf(x), 'norminv': lambda p: _N.inv_cdf(p)}


def gen_values(spec):
    m = re.match(r'^(-?[\d.]+)\s*\.\.\s*(-?[\d.]+)(?:\s+step\s+([\d.]+))?$', spec.strip())
    if m:
        a, b, st = float(m[1]), float(m[2]), float(m[3] or 1)
        out, v = [], a
        while v <= b + 1e-9:
            out.append(round(v, 6)); v += st
        return out
    return [float(x) for x in spec.split(',') if re.match(r'^\s*-?[\d.]+\s*$', x)]


def lint(path):
    E, W = [], []
    raw = open(path, encoding='utf-8').read().replace('\r', '')
    lines = raw.split('\n')
    if not lines or not lines[0].startswith('# '):
        E.append('first line must be "# Lecture N - Title"')
    if not re.search(r'^code:\s*\S', raw, re.M):
        W.append('no "code:" line (e.g. code: L5)')
    pm = re.search(r'^pdf:\s*(.+)$', raw, re.M)
    if not pm:
        W.append('no "pdf:" line - the slides will not show next to the notes')
    else:
        for p in [x.strip() for x in pm[1].split('|') if x.strip()]:
            # main repo: path relative to the folder above StudyHub; shared copies: slides/... next to index.html
            if not (os.path.exists(os.path.join(ROOT, p)) or os.path.exists(os.path.join(STUDYHUB, p))):
                (W if p.startswith('slides/') else E).append(f'pdf not found: {p}' + ('' if p.startswith('slides/') else f' (path must be relative to {ROOT})'))

    # sections
    secs, cur, body = [], 'head', {}
    for ln in lines:
        if re.match(r'^<!--.*-->\s*$', ln.strip()):
            continue
        h = re.match(r'^##\s+(.+)$', ln)
        if h:
            n = h[1].strip().lower()
            kind = ('highlights' if n.startswith('highlight') else 'explained' if n.startswith('explain') else
                    'examples' if n.startswith('example') else 'cards' if n.startswith('flash') else
                    'quiz' if re.match(r'^(quiz|question)', n) else 'summary')
            if cur == 'summary' and kind != 'summary' and kind not in secs and kind in ('examples', 'quiz') and 'explained' not in secs:
                W.append(f'heading "## {h[1]}" inside the notes starts a new {kind} section - rename it (e.g. "Worked case: ...")')
            secs.append(kind); cur = kind
            body.setdefault(kind, []).append(ln)
            continue
        body.setdefault(cur, []).append(ln)
    for need in ('highlights', 'summary', 'explained', 'cards', 'quiz'):
        if need not in secs:
            E.append(f'missing section: {need}')
    summary = '\n'.join(body.get('summary', []))
    subheads = [l for l in body.get('summary', []) if l.startswith('## ') and not re.match(r'^##\s+(summary|notes)\s*$', l, re.I)]
    if len(subheads) < 4:
        W.append(f'only {len(subheads)} topic headings in the notes - split the lecture into one "##" section per topic')
    if summary.count('> **Key idea:**') < 2:
        W.append('fewer than 2 "> **Key idea:**" callouts in the notes')
    bad_sub = sorted(set(re.findall(r'[A-Za-z0-9]_\([^)]*\)', re.sub(r'```.*?```|<!--.*?-->', '', raw, flags=re.S))))
    if bad_sub:
        W.append('subscripts in round brackets do not render (e.g. ' + ', '.join(bad_sub[:3]) + ') - write A_{i+1}')

    # images
    imgs = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', raw)
    for im in imgs:
        if not im.startswith(('http', 'data:')) and not os.path.exists(os.path.join(os.path.dirname(path), im)):
            E.append(f'image not found: {im}')
    if not imgs:
        W.append('no figures - add SVGs where a picture explains a mechanism better than text')

    # flashcards
    cards, c = [], None
    for ln in body.get('cards', [])[1:]:
        if ln.startswith('Q:'):
            if c: cards.append(c)
            c = {'q': ln[2:].strip(), 'a': ''}
        elif ln.startswith('A:') and c is not None:
            c['a'] = ln[2:].strip()
        elif c is not None and ln.strip():
            c['a' if c['a'] else 'q'] += ' ' + ln.strip()
    if c: cards.append(c)
    for c in cards:
        if not c['a']:
            E.append(f'flashcard without answer: {c["q"][:60]}')
        if len(c['a']) > 420:
            W.append(f'long flashcard answer ({len(c["a"])} chars) - split it: {c["q"][:60]}')
    seen = {}
    for c in cards:
        k = re.sub(r'\W+', ' ', c['q'].lower()).strip()
        if k in seen:
            E.append(f'duplicate flashcard: {c["q"][:60]}')
        seen[k] = 1
    if len(cards) < 25:
        W.append(f'only {len(cards)} flashcards - cover every section of the lecture (aim 30-40)')
    # acronyms in cards must be explained somewhere in the file
    for c in cards:
        for acr in set(re.findall(r'(?<![&/])\b[A-Z][A-Z0-9]{1,5}s?\b(?![&/])', c['q'] + ' ' + c['a'])):
            a = acr.rstrip('s') if acr.endswith('s') and acr[:-1].isupper() else acr
            if a in ACR_OK or len(a) < 2 or not re.search('[A-Z]{2}', a):
                continue
            explained = re.search(rf'\b{re.escape(a)}s?\s*\(|\({re.escape(a)}s?\)|\b{re.escape(a)}s?\b\s*[=:-]\s', raw)
            if not explained:
                W.append(f'acronym "{a}" in a flashcard is never spelled out - explain it in the card: {c["q"][:50]}')

    # quiz
    qs, q = [], None
    for ln in body.get('quiz', [])[1:]:
        if re.match(r'^<!--.*-->\s*$', ln.strip()):
            continue
        m = re.match(r'^\?\s*(?:\[(\w+)\])?\s*(.*)$', ln)
        if m:
            if q: qs.append(q)
            q = {'type': (m[1] or 'short').lower(), 'text': m[2], 'opts': [], 'ans': None, 'vars': {}, 'expl': ''}
            continue
        if q is None:
            continue
        if q['type'] in ('mcq', 'multi') and re.match(r'^[-*]\s+', ln):
            q['opts'].append((ln[0] == '*', re.sub(r'^[-*]\s+', '', ln).strip()))
        elif ln.startswith('@'):
            vm = re.match(r'^@\s*(\w+)\s*=\s*(.+)$', ln)
            if vm: q['vars'][vm[1]] = gen_values(vm[2])
        elif ln.startswith('='):
            q['ans'] = ln[1:].strip()
        elif ln.startswith('>'):
            q['expl'] = ln[1:].strip()
    if q: qs.append(q)

    # items are shuffled: a question must not lean on another one, and a calculation must say what its symbols are
    CTX = re.compile(r'^(same|again|also|then|now|next|and)\s|\bsame (jobs?|graph|data|setup|example|numbers?|stream|document|network|settings?|case|start|objects?|lsh|spider trap)\b|\bthat same\b|\b(as|from) (above|before)\b|\bthe previous (question|part)\b|\(instead of\b', re.I)
    for q in qs:
        t = re.sub(r'`[^`]*`', '', q['text'])
        if CTX.search(t):
            W.append(f'question depends on another one - repeat its context: {q["text"][:70]}')
        elif q['type'] in ('calc', 'gen') and len(re.findall(r'\b[A-Za-z]{1,3}(_\w+)? ?= ?[-\d{]', t)) >= 2 and len(re.sub(r'[^a-z ]', '', t.lower()).split()) < 12:
            W.append(f'calculation is only symbols - say what each one is: {q["text"][:70]}')
    DEMO = re.compile(r"\bdemo\b|what did (the )?[\w\s'-]{0,40}(example|case|study|demo)? ?show|in the (slide'?s? )?example|the slide'?s (table|example|figure)", re.I)
    for c in cards:
        if DEMO.search(c['q']):
            W.append(f'flashcard asks about a demo/example itself - ask about the idea it illustrates: {c["q"][:70]}')
        if CTX.search(re.sub(r'`[^`]*`', '', c['q'])):
            W.append(f'flashcard depends on another card - repeat its context: {c["q"][:70]}')
    longest = 0; nmcq = 0; tf = []
    texts = {}
    for q in qs:
        lab = q['text'][:60]
        k = re.sub(r'\W+', ' ', q['text'].lower()).strip()
        if k in texts and q['type'] != 'gen':
            E.append(f'duplicate quiz question: {lab}')
        texts[k] = 1
        t = q['type']
        if t == 'mcq':
            nmcq += 1
            right = [o for o in q['opts'] if o[0]]
            if len(right) != 1:
                E.append(f'mcq needs exactly one "*" option: {lab}')
                continue
            if len(q['opts']) < 4:
                W.append(f'mcq with fewer than 4 options: {lab}')
            lens = [len(o[1]) for o in q['opts']]
            rl = len(right[0][1]); others = [len(o[1]) for o in q['opts'] if not o[0]]
            if rl > max(others):
                longest += 1
                if rl > 1.25 * max(others) and rl - max(others) > 8:
                    W.append(f'correct option is clearly the longest - make the distractors as long and specific: {lab}')
        elif t == 'multi':
            if len(q['opts']) < 3 or not any(o[0] for o in q['opts']):
                E.append(f'multi needs >= 3 options and at least one "*": {lab}')
        elif t == 'tf':
            if (q['ans'] or '').lower() not in ('true', 'false'):
                E.append(f'tf answer must be "= true" or "= false": {lab}')
            else:
                tf.append(q['ans'].lower())
        elif t == 'calc':
            if not q['ans'] or not re.match(r'^-?\d[\d,]*\.?\d*|^-?\.\d+', q['ans']):
                E.append(f'calc answer must start with a number (e.g. "= 0.467 ±0.002"): {lab}')
            if not q['expl']:
                W.append(f'calc without a "> worked solution" line: {lab}')
        elif t == 'gen':
            if not q['vars'] or not q['ans']:
                E.append(f'gen needs @ variables and an "= expression ±tol": {lab}')
                continue
            expr = re.sub(r'\s*(?:±|\+/-)\s*[\d.]+\s*%?\s*$', '', q['ans'])
            if re.search(r'(^|[(*/+,])\s*-\s*[\w.()]+\s*\^', expr):
                W.append(f'"-x^n" in a gen formula: JavaScript rejects unary minus before a power - write -(x^n) or (-x)^n: {lab}')
            py = expr.replace('^', '**')
            names = list(q['vars'])
            bad = None
            for combo in itertools.islice(itertools.product(*q['vars'].values()), 400):
                env = dict(GEN_FNS, **dict(zip(names, combo)))
                try:
                    v = eval(py, {'__builtins__': {}}, env)
                    if not isinstance(v, (int, float)) or not math.isfinite(v):
                        bad = f'{dict(zip(names, combo))} -> {v}'; break
                except Exception as e:
                    bad = f'{dict(zip(names, combo))} -> {type(e).__name__}: {e}'; break
            if bad:
                E.append(f'gen formula fails for {bad}: {lab}')
            for ph in set(re.findall(r'\{(\w+)\}', q['text'] + q['expl'])):
                if ph != 'answer' and ph not in q['vars']:
                    W.append(f'{{{ph}}} is not an @ variable, so it is shown literally - fine for set notation, otherwise a typo: {lab}')
        elif t in ('short', 'code'):
            if not q['ans']:
                E.append(f'{t} question without "= model answer": {lab}')
        else:
            W.append(f'unknown question type [{t}] (treated as short): {lab}')
    if nmcq >= 6 and longest / nmcq > 0.35:
        W.append(f'the correct option is the longest in {longest}/{nmcq} MCQs - students learn to pick the longest; balance option lengths')
    if len(tf) >= 4 and (tf.count('true') == 0 or tf.count('false') == 0):
        W.append('all true/false answers are the same - mix true and false statements')
    types = {}
    for q in qs:
        types[q['type']] = types.get(q['type'], 0) + 1
    if len(qs) < 20:
        W.append(f'only {len(qs)} quiz questions (aim 25-35, mixed types)')
    return E, W, {'cards': len(cards), 'questions': len(qs), 'types': types, 'figures': len(imgs), 'sections': len(subheads)}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    bad = False
    for p in sys.argv[1:]:
        E, W, st = lint(p)
        print(f'\n{p}\n  {st}')
        for e in E: print('  ERROR   ', e)
        for w in W: print('  warning ', w)
        if not E and not W: print('  all checks passed')
        bad |= bool(E)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
