#!/usr/bin/env python3
"""Serve StudyHub and save your progress to a file.

Usage
  python3 serve.py              open http://localhost:8000/ (same address as `python3 -m http.server 8000`)
  python3 serve.py --port 8001
  python3 serve.py --content DIR   serve the courses in DIR (content/, slides/, materials/, data.js);
                                   default $STUDYHUB_CONTENT, else this folder. Files in DIR win over the engine's.

The page syncs with /studyhub-sync every few seconds while you study (see syncNow in index.html):
GET returns the saved copy, PUT stores the merged copy. Progress is kept in
  ~/Library/Mobile Documents/com~apple~CloudDocs/StudyHub/studyhub-sync.json   (iCloud Drive, if available)
  ~/StudyHub-progress/studyhub-sync.json                                       (otherwise)
with an hourly copy in backups/ next to it (the newest 300 are kept). Set STUDYHUB_DATA to use another folder.
"""
import argparse, functools, http.server, json, os, shutil, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
HOME = ROOT   # set from --content in main()
ICLOUD = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
DATA_DIR = os.environ.get("STUDYHUB_DATA") or (os.path.join(ICLOUD, "StudyHub") if os.path.isdir(ICLOUD) else os.path.expanduser("~/StudyHub-progress"))
SYNC_FILE = os.path.join(DATA_DIR, "studyhub-sync.json")
BACKUPS = os.path.join(DATA_DIR, "backups")
KEEP = 300


def load():
    try:
        with open(SYNC_FILE, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "{}"


def save(body):
    os.makedirs(BACKUPS, exist_ok=True)
    tmp = SYNC_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, SYNC_FILE)          # atomic: a crash never leaves a half-written file
    stamp = os.path.join(BACKUPS, time.strftime("studyhub-sync-%Y-%m-%d-%H.json"))
    shutil.copyfile(SYNC_FILE, stamp)   # one copy per hour, overwritten within the hour
    old = sorted(os.listdir(BACKUPS))[:-KEEP]
    for name in old:
        os.remove(os.path.join(BACKUPS, name))


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        """Files in the content folder shadow the engine's, so index.html comes from the engine and data.js,
        slides/, materials/ ... from the courses."""
        p = super().translate_path(path)          # resolved against the engine folder
        if HOME != ROOT:
            rel = os.path.relpath(p, ROOT)
            alt = os.path.normpath(os.path.join(HOME, rel))
            if alt.startswith(HOME + os.sep) and os.path.isfile(alt):
                return alt
        return p

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] != "/studyhub-sync":
            return super().do_GET()
        body = load().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        if self.path.split("?")[0] != "/studyhub-sync":
            return self.send_error(405)
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
        try:
            data = json.loads(raw)
            assert isinstance(data, dict) and "progress" in data
        except Exception:
            return self.send_error(400, "not a StudyHub sync body")
        save(json.dumps(data, ensure_ascii=False))
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        if "/studyhub-sync" not in str(args[0] if args else ""):
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--content", default=os.environ.get("STUDYHUB_CONTENT"), help="folder with content/, slides/, materials/")
    a = ap.parse_args()
    global HOME
    if a.content:
        HOME = os.path.abspath(os.path.expanduser(a.content))
        if not os.path.isdir(HOME):
            sys.exit(f"--content folder not found: {HOME}")
    handler = functools.partial(Handler, directory=ROOT)
    import socket
    for host in ("127.0.0.1", "::1"):   # an old `python3 -m http.server` listens on :: and would not block 127.0.0.1
        try:
            socket.create_connection((host, a.port), timeout=0.5).close()
            sys.exit(f"Port {a.port} is busy - stop the other server (e.g. an old `python3 -m http.server`) or use --port.")
        except OSError:
            pass
    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), handler)
    except OSError:
        sys.exit(f"Port {a.port} is busy - stop the other server (e.g. an old `python3 -m http.server`) or use --port.")
    print(f"StudyHub: http://localhost:{a.port}/   (courses from {HOME})")
    print(f"Progress is saved to {SYNC_FILE}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
