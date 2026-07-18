from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from onenote_archive.preprocess import extract_title, strip_multipart


@dataclass
class PageRef:
    notebook_id: str
    section_id: str
    page_id: str
    notebook_name: str
    section_name: str
    page_title: str
    page_html: Path


def iter_pages(out_dir: Path) -> Iterator[PageRef]:
    notebooks_path = out_dir / "notebooks.json"
    if not notebooks_path.is_file():
        return

    notebooks = json.loads(notebooks_path.read_text(encoding="utf-8"))

    for nb in notebooks:
        nb_id = nb["id"]
        nb_name = nb.get("displayName") or nb_id

        sections_path = out_dir / nb_id / "sections.json"
        if not sections_path.is_file():
            continue

        sections = json.loads(sections_path.read_text(encoding="utf-8"))

        for sec in sections:
            sec_id = sec["id"]
            sec_name = sec.get("displayName") or sec_id

            pages_path = out_dir / nb_id / sec_id / "pages.json"
            if not pages_path.is_file():
                continue

            pages = json.loads(pages_path.read_text(encoding="utf-8"))

            for page in pages:
                page_id = page["id"]
                page_html = out_dir / nb_id / sec_id / page_id / "page.html"
                if not page_html.is_file():
                    continue

                page_title = page.get("title")
                if not page_title:
                    raw = page_html.read_text(encoding="utf-8", errors="replace")
                    page_title = extract_title(strip_multipart(raw))

                yield PageRef(
                    notebook_id=nb_id,
                    section_id=sec_id,
                    page_id=page_id,
                    notebook_name=nb_name,
                    section_name=sec_name,
                    page_title=page_title,
                    page_html=page_html,
                )
