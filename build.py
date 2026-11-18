#!/usr/bin/env python3
"""StudyHub build script.

Usage
  python3 build.py                 bundle everything in <home>/content into <home>/data.js (+ StudyHub-standalone.html)
  python3 build.py --content DIR   use DIR as <home> (default: $STUDYHUB_CONTENT, else this folder)
  python3 build.py --import FILE   unpack a bundle exported from the page ("Export my lectures")
                                   into <home>/content, then rebuild

<home> is the content folder: it holds content/, and optionally slides/ and materials/. Keeping it
apart from the engine lets one engine serve many course collections (see README.md).

Content layout
  content/<course-id>/course.md    course meta + "How the professor tests"
  content/<course-id>/NN-name.md   one file per lecture (notes + flashcards + quiz)
See README.md for the lecture file format.
"""
import json, os, re, sys, html

ROOT = os.path.dirname(os.path.abspath(__file__))


def _home():
    """--content DIR / $STUDYHUB_CONTENT / the engine folder itself."""
    if "--content" in sys.argv:
        i = sys.argv.index("--content")
        d = sys.argv[i + 1]
        del sys.argv[i:i + 2]
        return os.path.abspath(os.path.expanduser(d))
    return os.path.abspath(os.path.expanduser(os.environ.get("STUDYHUB_CONTENT") or ROOT))


HOME = _home()
CONTENT = os.path.join(HOME, "content")
sys.path.insert(0, os.path.join(ROOT, "engine"))
try:
    import slidemap  # links note sections to slide pages (needs pdftotext)
except Exception:
    slidemap = None


from svgmath import typeset_svg


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def import_bundle(path):
    text = read(path)
    parts = re.split(r"^=====FILE: (.+?)=====\s*$", text, flags=re.M)
    n = 0
    # parts = [preamble, name1, body1, name2, body2, ...]
    for i in range(1, len(parts), 2):
        rel, body = parts[i].strip(), parts[i + 1].lstrip("\n")
        dest = os.path.normpath(os.path.join(CONTENT, rel))
        if not dest.startswith(CONTENT + os.sep):
            print("skip unsafe path", rel)
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(body.rstrip() + "\n")
        n += 1
        print("wrote", os.path.relpath(dest, HOME))
    print(f"imported {n} file(s)")


def build():
    courses = []
    for cid in sorted(os.listdir(CONTENT)):
        cdir = os.path.join(CONTENT, cid)
        if not os.path.isdir(cdir) or not os.path.exists(os.path.join(cdir, "course.md")):
            continue
        lectures = []
        for fn in sorted(os.listdir(cdir)):
            if fn.endswith(".md") and fn != "course.md":
                lec = {"file": fn, "raw": read(os.path.join(cdir, fn))}
                sl = slidemap.lecture_slides(lec["raw"], os.path.dirname(HOME), os.path.join(HOME, ".slidecache.json"), HOME) if slidemap else None
                if sl:
                    lec["slides"] = sl
                lectures.append(lec)
        entry = {"dir": cid, "course": read(os.path.join(cdir, "course.md")), "lectures": lectures}
        idir = os.path.join(cdir, "img")
        if os.path.isdir(idir):
            import base64, mimetypes
            imgs = {}
            for fn in sorted(os.listdir(idir)):
                mt = {"svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(fn.rsplit(".", 1)[-1].lower())
                if mt:
                    with open(os.path.join(idir, fn), "rb") as fh:
                        payload = fh.read()
                        if mt == "image/svg+xml":
                            payload = typeset_svg(payload.decode("utf-8")).encode("utf-8")
                        imgs["img/" + fn] = "data:" + mt + ";base64," + base64.b64encode(payload).decode()
            entry["images"] = imgs
        ov = os.path.join(cdir, "overview.html")      # optional course overview page (mindmap), shown at #/c/<id>/overview
        if os.path.exists(ov):
            entry["overview"] = read(ov)
        sp = os.path.join(cdir, "setup.py")
        if os.path.exists(sp):
            entry["setup"] = read(sp)
        courses.append(entry)
    data = "window.STUDYHUB_DATA = " + json.dumps(courses, ensure_ascii=False, indent=1) + ";\n"
    with open(os.path.join(HOME, "data.js"), "w", encoding="utf-8") as f:
        f.write(data)
    nl = sum(len(c["lectures"]) for c in courses)
    ns = sum(1 for c in courses for l in c["lectures"] if l.get("slides"))
    print(f"data.js: {len(courses)} courses, {nl} lectures ({ns} with slide links)")

    # standalone single-file version (works when emailed / moved anywhere)
    idx = read(os.path.join(ROOT, "index.html"))
    runner = read(os.path.join(ROOT, "engine", "pyrunner.py")).replace("</script>", "<\\/script>")
    idx2 = re.sub(r'(<script type="text/plain" id="pyrunner">).*?(</script>)', lambda m: m.group(1) + runner + m.group(2), idx, flags=re.S)
    # a version stamp on data.js makes browsers fetch the new content after every build instead of a cached copy
    import hashlib
    ver = hashlib.sha1(data.encode("utf-8")).hexdigest()[:10]
    idx2 = re.sub(r'<script src="data\.js(?:\?v=[0-9a-f]+)?"></script>', f'<script src="data.js?v={ver}"></script>', idx2)
    if idx2 != idx and HOME == ROOT:   # a separate content folder never edits the engine's index.html
        with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
            f.write(idx2)
        idx = idx2
    standalone = re.sub(r'<script src="data\.js(?:\?v=[0-9a-f]+)?"></script>', lambda m: "<script>\n" + data.replace("</script>", "<\\/script>") + "</script>", idx)
    with open(os.path.join(HOME, "StudyHub-standalone.html"), "w", encoding="utf-8") as f:
        f.write(standalone)
    print("StudyHub-standalone.html written to", HOME)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--import":
        import_bundle(sys.argv[2])
    build()
