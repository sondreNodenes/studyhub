import ast, copy, io, json as _json, contextlib, math as _math, re as _re, traceback

_NOVAL = object()


class _Plt:
    def __getattr__(self, name):
        return lambda *a, **k: None


def _base_ns():
    import numpy, pandas
    from collections import Counter
    d = {'__name__': '__main__', 'np': numpy, 'pd': pandas, 're': _re, 'json': _json, 'math': _math,
         'Counter': Counter, 'plt': _Plt()}
    try:
        import bs4
        d['bs4'] = bs4
    except ImportError:
        pass
    return d


def _eq(a, b):
    if a is b:
        return True
    try:
        import numpy as np, pandas as pd
        if isinstance(a, pd.DataFrame) or isinstance(b, pd.DataFrame):
            if not (isinstance(a, pd.DataFrame) and isinstance(b, pd.DataFrame)):
                return False
            pd.testing.assert_frame_equal(a, b, check_dtype=False, check_names=False)
            return True
        if isinstance(a, pd.Series) or isinstance(b, pd.Series):
            if not (isinstance(a, pd.Series) and isinstance(b, pd.Series)):
                return False
            pd.testing.assert_series_equal(a, b, check_dtype=False, check_names=False)
            return True
        if isinstance(a, pd.Index) or isinstance(b, pd.Index):
            return list(a) == list(b)
        if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
            a, b = np.asarray(a), np.asarray(b)
            if a.shape != b.shape:
                return False
            if a.dtype.kind in 'fc' or b.dtype.kind in 'fc':
                return bool(np.allclose(a, b, equal_nan=True))
            return bool(np.array_equal(a, b))
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            return len(a) == len(b) and all(_eq(x, y) for x, y in zip(a, b))
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(_eq(a[k], b[k]) for k in a)
        if isinstance(a, (int, float, np.number)) and isinstance(b, (int, float, np.number)) and not isinstance(a, bool) and not isinstance(b, bool):
            return _math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9) or (a != a and b != b)
        if type(a).__module__.startswith('bs4') or type(b).__module__.startswith('bs4'):
            return str(a) == str(b)
        r = (a == b)
        return bool(r) if not hasattr(r, 'all') else bool(r.all())
    except Exception:
        return False


def _show(v, limit=1800):
    try:
        import pandas as pd
        if isinstance(v, pd.DataFrame):
            s = v.to_string(max_rows=12, max_cols=10)
        elif isinstance(v, pd.Series):
            s = v.to_string(max_rows=12)
        else:
            s = repr(v)
    except Exception:
        s = repr(v)
    return s if len(s) <= limit else s[:limit] + ' ...'


def _skip(v):
    import types
    return isinstance(v, (types.ModuleType, types.FunctionType, type, _Plt)) or (callable(v) and not hasattr(v, 'shape'))


def _snapshot(ns):
    snap = {}
    for k, v in ns.items():
        if k.startswith('_') or _skip(v):
            continue
        try:
            snap[k] = (v, copy.deepcopy(v))
        except Exception:
            snap[k] = (v, v)
    return snap


def _changed(k, v, snap):
    if k not in snap:
        return True
    orig, cp = snap[k]
    if v is orig:
        import numpy as np, pandas as pd
        if isinstance(v, (pd.DataFrame, pd.Series, np.ndarray, list, dict, set)):
            return not _eq(v, cp)
        return False
    return not _eq(v, cp)


def _run(setup, code, pristine=False):
    r = {'ns': None, 'out': '', 'err': None, 'val': _NOVAL, 'changed': {}, 'bound': set()}
    out = io.StringIO()
    ns = {'__name__': '__main__'} if pristine else _base_ns()
    r['ns'] = ns
    try:
        with contextlib.redirect_stdout(out):
            if not pristine:
                ns['np'].random.seed(0)
            if not pristine and setup.strip():
                exec(setup, ns)
            if not pristine:
                ns['np'].random.seed(0)
            before = set(ns.keys())
            snap = _snapshot(ns)
            body = ast.parse(code).body
            last = body.pop() if body and isinstance(body[-1], ast.Expr) else None
            exec(compile(ast.Module(body, []), '<code>', 'exec'), ns)
            if last is not None:
                r['val'] = eval(compile(ast.Expression(last.value), '<code>', 'eval'), ns)
            elif body and isinstance(body[-1], ast.Assign) and len(body[-1].targets) == 1 and isinstance(body[-1].targets[0], ast.Name):
                r['val'] = ns[body[-1].targets[0].id]
            r['bound'] = set(ns.keys()) - before
            for k, v in ns.items():
                if k.startswith('_') or _skip(v):
                    continue
                if _changed(k, v, snap):
                    r['changed'][k] = v
    except BaseException as e:
        tb = traceback.format_exception_only(type(e), e)
        r['err'] = ''.join(tb).strip()
    r['out'] = out.getvalue()
    return r


def _is_import_only(code):
    try:
        body = ast.parse(code).body
        return bool(body) and all(isinstance(n, (ast.Import, ast.ImportFrom)) for n in body)
    except Exception:
        return False


def sh_run(setup, code):
    r = _run(setup, code)
    return _json.dumps({'out': r['out'], 'err': r['err'], 'val': None if r['val'] is _NOVAL else _show(r['val'])})


def sh_check(setup, code, ref, calls, tests):
    calls, tests = _json.loads(calls or '[]'), _json.loads(tests or '{}')
    if tests.get('match') or tests.get('nomatch') or tests.get('find'):
        return _check_pattern(code, ref, tests)
    if _is_import_only(ref):
        a, b = _run('', ref, True), _run('', code, True)
        if b['err']:
            return _json.dumps({'verdict': 'error', 'err': b['err'], 'out': b['out']})
        ok = a['bound'] <= b['bound']
        return _json.dumps({'verdict': 'ok' if ok else 'diff', 'out': b['out'], 'val': None, 'expected': 'names defined: ' + ', '.join(sorted(a['bound']))})
    exp, usr = _run(setup, ref), _run(setup, code)
    if exp['err']:
        return _json.dumps({'verdict': 'unverifiable', 'out': usr['out'], 'err': usr['err'], 'val': None if usr['val'] is _NOVAL else _show(usr['val'])})
    shown = None if usr['val'] is _NOVAL else _show(usr['val'])
    if usr['err']:
        return _json.dumps({'verdict': 'error', 'err': usr['err'], 'out': usr['out']})
    checks, ok = 0, True
    if exp['val'] is not _NOVAL:
        checks += 1
        cands = [usr['val']] + list(usr['changed'].values())
        if not any(c is not _NOVAL and _eq(c, exp['val']) for c in cands):
            ok = False
    for k, v in exp['changed'].items():
        if exp['val'] is not _NOVAL and v is exp['val']:
            continue
        checks += 1
        if not (k in usr['ns'] and _eq(usr['ns'][k], v)):
            ok = False
    for c in calls:
        checks += 1
        try:
            ev = eval(c, exp['ns']); uv = eval(c, usr['ns'])
            if not _eq(ev, uv):
                ok = False
        except BaseException:
            ok = False
    if exp['out'].strip() and exp['val'] is _NOVAL and not exp['changed']:
        checks += 1
        if usr['out'].strip() != exp['out'].strip():
            ok = False
    if not checks:
        return _json.dumps({'verdict': 'unverifiable', 'out': usr['out'], 'val': shown})
    return _json.dumps({'verdict': 'ok' if ok else 'diff', 'out': usr['out'], 'val': shown,
                        'expected': None if ok else (_show(exp['val']) if exp['val'] is not _NOVAL else exp['out'] or ', '.join(exp['changed']))})


def _pattern_of(code):
    c = code.strip()
    try:
        v = eval(c, {})
        if isinstance(v, str):
            return v
    except Exception:
        pass
    return c


def _check_pattern(code, ref, tests):
    pat, rp = _pattern_of(code), _pattern_of(ref)
    res, ok = [], True
    try:
        cp, rc = _re.compile(pat), _re.compile(rp)
    except _re.error as e:
        return _json.dumps({'verdict': 'error', 'err': 'Invalid regular expression: ' + str(e), 'out': ''})
    for s in tests.get('match', []):
        m, rm = cp.fullmatch(s), rc.fullmatch(s)
        good = m is not None and (rc.groups == 0 or (rm is not None and m.groups() == rm.groups()))
        ok &= good
        res.append({'s': s, 'want': True, 'got': m is not None, 'ok': good, 'groups': list(m.groups()) if m and cp.groups else None})
    for s in tests.get('nomatch', []):
        m = cp.fullmatch(s)
        good = m is None
        ok &= good
        res.append({'s': s, 'want': False, 'got': m is not None, 'ok': good, 'groups': None})
    for s in tests.get('find', []):
        got, want = cp.findall(s), rc.findall(s)
        good = got == want
        ok &= good
        res.append({'s': s, 'find': True, 'want': want, 'got': got, 'ok': good, 'groups': None})
    return _json.dumps({'verdict': 'ok' if ok else 'diff', 'tests': res, 'out': '', 'val': None, 'expected': None})


def sh_describe(setup, names):
    names = set(_json.loads(names))
    ns = _base_ns()
    try:
        ns['np'].random.seed(0)
        exec(setup, ns)
    except BaseException as e:
        return _json.dumps({'text': 'Setup failed: ' + str(e)})
    parts = []
    for k, v in ns.items():
        if k.startswith('_') or k not in names or _skip(v) or k in ('np', 'pd', 're', 'json', 'math', 'Counter', 'plt', 'bs4'):
            continue
        try:
            import pandas as pd, numpy as np
            if isinstance(v, pd.DataFrame):
                parts.append(k + ' = DataFrame, shape ' + str(v.shape) + '\n' + v.head(8 if len(v) <= 8 else 4).to_string(max_cols=8))
            elif isinstance(v, pd.Series):
                parts.append(k + ' = Series\n' + v.head(5).to_string())
            elif isinstance(v, np.ndarray):
                parts.append(k + ' = array, shape ' + str(v.shape) + ': ' + repr(v)[:160])
            else:
                parts.append(k + ' = ' + repr(v)[:160])
        except Exception:
            pass
    return _json.dumps({'text': '\n\n'.join(parts) or 'No sample data for this one.'})
