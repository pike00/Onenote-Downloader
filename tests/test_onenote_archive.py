from pathlib import Path
from unittest.mock import patch

from onenote_archive.catalog import PageRef
from onenote_archive.preprocess import prepare_page
from onenote_archive.render_a import RenderResult, render_path_a
from onenote_archive.run_archive import (
    PAGE_ID_MARKER,
    _process_page,
    resolve_dest_dir,
)


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


def _page_ref(tmp_path: Path) -> PageRef:
    origin = tmp_path / "origin"
    origin.mkdir()
    page_html = origin / "page.html"
    page_html.write_text(
        "--bound\nContent-Type: text/html\n\n"
        "<html><head><title>Retry Page</title></head><body><p>hi</p></body></html>\n"
        "--bound--",
        encoding="utf-8",
    )
    return PageRef(
        notebook_id="nb",
        section_id="sec",
        page_id="page-abc12345",
        notebook_name="Notebook",
        section_name="Section",
        page_title="Retry Page",
        page_html=page_html,
    )


def test_process_page_writes_page_id_before_render(tmp_path):
    archive = tmp_path / "archive"
    ref = _page_ref(tmp_path)
    dest = archive / "Notebook" / "Section" / "Retry-Page"
    failures_log = archive / "failures.log"

    with patch(
        "onenote_archive.run_archive.render_path_a",
        return_value=RenderResult(ok=False, html=dest / "page.html", pdf=None, error="pdf failed"),
    ):
        outcome = _process_page(
            ref,
            dest,
            archive,
            skip_pdf=False,
            force=False,
            failures_log=failures_log,
        )

    assert outcome == "fail"
    assert (dest / PAGE_ID_MARKER).read_text(encoding="utf-8") == ref.page_id
    assert (dest / "page.html").is_file()


def test_resolve_dest_dir_reuses_marked_dir_on_retry(tmp_path):
    archive = tmp_path / "archive"
    ref = _page_ref(tmp_path)
    dest = archive / "Notebook" / "Section" / "Retry-Page"
    dest.mkdir(parents=True)
    (dest / "page.html").write_text("<html></html>", encoding="utf-8")
    (dest / PAGE_ID_MARKER).write_text(ref.page_id, encoding="utf-8")

    claimed: dict[Path, str] = {}
    resolved = resolve_dest_dir(archive, ref, claimed)

    assert resolved == dest
    assert claimed[dest] == ref.page_id
