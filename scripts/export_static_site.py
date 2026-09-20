"""Build the static site (site/) for Vercel (or any static host) from the same templates and assets the Lambda serves,
plus the recording made by scripts/record_playback.py. No backend is needed to serve it.

    .venv/bin/python scripts/export_static_site.py       # -> site/   (commit it; deploy with root directory "site")

What the static site contains, and what it is honest about:
  /          the landing page (rendered by the real template); its two demo buttons point to the recorded run and "run it yourself"
  /sandbox   the recorded run: eight customers replayed from site_src/recording.json (real transcripts, not generated)
  /dashboard/aquaspin, /dashboard/arcticair   the real dashboard UI over recorded API responses (read-only; the second shows Cedar's real refusal)
  /run       how to run the real thing
public/static/replay-shim.js answers the few /api calls those pages make from the recording; every place that shows
recorded data says so.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AFTERCARE_STORE", "file")

from src import pages  # noqa: E402  (renders the real templates; needs no running services)

SRC = ROOT / "site_src" / "recording.json"
OUT = ROOT / "site"
NOTE = ('<div class="static-note">A static copy of the site. The demo here is a <b>recording</b> of the real run; '
        'to run it live, see <a href="/run">Run it yourself</a>.</div>')
NOTE_CSS = ('<style>.static-note{position:relative;z-index:300;background:#0a2a52;color:#cfe4ff;font:500 13px/1.4 Inter,system-ui,sans-serif;'
            'text-align:center;padding:8px 16px}.static-note a{color:#8ec0ff}body.db .static-note{border-radius:0 0 14px 14px}</style>')
SHIM = '<script src="/static/replay-shim.js"></script>\n'


def write(rel: str, html: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html)


def redirect(target: str) -> str:
    return f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{target}"><a href="{target}">Continue</a>'


def landing() -> str:
    h = pages.landing()
    swaps = [
        ('<a class="l-pill l-pill-sm l-pill-alt" href="/sandbox">Sandbox</a>', '<a class="l-pill l-pill-sm l-pill-alt" href="/run">Run it</a>'),
        ('<a class="l-pill l-pill-sm" href="/demo">Live demo</a>', '<a class="l-pill l-pill-sm" href="/sandbox">Recorded run</a>'),
        ('<a class="l-pill" href="/demo">Live demo</a>', '<a class="l-pill" href="/sandbox">Watch the recorded run</a>'),
        ('<a class="l-pill l-pill-alt" href="/sandbox">Sandbox demo</a>', '<a class="l-pill l-pill-alt" href="/run">Run it yourself</a>'),
        ('<a class="l-pill l-pill-lg" href="/demo">Open live demo</a>', '<a class="l-pill l-pill-lg" href="/sandbox">Watch the recorded run</a>'),
        ('<a class="l-pill l-pill-lg l-pill-alt" href="/sandbox">Open sandbox demo</a>', '<a class="l-pill l-pill-lg l-pill-alt" href="/run">Run it yourself</a>'),
        ('<a href="/demo">Live demo</a> · <a href="/sandbox">Sandbox demo</a>', '<a href="/sandbox">Recorded run</a> · <a href="/run">Run it yourself</a>'),
        ("Load an order file, message as a customer, and watch both sides of the conversation, including a person taking over. No sign-up, no download.",
         "Watch a recorded run: eight customers, the agent at work, and a person taking over. Then run it yourself."),
    ]
    for a, b in swaps:
        assert a in h, f"landing changed; update the export: {a[:60]}"
        h = h.replace(a, b)
    h = h.replace('<script src="/static/landing.js"></script>', SHIM + '<script src="/static/landing.js"></script>')
    return h.replace("<body>", "<body>\n" + NOTE_CSS + NOTE, 1)


def dashboard(brand: str) -> str:
    h = pages.dashboard(brand)
    h = h.replace('<script src="/static/dashboard.js"></script>', SHIM + '<script src="/static/dashboard.js"></script>')
    h = h.replace('<body class="db">', '<body class="db">\n' + NOTE_CSS + NOTE, 1)
    return re.sub(r'<a href="/sandbox">Sandbox</a>', '<a href="/sandbox">Recorded run</a>', h)


def main() -> int:
    if not SRC.exists():
        print("no recording: run scripts/record_playback.py against a running stack first", file=sys.stderr)
        return 1
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "public" / "static", OUT / "static")
    shutil.copy(SRC, OUT / "static" / "recording.json")

    write("index.html", landing())
    write("sandbox/index.html", (ROOT / "scripts" / "site_templates" / "playback.html").read_text())
    write("run/index.html", (ROOT / "scripts" / "site_templates" / "run.html").read_text())
    write("demo/index.html", redirect("/sandbox"))
    for brand in ("aquaspin", "arcticair"):
        write(f"dashboard/{brand}/index.html", dashboard(brand))
    write("dashboard/index.html", redirect("/dashboard/aquaspin"))
    write("404.html", redirect("/"))
    (OUT / "vercel.json").write_text(json.dumps({"cleanUrls": True, "trailingSlash": False}, indent=2) + "\n")
    (OUT / "README.txt").write_text("Generated by scripts/export_static_site.py. Deploy this folder as the Vercel project root (no build command, no output directory).\n")
    n = sum(1 for _ in OUT.rglob("*") if _.is_file())
    print(f"wrote {OUT} ({n} files, {sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()) // 1000} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
