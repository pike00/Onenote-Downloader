#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4>=4.12",
#     "pillow>=10.0",
#     "playwright>=1.40",
# ]
# ///
"""Run A/B/C archival bake-off on one sample OneNote page."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from archive_bakeoff.path_a import build_path_a
from archive_bakeoff.path_b import build_path_b
from archive_bakeoff.path_c import build_path_c
from archive_bakeoff.preprocess import find_sample_page, prepare_source


def write_compare_stub(page_dir: Path, title: str) -> None:
    path = page_dir / "COMPARE.md"
    docs_copy = ROOT / "docs" / "projects" / "onenote-archive-bakeoff" / "COMPARE.md"
    text = f"""# Bake-off comparison — {title}

Open each `page.html` in a browser (and PDFs if present):

| Path | HTML | PDF | Notes |
|------|------|-----|-------|
| A browser | `A_browser/page.html` | `A_browser/page.pdf` | Canvas InkML |
| B python | `B_python/page.html` | `B_python/page.pdf` | Raster overlay |
| C opportunistic | `C_opportunistic/page.html` | `C_opportunistic/page.pdf` | No ink render |

## Checklist

- [ ] Ink alignment vs OneNote (A)
- [ ] Ink alignment vs OneNote (B)
- [ ] Slides/images look correct (C)
- [ ] PDF usable / zoomable
- [ ] Winner for full archive: A / B / C / hybrid

## Observed

_(fill after visual review)_

"""
    path.write_text(text, encoding="utf-8")
    docs_copy.parent.mkdir(parents=True, exist_ok=True)
    docs_copy.write_text(text, encoding="utf-8")


def main() -> int:
    out_dir = ROOT / "out"
    bakeoff_root = ROOT / "archive" / "_bakeoff"
    bakeoff_root.mkdir(parents=True, exist_ok=True)

    sample = find_sample_page(out_dir)
    print(f"Sample page: {sample}")
    prepared = prepare_source(sample, bakeoff_root)
    print(f"Prepared source: {prepared.source_dir}")
    print(f"Title: {prepared.title} ({prepared.width}x{prepared.height}px)")

    print("Building path C…")
    c_dir = build_path_c(prepared)
    print(f"  → {c_dir}")

    print("Building path B…")
    b_dir = build_path_b(prepared)
    print(f"  → {b_dir}")

    print("Building path A…")
    a_dir = build_path_a(prepared)
    print(f"  → {a_dir}")

    write_compare_stub(prepared.page_dir, prepared.title)
    print(f"Done. Review: {prepared.page_dir}")
    print(f"Compare notes: {prepared.page_dir / 'COMPARE.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
