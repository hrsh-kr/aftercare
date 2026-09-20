"""The pre-rendered pages Vercel serves (public/*.html) must match what the templates render today, so that
pushing to GitHub never deploys a stale page. If this fails: .venv/bin/python scripts/build_site.py and commit."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_site


def test_pages_are_up_to_date():
    stale = [n for n, html in build_site.render_all().items() if not (build_site.PUBLIC / n).exists() or (build_site.PUBLIC / n).read_text() != html]
    assert not stale, f"stale or missing: {stale}. Run scripts/build_site.py and commit."


def test_the_recording_is_present_and_complete():
    import json
    rec = json.loads((build_site.PUBLIC / "static" / "recording.json").read_text())
    assert len(rec["personas"]) == 8 and rec["dashboard"]["aquaspin"]["tickets"]


def test_deployed_pages_contain_no_local_urls_or_secrets():
    for n in build_site.render_all():
        text = (build_site.PUBLIC / n).read_text()
        for bad in ("host.docker.internal", "local-dev-only", "aqua-manager", "arctic-manager", "aqua-agent"):
            assert bad not in text, f"{n} contains {bad}"


if __name__ == "__main__":
    fails = 0
    for name, fn in [(n, f) for n, f in list(globals().items()) if n.startswith("test_")]:
        try:
            fn(); print("PASS ", name)
        except AssertionError as e:
            fails += 1; print("FAIL ", name, e)
    print("all passed" if not fails else f"{fails} failed")
    sys.exit(1 if fails else 0)
