"""Render the deployable static pages into public/ (the folder Vercel serves).

    .venv/bin/python scripts/build_site.py        # after changing a template; commit the result

The website is one set of templates. The Lambda (sam local) renders them live; a static host can't run the Lambda, so
these four pages are pre-rendered from the SAME templates and committed, and Vercel serves public/ as it is (see
vercel.json): push to GitHub and the site updates. `tests/test_site_fresh.py` fails if a template changed but this
wasn't re-run, so the deployed pages can't drift from the source.

  public/index.html                          the landing page (its /api calls are answered from the recording by replay-shim.js)
  public/demo.html                           the live demo: the recorded dashboard and the recorded conversations (public/static/recording.json)
  public/dashboard-snapshot-aquaspin.html   the real dashboard UI over recorded API responses, read-only (framed on the demo page)
The recording itself comes from scripts/record_playback.py (run against a live stack), never from this script.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import (
    pages,
)

PUBLIC = ROOT / "public"
SHIM = '<script src="/static/replay-shim.js"></script>\n  '
NOTE_CSS = ('<style>.static-note{background:#0a2a52;color:#cfe4ff;font:500 12.5px/1.4 Inter,system-ui,sans-serif;text-align:center;'
            'padding:6px 14px;border-radius:0 0 12px 12px}</style>')


def landing() -> str:
    """The static landing page: same markup, but the status chips and the file checker read the recording."""
    h = pages.landing()
    assert '<script src="/static/landing.js"></script>' in h
    return h.replace('<script src="/static/landing.js"></script>', SHIM + '<script src="/static/landing.js"></script>')


def snapshot(brand: str) -> str:
    """The dashboard UI over recorded data: no sign-in, no navigation out of the frame, a one-line note."""
    h = pages.dashboard(brand)
    h = re.sub(r'\s*<nav class="db-nav".*?</nav>', "", h, flags=re.DOTALL)
    h = h.replace('<script src="/static/dashboard.js"></script>', SHIM + '<script src="/static/dashboard.js"></script>')
    note = f'{NOTE_CSS}<div class="static-note">Recorded snapshot: read-only. Every value was captured from the running dashboard.</div>'
    return h.replace('<body class="db">', '<body class="db">\n' + note, 1)


def render_all() -> dict[str, str]:
    return {
        "index.html": landing(),
        "demo.html": pages.demo(),
        "dashboard-snapshot-aquaspin.html": snapshot("aquaspin"),
    }


def main() -> int:
    if not (PUBLIC / "static" / "recording.json").exists():
        print("no recording: run scripts/record_playback.py against a running stack first", file=sys.stderr)
        return 1
    for name, html in render_all().items():
        (PUBLIC / name).write_text(html)
        print(f"wrote public/{name} ({len(html) // 1000} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
