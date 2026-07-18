from pathlib import Path

from onenote_archive.preprocess import prepare_page
from onenote_archive.render_a import render_path_a


def test_prepare_page_writes_assets_and_inkml(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    raw = (
        "--bound\nContent-Type: text/html\n\n"
        "<html><head><title>Test Page</title></head>"
        '<body><img src="https://graph.microsoft.com/v1.0/me/onenote/resources/abc123/$value" /></body></html>\n'
        "--bound\nContent-Type: application/inkml+xml\n\n"
        '<inkml:ink xmlns:inkml="http://www.w3.org/2003/InkML"></inkml:ink>\n'
        "--bound--"
    )
    page_html = origin / "page.html"
    page_html.write_text(raw, encoding="utf-8")
    (origin / "abc123").write_bytes(b"\x89PNG\r\n\x1a\n")

    dest = tmp_path / "archive" / "Test-Page"
    prepared = prepare_page(page_html, dest)

    assert prepared.title == "Test Page"
    assert prepared.html_path == dest / "page.html"
    assert prepared.assets_dir == dest / "assets"
    assert (dest / "assets" / "abc123.png").is_file()
    assert prepared.inkml_path == dest / "ink.inkml"
    assert prepared.inkml_path.is_file()


def test_render_path_a_writes_html(tmp_path):
    dest = tmp_path / "page"
    dest.mkdir()
    prepared_html = dest / "page.html"
    prepared_html.write_text(
        "<html><body><p>slides</p></body></html>",
        encoding="utf-8",
    )
    from onenote_archive.preprocess import PreparedPage

    prepared = PreparedPage(
        html_path=prepared_html,
        width=1200,
        height=800,
        title="Test",
        inkml_path=None,
        assets_dir=dest / "assets",
    )
    result = render_path_a(prepared, dest, skip_pdf=True)
    assert result.ok
    assert result.html == dest / "page.html"
    assert result.html.read_text(encoding="utf-8").startswith("<html")
    assert (dest / "ink_render.js").is_file()


def test_render_path_a_injects_ink_canvas(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    raw = (
        "--bound\nContent-Type: text/html\n\n"
        "<html><head><title>Ink Page</title></head>"
        "<body><p>content</p></body></html>\n"
        "--bound\nContent-Type: application/inkml+xml\n\n"
        '<inkml:ink xmlns:inkml="http://www.w3.org/2003/InkML"></inkml:ink>\n'
        "--bound--"
    )
    page_html = origin / "page.html"
    page_html.write_text(raw, encoding="utf-8")

    dest = tmp_path / "archive" / "Ink-Page"
    prepared = prepare_page(page_html, dest)
    result = render_path_a(prepared, dest, skip_pdf=True)

    assert result.ok
    assert result.html == dest / "page.html"
    assert (dest / "ink_render.js").is_file()
    assert (dest / "ink.inkml").is_file()

    html = result.html.read_text(encoding="utf-8")
    assert 'id="ink-canvas"' in html
    assert 'id="inkml-data"' in html
    assert "ink_render.js" in html
    assert "<!-- inkml extracted; not rendered in this path -->" in html
