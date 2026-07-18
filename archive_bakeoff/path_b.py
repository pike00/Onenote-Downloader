from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from archive_bakeoff.inkml_common import parse_inkml, rgba_from_brush
from archive_bakeoff.pdf_export import html_to_pdf
from archive_bakeoff.preprocess import (
    PreparedSource,
    extract_inkml,
    remove_inkml,
    rewrite_asset_prefix,
)
from archive_bakeoff.path_c import _ensure_body_size, _inject_after_body

BANNER = """
<div id="bakeoff-banner" style="position:relative;z-index:9999;background:#0b3d2e;color:#f5f5f5;padding:10px 14px;font:14px/1.4 system-ui,sans-serif;">
  Path B — Python raster ink overlay
</div>
"""


def build_path_b(prepared: PreparedSource) -> Path:
    out_dir = prepared.page_dir / "B_python"
    out_dir.mkdir(parents=True, exist_ok=True)

    html = prepared.html_path.read_text(encoding="utf-8")
    inkml = extract_inkml(html)
    width = prepared.width
    height = prepared.height
    overlay_tag = ""

    if inkml:
        ink = parse_inkml(inkml)
        width = max(width, int(ink.max_x) + 40)
        height = max(height, int(ink.max_y) + 40)
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for trace in ink.traces:
            if len(trace.points) < 2:
                continue
            color = rgba_from_brush(trace.brush)
            width_px = max(1, int(round(trace.brush.width_px)))
            draw.line(trace.points, fill=color, width=width_px, joint="curve")
        overlay_path = out_dir / "ink_overlay.png"
        overlay.save(overlay_path)
        overlay_tag = (
            f'<img src="ink_overlay.png" alt="ink overlay" width="{width}" height="{height}" '
            f'style="position:absolute;left:0;top:0;z-index:50;pointer-events:none;" />'
        )
        html = remove_inkml(html)
    else:
        print("Path B: no InkML on this page; writing slides-only HTML")

    html = rewrite_asset_prefix(html, "../source")
    html = _inject_after_body(html, BANNER + overlay_tag)
    html = _ensure_body_size(html, width, height)

    page_html = out_dir / "page.html"
    page_html.write_text(html, encoding="utf-8")
    html_to_pdf(page_html, out_dir / "page.pdf", width, height)
    return out_dir
