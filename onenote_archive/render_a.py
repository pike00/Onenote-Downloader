from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from onenote_archive.pdf_export import html_to_pdf, html_to_pdf_with_ink_wait
from onenote_archive.preprocess import PreparedPage, extract_inkml, remove_inkml


@dataclass
class RenderResult:
    ok: bool
    html: Path | None
    pdf: Path | None
    error: str | None


def render_path_a(
    prepared: PreparedPage,
    dest_dir: Path,
    *,
    skip_pdf: bool = False,
) -> RenderResult:
    """Write final path-A page.html (+ optional PDF) into dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        html = prepared.html_path.read_text(encoding="utf-8")
        inkml = extract_inkml(html)
        if not inkml and prepared.inkml_path and prepared.inkml_path.is_file():
            inkml = prepared.inkml_path.read_text(encoding="utf-8")
        width = prepared.width
        height = prepared.height

        js_src = Path(__file__).with_name("ink_render.js")
        shutil.copy2(js_src, dest_dir / "ink_render.js")

        canvas = ""
        if inkml:
            (dest_dir / "ink.inkml").write_text(inkml, encoding="utf-8")
            html = remove_inkml(html)
            escaped = inkml.replace("</script>", "<\\/script>")
            canvas = (
                f'<canvas id="ink-canvas" width="{width}" height="{height}" '
                f'data-inkml-src="ink.inkml" '
                f'style="position:absolute;left:0;top:0;z-index:50;pointer-events:none;"></canvas>'
                f'<script id="inkml-data" type="text/plain">{escaped}</script>'
                f'<script src="ink_render.js"></script>'
            )

        html = _inject_after_body(html, canvas)
        html = _ensure_body_size(html, width, height)

        page_html = dest_dir / "page.html"
        page_html.write_text(html, encoding="utf-8")

        pdf_path: Path | None = None
        if not skip_pdf:
            pdf_path = dest_dir / "page.pdf"
            if inkml:
                pdf_ok = html_to_pdf_with_ink_wait(page_html, pdf_path, width, height)
            else:
                pdf_ok = html_to_pdf(page_html, pdf_path, width, height)
            if not pdf_ok or not pdf_path.is_file():
                return RenderResult(
                    ok=False,
                    html=page_html,
                    pdf=None,
                    error="PDF export failed",
                )

        return RenderResult(ok=True, html=page_html, pdf=pdf_path, error=None)
    except Exception as exc:  # noqa: BLE001
        return RenderResult(ok=False, html=None, pdf=None, error=str(exc))


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
