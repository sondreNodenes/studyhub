"""Locate the StudyHub engine (the separate `studyhub` repo) and run one of its scripts on THIS folder's courses.
Engine: $STUDYHUB_ENGINE, else ../studyhub next to this repo."""
import os, runpy, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script):
    eng = os.path.abspath(os.path.expanduser(os.environ.get("STUDYHUB_ENGINE") or os.path.join(HERE, "..", "studyhub")))
    path = os.path.join(eng, script)
    if not os.path.exists(path):
        sys.exit(f"StudyHub engine not found at {eng}\nClone it next to this folder:  git clone <studyhub-repo-url> {os.path.join(HERE, '..', 'studyhub')}\n(or set STUDYHUB_ENGINE)")
    os.environ.setdefault("STUDYHUB_CONTENT", HERE)
    sys.argv[0] = path
    sys.path.insert(0, eng)
    runpy.run_path(path, run_name="__main__")
