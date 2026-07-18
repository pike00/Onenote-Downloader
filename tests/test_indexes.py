from pathlib import Path

from onenote_archive.catalog import PageRef
from onenote_archive.indexes import write_indexes


def _ref(
    *,
    notebook_name: str,
    section_name: str,
    page_title: str,
    page_id: str = "page-id",
) -> PageRef:
    return PageRef(
        notebook_id="nb-id",
        section_id="sec-id",
        page_id=page_id,
        notebook_name=notebook_name,
        section_name=section_name,
        page_title=page_title,
        page_html=Path("out/nb/sec/page.html"),
    )


def test_write_indexes_root_and_notebook(tmp_path):
    archive = tmp_path / "archive"
    nb_dir = archive / "Alpha-Notebook"
    page_a = nb_dir / "Section-One" / "First-Page"
    page_b = nb_dir / "Section-Two" / "Second-Page"
    page_a.mkdir(parents=True)
    page_b.mkdir(parents=True)
    (page_a / "page.html").write_text("<html></html>", encoding="utf-8")
    (page_b / "page.html").write_text("<html></html>", encoding="utf-8")

    refs = [
        _ref(notebook_name="Alpha Notebook", section_name="Section Two", page_title="Second Page", page_id="p2"),
        _ref(notebook_name="Alpha Notebook", section_name="Section One", page_title="First Page", page_id="p1"),
    ]
    dests = [page_b, page_a]

    write_indexes(archive, refs, dests)

    root = (archive / "index.html").read_text(encoding="utf-8")
    assert "OneNote Archive" in root
    assert 'href="Alpha-Notebook/index.html"' in root
    assert "Alpha Notebook" in root
    assert "<script>" not in root

    nb_index = (nb_dir / "index.html").read_text(encoding="utf-8")
    assert "Section One" in nb_index
    assert "Section Two" in nb_index
    assert 'href="Section-One/First-Page/page.html"' in nb_index
    assert 'href="Section-Two/Second-Page/page.html"' in nb_index
    assert nb_index.index("Section One") < nb_index.index("Section Two")
    assert nb_index.index("First Page") < nb_index.index("Second Page")


def test_write_indexes_escapes_html_in_titles(tmp_path):
    archive = tmp_path / "archive"
    notebook_name = 'Evil <script>alert("x")</script>'
    nb_dir = archive / "Evil-script-alert(-x-)-script"
    page_dir = nb_dir / "Sec" / "Page"
    page_dir.mkdir(parents=True)
    (page_dir / "page.html").write_text("<html></html>", encoding="utf-8")

    ref = _ref(
        notebook_name=notebook_name,
        section_name="Sec & Co",
        page_title='Page "quoted"',
    )
    write_indexes(archive, [ref], [page_dir])

    root = (archive / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in root
    assert "&lt;script&gt;" in root

    nb_index = (nb_dir / "index.html").read_text(encoding="utf-8")
    assert "Sec &amp; Co" in nb_index
    assert "Page &quot;quoted&quot;" in nb_index
