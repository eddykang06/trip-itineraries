"""Local preview with live reload: `python preview.py`, then open http://localhost:8000

Builds the site (including _draft files) into _site/, rebuilds whenever anything in
content/, templates/, trips.css or build.py changes, and the open page reloads itself.
Stop with Ctrl-C. Needs `pip install markdown`.
"""

import functools
import http.server
import importlib
import threading
import time
import traceback
from pathlib import Path

import build

PORT = 8000
WATCH = [build.CONTENT, build.TEMPLATES, build.ROOT / "trips.css", build.ROOT / "build.py", build.ROOT / "site.json"]

# Polls /.version once a second and reloads the page when it changes.
RELOAD = """<script>
(() => {
  let seen = null;
  setInterval(async () => {
    try {
      const v = await (await fetch("/.version", {cache: "no-store"})).text();
      if (seen !== null && v !== seen) location.reload();
      seen = v;
    } catch (e) {}
  }, 1000);
})();
</script>
</body>"""


def snapshot():
    files = []
    for w in WATCH:
        if w.is_file():
            files.append(w)
        elif w.is_dir():
            files += [f for f in w.rglob("*") if f.is_file()]
    return {str(f): f.stat().st_mtime for f in files}


def rebuild():
    importlib.reload(build)  # pick up edits to build.py too
    try:
        build.build_site(drafts=True)
        for page in build.OUT.rglob("*.html"):
            page.write_text(page.read_text(encoding="utf-8").replace("</body>", RELOAD, 1), encoding="utf-8")
        print(time.strftime("%H:%M:%S"), "rebuilt", flush=True)
    except SystemExit as e:  # build.fail(): show the message, keep serving
        build.OUT.mkdir(exist_ok=True)
        (build.OUT / "index.html").write_text(f"<pre>{e}</pre>{RELOAD}", encoding="utf-8")
        print(time.strftime("%H:%M:%S"), e, flush=True)
    except Exception:
        traceback.print_exc()
        return
    (build.OUT / ".version").write_text(str(time.time()), encoding="utf-8")


def watch():
    last = snapshot()
    while True:
        time.sleep(0.5)
        now = snapshot()
        if now != last:
            last = now
            time.sleep(0.2)  # let editors finish writing
            rebuild()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    rebuild()
    threading.Thread(target=watch, daemon=True).start()
    handler = functools.partial(Quiet, directory=str(build.OUT))
    print(f"Preview at http://localhost:{PORT}  (Ctrl-C to stop)", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
