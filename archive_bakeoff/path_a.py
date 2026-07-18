from __future__ import annotations

import shutil
from pathlib import Path

from archive_bakeoff.pdf_export import html_to_pdf
from archive_bakeoff.preprocess import (
    PreparedSource,
    extract_inkml,
    remove_inkml,
    rewrite_asset_prefix,
)
from archive_bakeoff.path_c import _ensure_body_size, _inject_after_body

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
        # Inline InkML so file:// pages do not depend on fetch()
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
        _pdf_with_ink_wait(page_html, out_dir / "page.pdf", width, height)
    else:
        html_to_pdf(page_html, out_dir / "page.pdf", width, height)
    return out_dir


def _pdf_with_ink_wait(html_path: Path, pdf_path: Path, width_px: int, height_px: int) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return html_to_pdf(html_path, pdf_path, width_px, height_px)

    html_uri = html_path.resolve().as_uri()
    width_in = max(width_px, 800) / 96.0
    height_in = max(height_px, 800) / 96.0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": min(width_px, 1600), "height": 900})
            page.goto(html_uri, wait_until="networkidle")
            page.wait_for_function(
                "() => document.getElementById('ink-canvas')?.dataset?.inkReady === '1'",
                timeout=60000,
            )
            measured = page.evaluate(
                """() => Math.max(
                    document.body.scrollHeight, document.documentElement.scrollHeight
                )"""
            )
            if measured and measured > height_px:
                height_in = measured / 96.0
            page.pdf(
                path=str(pdf_path),
                width=f"{width_in}in",
                height=f"{height_in}in",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Path A PDF failed: {exc}; falling back")
        return html_to_pdf(html_path, pdf_path, width_px, height_px)
