from __future__ import annotations

from pathlib import Path

from archive_bakeoff.pdf_export import html_to_pdf
from archive_bakeoff.preprocess import (
    PreparedSource,
    extract_inkml,
    remove_inkml,
    rewrite_asset_prefix,
)
from onenote_archive.render_a import _inject_after_body

BANNER = """
<div id="bakeoff-banner" style="position:relative;z-index:9999;background:#1a1a1a;color:#f5f5f5;padding:10px 14px;font:14px/1.4 system-ui,sans-serif;">
  Path C — opportunistic archive (ink extracted, not rendered)
</div>
"""


def build_path_c(prepared: PreparedSource) -> Path:
    out_dir = prepared.page_dir / "C_opportunistic"
    ink_dir = out_dir / "inkml"
    out_dir.mkdir(parents=True, exist_ok=True)
    ink_dir.mkdir(parents=True, exist_ok=True)

    html = prepared.html_path.read_text(encoding="utf-8")
    inkml = extract_inkml(html)
    if inkml:
        (ink_dir / "ink.inkml").write_text(inkml, encoding="utf-8")
        html = remove_inkml(html)

    html = rewrite_asset_prefix(html, "../source")
    html = _inject_after_body(html, BANNER)

    page_html = out_dir / "page.html"
    page_html.write_text(html, encoding="utf-8")

    pdf_path = out_dir / "page.pdf"
    html_to_pdf(page_html, pdf_path, prepared.width, prepared.height)
    return out_dir
