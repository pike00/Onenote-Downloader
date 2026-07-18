from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from onenote_archive.preprocess import (
    content_extents,
    extract_inkml,
    extract_title,
    himetric_to_px,
    parse_multipart,
    prepare_page,
    remove_inkml,
    resource_id_from_url,
    rewrite_asset_prefix,
    sanitize_title,
    strip_multipart,
)

__all__ = [
    "PreparedSource",
    "content_extents",
    "extract_inkml",
    "extract_title",
    "find_sample_page",
    "himetric_to_px",
    "parse_multipart",
    "prepare_page",
    "prepare_source",
    "remove_inkml",
    "resource_id_from_url",
    "rewrite_asset_prefix",
    "sanitize_title",
    "strip_multipart",
]


@dataclass
class PreparedSource:
    page_dir: Path
    source_dir: Path
    title: str
    html_path: Path
    width: int
    height: int


def find_sample_page(out_dir: Path, title_substr: str = "Glycolysis") -> Path:
    pages = sorted(out_dir.rglob("page.html"))
    if not pages:
        raise FileNotFoundError(f"No page.html under {out_dir}")
    needle = title_substr.lower()
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        title = extract_title(strip_multipart(text)).lower()
        if needle in title:
            return page
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        if "inkml:ink" in text.lower() or "<inkml:ink" in text:
            return page
    return pages[0]


def prepare_source(page_html_path: Path, bakeoff_root: Path) -> PreparedSource:
    """Bake-off layout: ``<slug>/source/page.html`` + ``source/assets/``."""
    title = extract_title(strip_multipart(page_html_path.read_text(encoding="utf-8", errors="replace")))
    slug = sanitize_title(title)
    page_dir = bakeoff_root / slug
    source_dir = page_dir / "source"
    prepared = prepare_page(page_html_path, source_dir)
    return PreparedSource(
        page_dir=page_dir,
        source_dir=source_dir,
        title=prepared.title,
        html_path=prepared.html_path,
        width=prepared.width,
        height=prepared.height,
    )
