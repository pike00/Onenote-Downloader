from __future__ import annotations

from collections import defaultdict
from html import escape
from pathlib import Path

from onenote_archive.catalog import PageRef
from onenote_archive.preprocess import sanitize_title

_DISCOVERED_ID = "discovered"


def discover_archived_pages(archive_root: Path) -> list[tuple[PageRef, Path]]:
    """Scan archive_root for notebook/section/page/page.html entries."""
    if not archive_root.is_dir():
        return []

    discovered: list[tuple[PageRef, Path]] = []
    for page_html in archive_root.rglob("page.html"):
        try:
            rel = page_html.relative_to(archive_root)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == "_bakeoff":
            continue
        if len(rel.parts) != 4:
            continue

        nb_slug, sec_slug, page_slug, _ = rel.parts
        dest_dir = page_html.parent
        discovered.append(
            (
                PageRef(
                    notebook_id=_DISCOVERED_ID,
                    section_id=_DISCOVERED_ID,
                    page_id=_DISCOVERED_ID,
                    notebook_name=nb_slug,
                    section_name=sec_slug,
                    page_title=page_slug,
                    page_html=page_html,
                ),
                dest_dir,
            )
        )
    return discovered

_STYLE = """
body { font-family: system-ui, -apple-system, sans-serif; max-width: 48rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
h2 { font-size: 1.1rem; margin-top: 1.75rem; margin-bottom: 0.35rem; color: #444; }
ul { padding-left: 1.25rem; margin: 0.25rem 0 0; }
li { margin: 0.2rem 0; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }
"""


def _html_document(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{escape(title)}</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def write_indexes(
    archive_root: Path,
    pages: list[PageRef],
    dest_dirs: list[Path],
) -> None:
    """Write archive index pages under archive_root."""
    if len(pages) != len(dest_dirs):
        raise ValueError("pages and dest_dirs must have the same length")

    merged: dict[Path, tuple[PageRef, Path]] = {}
    for ref, dest_dir in discover_archived_pages(archive_root):
        merged[dest_dir.resolve()] = (ref, dest_dir)
    for ref, dest_dir in zip(pages, dest_dirs, strict=True):
        merged[dest_dir.resolve()] = (ref, dest_dir)

    by_notebook: dict[str, list[tuple[PageRef, Path]]] = defaultdict(list)
    for ref, dest_dir in merged.values():
        by_notebook[ref.notebook_name].append((ref, dest_dir))

    root_items: list[str] = []
    for notebook_name in sorted(by_notebook, key=str.casefold):
        entries = by_notebook[notebook_name]
        nb_slug = sanitize_title(notebook_name)
        nb_dir = archive_root / nb_slug
        nb_dir.mkdir(parents=True, exist_ok=True)

        by_section: dict[str, list[tuple[PageRef, Path]]] = defaultdict(list)
        for ref, dest_dir in entries:
            by_section[ref.section_name].append((ref, dest_dir))

        section_blocks: list[str] = []
        for section_name in sorted(by_section, key=str.casefold):
            section_entries = sorted(
                by_section[section_name],
                key=lambda item: item[0].page_title.casefold(),
            )
            links = []
            for ref, dest_dir in section_entries:
                rel = dest_dir.relative_to(nb_dir).as_posix()
                page_href = f"{rel}/page.html"
                links.append(f'  <li><a href="{escape(page_href)}">{escape(ref.page_title)}</a></li>')
            section_blocks.append(
                f"<h2>{escape(section_name)}</h2>\n<ul>\n"
                + "\n".join(links)
                + "\n</ul>"
            )

        nb_body = f"<h1>{escape(notebook_name)}</h1>\n<p><a href=\"../index.html\">All notebooks</a></p>\n" + "\n".join(
            section_blocks
        )
        (nb_dir / "index.html").write_text(
            _html_document(notebook_name, nb_body),
            encoding="utf-8",
        )
        root_items.append(
            f'  <li><a href="{escape(f"{nb_slug}/index.html")}">{escape(notebook_name)}</a></li>'
        )

    root_body = "<h1>OneNote Archive</h1>\n<ul>\n" + "\n".join(root_items) + "\n</ul>"
    archive_root.mkdir(parents=True, exist_ok=True)
    (archive_root / "index.html").write_text(
        _html_document("OneNote Archive", root_body),
        encoding="utf-8",
    )
