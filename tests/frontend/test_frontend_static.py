from __future__ import annotations

from pathlib import Path


STATIC_ROOT = Path(__file__).resolve().parents[2] / "src" / "pcad" / "api" / "static"


def test_frontend_static_entrypoints_exist() -> None:
    assert (STATIC_ROOT / "index.html").is_file()
    assert (STATIC_ROOT / "css" / "styles.css").is_file()
    assert (STATIC_ROOT / "js" / "main.js").is_file()
    assert (STATIC_ROOT / "landing" / "index.html").is_file()
    assert (STATIC_ROOT / "landing" / "styles.css").is_file()


def test_frontend_uses_native_modules_without_framework() -> None:
    index_html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    assert '<script type="module" src="/static/js/main.js"></script>' in index_html
    assert "cdn.jsdelivr.net/npm/marked@12/marked.min.js" in index_html
    forbidden = ["react", "vue", "svelte", "tailwind", "babel"]
    assert not any(token in index_html.lower() for token in forbidden)
    assert not (STATIC_ROOT.parents[3] / "package.json").exists()


def test_required_microcopy_is_present() -> None:
    import re

    raw = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            STATIC_ROOT / "index.html",
            STATIC_ROOT / "landing" / "index.html",
            STATIC_ROOT / "js" / "views" / "fake_note_modal.js",
            STATIC_ROOT / "js" / "views" / "conversation_panel.js",
        ]
    )
    # Strip inline HTML so emphasis tags inside microcopy (added by the
    # landing-page redesign) don't break literal substring checks.
    text = re.sub(r"<[^>]+>", "", raw)
    assert "Never prepare for a client call from scratch again." in text
    assert "Try the synthetic demo" in text
    assert "This public demo uses synthetic data only." in text
    assert "The public demo has reached its daily budget." in text


def test_landing_links_to_demo_route() -> None:
    landing_html = (STATIC_ROOT / "landing" / "index.html").read_text(encoding="utf-8")
    demo_html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")

    assert 'href="/demo"' in landing_html
    assert 'href="/"' in demo_html
