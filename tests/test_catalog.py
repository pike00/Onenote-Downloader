import json
from pathlib import Path

from onenote_archive.catalog import PageRef, iter_pages


def _write_tree(tmp_path: Path) -> None:
    nb_id, sec_id, page_id = "nb-1", "sec-1", "page-1"
    (tmp_path / "notebooks.json").write_text(
        json.dumps([{"id": nb_id, "displayName": "Demo NB"}]),
        encoding="utf-8",
    )
    nb_dir = tmp_path / nb_id
    nb_dir.mkdir()
    (nb_dir / "sections.json").write_text(
        json.dumps([{"id": sec_id, "displayName": "Sec"}]),
        encoding="utf-8",
    )
    sec_dir = nb_dir / sec_id
    sec_dir.mkdir()
    (sec_dir / "pages.json").write_text(
        json.dumps([{"id": page_id, "title": "Lecture 1"}]),
        encoding="utf-8",
    )
    page_dir = sec_dir / page_id
    page_dir.mkdir()
    (page_dir / "page.html").write_text(
        "<html><head><title>Lecture 1</title></head><body>hi</body></html>",
        encoding="utf-8",
    )


def test_iter_pages_resolves_names(tmp_path):
    _write_tree(tmp_path)
    refs = list(iter_pages(tmp_path))
    assert len(refs) == 1
    assert refs[0].notebook_name == "Demo NB"
    assert refs[0].section_name == "Sec"
    assert "Lecture" in refs[0].page_title


def test_iter_pages_skips_missing_page_html(tmp_path):
    _write_tree(tmp_path)
    (tmp_path / "nb-1" / "sec-1" / "page-1" / "page.html").unlink()
    assert list(iter_pages(tmp_path)) == []


def test_iter_pages_title_fallback_from_html(tmp_path):
    nb_id, sec_id, page_id = "nb-1", "sec-1", "page-1"
    (tmp_path / "notebooks.json").write_text(
        json.dumps([{"id": nb_id, "displayName": "Demo NB"}]),
        encoding="utf-8",
    )
    nb_dir = tmp_path / nb_id
    nb_dir.mkdir()
    (nb_dir / "sections.json").write_text(
        json.dumps([{"id": sec_id, "displayName": "Sec"}]),
        encoding="utf-8",
    )
    sec_dir = nb_dir / sec_id
    sec_dir.mkdir()
    (sec_dir / "pages.json").write_text(
        json.dumps([{"id": page_id}]),
        encoding="utf-8",
    )
    page_dir = sec_dir / page_id
    page_dir.mkdir()
    (page_dir / "page.html").write_text(
        "--bound\nContent-Type: text/html\n\n"
        "<html><head><title>From HTML Title</title></head><body></body></html>\n"
        "--bound--",
        encoding="utf-8",
    )
    refs = list(iter_pages(tmp_path))
    assert len(refs) == 1
    assert refs[0].page_title == "From HTML Title"


def test_page_ref_fields(tmp_path):
    _write_tree(tmp_path)
    ref = list(iter_pages(tmp_path))[0]
    assert isinstance(ref, PageRef)
    assert ref.notebook_id == "nb-1"
    assert ref.section_id == "sec-1"
    assert ref.page_id == "page-1"
    assert ref.page_html == tmp_path / "nb-1" / "sec-1" / "page-1" / "page.html"
