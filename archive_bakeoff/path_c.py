from __future__ import annotations

from pathlib import Path

from archive_bakeoff.pdf_export import html_to_pdf
from archive_bakeoff.preprocess import (
    PreparedSource,
    extract_inkml,
    remove_inkml,
    rewrite_asset_prefix,
)


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
    # Inject banner after <body...>
    html = _inject_after_body(html, BANNER)

    page_html = out_dir / "page.html"
    page_html.write_text(html, encoding="utf-8")

    pdf_path = out_dir / "page.pdf"
    html_to_pdf(page_html, pdf_path, prepared.width, prepared.height)
    return out_dir


def _inject_after_body(html: str, snippet: str) -> str:
    lower = html.lower()
    idx = lower.find("<body")
    if idx < 0:
        return snippet + html
    gt = html.find(">", idx)
    if gt < 0:
        return snippet + html
    return html[: gt + 1] + snippet + html[gt + 1 :]


def _ensure_body_size(html: str, width: int, height: int) -> str:
    """Merge width/min-height into the existing body style attribute."""
    import re

    extra = f"width:{width}px;min-height:{height}px;margin:0;position:relative;"
    updated, n = re.subn(
        r'(?i)<body([^>]*)\sstyle="([^"]*)"',
        lambda m: f'<body{m.group(1)} style="{extra}{m.group(2)}"',
        html,
        count=1,
    )
    if n:
        return updated
    return re.sub(
        r"(?i)<body\b",
        f'<body style="{extra}"',
        html,
        count=1,
    )
