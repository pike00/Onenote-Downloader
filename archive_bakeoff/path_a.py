from __future__ import annotations

import shutil
from pathlib import Path

from archive_bakeoff.pdf_export import html_to_pdf, html_to_pdf_with_ink_wait
from archive_bakeoff.preprocess import (
    PreparedSource,
    extract_inkml,
    remove_inkml,
    rewrite_asset_prefix,
)
from onenote_archive.render_a import _ensure_body_size, _inject_after_body

BANNER = """
<div id="bakeoff-banner" style="position:relative;z-index:9999;background:#1e3a5f;color:#f5f5f5;padding:10px 14px;font:14px/1.4 system-ui,sans-serif;">
  Path A — browser canvas ink
</div>
"""


def build_path_a(prepared: PreparedSource) -> Path:
    out_dir = prepared.page_dir / "A_browser"
    out_dir.mkdir(parents=True, exist_ok=True)

    html = prepared.html_path.read_text(encoding="utf-8")
    inkml = extract_inkml(html)
    width = prepared.width
    height = prepared.height

    js_src = Path(__file__).with_name("ink_render.js")
    shutil.copy2(js_src, out_dir / "ink_render.js")

    canvas = ""
    if inkml:
        (out_dir / "ink.inkml").write_text(inkml, encoding="utf-8")
        html = remove_inkml(html)
        escaped = inkml.replace("</script>", "<\\/script>")
        canvas = (
            f'<canvas id="ink-canvas" width="{width}" height="{height}" '
            f'data-inkml-src="ink.inkml" '
            f'style="position:absolute;left:0;top:0;z-index:50;pointer-events:none;"></canvas>'
            f'<script id="inkml-data" type="text/plain">{escaped}</script>'
            f'<script src="ink_render.js"></script>'
        )
    else:
        print("Path A: no InkML on this page; writing slides-only HTML")

    html = rewrite_asset_prefix(html, "../source")
    html = _inject_after_body(html, BANNER + canvas)
    html = _ensure_body_size(html, width, height)

    page_html = out_dir / "page.html"
    page_html.write_text(html, encoding="utf-8")

    if inkml:
        html_to_pdf_with_ink_wait(page_html, out_dir / "page.pdf", width, height)
    else:
        html_to_pdf(page_html, out_dir / "page.pdf", width, height)
    return out_dir
