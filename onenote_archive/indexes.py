from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from onenote_archive.catalog import PageRef

_DISCOVERED_ID = "discovered"


def _is_discovered(ref: PageRef) -> bool:
    return ref.page_id == _DISCOVERED_ID


@dataclass
class _SectionGroup:
    display: str
    pages: list[tuple[PageRef, Path]] = field(default_factory=list)


@dataclass
class _NotebookGroup:
    display: str
    sections: dict[str, _SectionGroup] = field(default_factory=dict)


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

    by_notebook: dict[str, _NotebookGroup] = {}
    for ref, dest_dir in merged.values():
        rel = dest_dir.relative_to(archive_root)
        if len(rel.parts) < 3:
            continue
        nb_slug = rel.parts[0]
        nb_dir = archive_root / nb_slug
        sec_slug = dest_dir.relative_to(nb_dir).parts[0]

        if nb_slug not in by_notebook:
            by_notebook[nb_slug] = _NotebookGroup(display=ref.notebook_name)
        elif not _is_discovered(ref):
            by_notebook[nb_slug].display = ref.notebook_name

        nb_group = by_notebook[nb_slug]
        if sec_slug not in nb_group.sections:
            nb_group.sections[sec_slug] = _SectionGroup(display=ref.section_name)
        elif not _is_discovered(ref):
            nb_group.sections[sec_slug].display = ref.section_name

        nb_group.sections[sec_slug].pages.append((ref, dest_dir))

    root_items: list[str] = []
    for nb_slug in sorted(by_notebook, key=str.casefold):
        nb_group = by_notebook[nb_slug]
        notebook_name = nb_group.display
        nb_dir = archive_root / nb_slug
        nb_dir.mkdir(parents=True, exist_ok=True)

        section_blocks: list[str] = []
        for sec_slug in sorted(nb_group.sections, key=str.casefold):
            sec_group = nb_group.sections[sec_slug]
            section_name = sec_group.display
            section_entries = sorted(
                sec_group.pages,
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
