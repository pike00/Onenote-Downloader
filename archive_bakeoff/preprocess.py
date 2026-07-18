from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

# Graph URLs include users('guid') — do not stop at quotes in the path.
RESOURCE_RE = re.compile(
    r"https://graph\.microsoft\.com/.+?/resources/([^/\"'\s]+)/\$value",
    re.IGNORECASE,
)


def parse_multipart(raw: str) -> tuple[str, str | None]:
    """Parse Graph multipart page download into (html, inkml_or_none).

    OneNote Graph returns `text/html` and often a sibling
    `application/inkml+xml` part after ``</html>``.
    """
    if not raw.lstrip().startswith("--"):
        html = _extract_html_document(raw)
        ink = extract_inkml(raw)
        return html, ink

    boundary = raw.lstrip().splitlines()[0].strip()
    if not boundary.startswith("--"):
        return _extract_html_document(raw), extract_inkml(raw)

    parts = raw.split(boundary)
    html_doc: str | None = None
    inkml_doc: str | None = None
    for part in parts:
        part = part.strip()
        if not part or part == "--":
            continue
        headers, _, body = part.partition("\n\n")
        if not body:
            headers, _, body = part.partition("\r\n\r\n")
        headers_l = headers.lower()
        body = body.strip()
        if "text/html" in headers_l:
            html_doc = _extract_html_document(body)
        elif "inkml" in headers_l or body.lstrip().startswith("<?xml") or "<inkml:ink" in body:
            # Drop XML declaration for embedding friendliness
            body = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", body)
            if "<inkml:ink" in body or re.search(r"<ink\b", body):
                inkml_doc = body.strip()

    if html_doc is None:
        html_doc = _extract_html_document(raw)
    if inkml_doc is None:
        inkml_doc = extract_inkml(raw)
    return html_doc, inkml_doc


def _extract_html_document(text: str) -> str:
    match = re.search(r"(?is)<html\b.*</html>", text)
    if match:
        return match.group(0).strip()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("<"):
            return "\n".join(lines[i:]).strip()
    return text.strip()


def strip_multipart(html: str) -> str:
    """Remove Graph multipart MIME wrapper; return the HTML document only."""
    doc, _ink = parse_multipart(html)
    return doc


def sanitize_title(title: str) -> str:
    title = title.strip()
    title = re.sub(r"[:/\\?%*|\"<>]+", "-", title)
    title = re.sub(r"\s+", "-", title)
    title = re.sub(r"-{2,}", "-", title)
    title = title.strip("-.")
    return title or "untitled-page"


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return "untitled-page"


def content_extents(html: str) -> tuple[int, int]:
    """Return (width, height) CSS px covering absolutely positioned content."""
    max_right = 0
    max_bottom = 0
    for tag in BeautifulSoup(html, "html.parser").find_all(True):
        style = tag.get("style") or ""
        if "position:absolute" not in style.replace(" ", ""):
            # still allow spaced style
            if "absolute" not in style:
                continue
        left = _style_px(style, "left") or 0
        top = _style_px(style, "top") or 0
        width = _attr_int(tag, "width") or _style_px(style, "width") or 0
        height = _attr_int(tag, "height") or _style_px(style, "height") or 0
        max_right = max(max_right, int(left + width))
        max_bottom = max(max_bottom, int(top + height))
    return max(max_right, 1200), max(max_bottom, 800)


def _style_px(style: str, prop: str) -> float | None:
    match = re.search(rf"{prop}\s*:\s*(-?\d+(?:\.\d+)?)px", style, re.I)
    return float(match.group(1)) if match else None


def _attr_int(tag, name: str) -> int | None:
    val = tag.get(name)
    if val is None:
        return None
    try:
        return int(float(str(val)))
    except ValueError:
        return None


def resource_id_from_url(url: str) -> str | None:
    match = RESOURCE_RE.search(url)
    return match.group(1) if match else None


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
    # Prefer a page that actually contains InkML
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        if "inkml:ink" in text.lower() or "<inkml:ink" in text:
            return page
    return pages[0]


def prepare_source(page_html_path: Path, bakeoff_root: Path) -> PreparedSource:
    raw = page_html_path.read_text(encoding="utf-8", errors="replace")
    html, inkml = parse_multipart(raw)
    title = extract_title(html)
    slug = sanitize_title(title)
    page_dir = bakeoff_root / slug
    source_dir = page_dir / "source"
    assets_dir = source_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    origin_dir = page_html_path.parent

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        _rewrite_resource_attrs(tag, origin_dir, assets_dir)

    rewritten = str(soup)
    # Persist InkML beside HTML and embed before </body> for path extractors
    if inkml:
        (source_dir / "ink.inkml").write_text(inkml, encoding="utf-8")
        lower = rewritten.lower()
        body_close = lower.rfind("</body>")
        if body_close >= 0:
            rewritten = rewritten[:body_close] + "\n" + inkml + "\n" + rewritten[body_close:]
        else:
            rewritten = rewritten + "\n" + inkml

    width, height = content_extents(rewritten)
    html_path = source_dir / "page.html"
    html_path.write_text(rewritten, encoding="utf-8")

    return PreparedSource(
        page_dir=page_dir,
        source_dir=source_dir,
        title=title,
        html_path=html_path,
        width=width,
        height=height,
    )


def _rewrite_resource_attrs(tag, origin_dir: Path, assets_dir: Path) -> None:
    # Prefer full-res when available
    fullres = tag.get("data-fullres-src")
    src = tag.get("src")
    data = tag.get("data")

    def localize(url: str | None, mime_hint: str | None = None) -> str | None:
        if not url:
            return None
        rid = resource_id_from_url(url)
        if not rid:
            return None
        src_file = origin_dir / rid
        ext = _ext_for_mime(mime_hint) or _ext_from_magic(src_file)
        dest_name = f"{rid}{ext}" if ext and not rid.endswith(ext) else rid
        dest = assets_dir / dest_name
        if src_file.is_file() and not dest.exists():
            shutil.copy2(src_file, dest)
        if dest.exists():
            return f"assets/{dest_name}"
        return None

    mime = tag.get("data-fullres-src-type") or tag.get("data-src-type") or tag.get("type")
    if fullres:
        local = localize(fullres, mime)
        if local:
            tag["src"] = local
            tag["data-fullres-src"] = local
        elif src:
            local_src = localize(src, tag.get("data-src-type") or mime)
            if local_src:
                tag["src"] = local_src
    elif src:
        local_src = localize(src, tag.get("data-src-type") or mime)
        if local_src:
            tag["src"] = local_src

    if data:
        local_data = localize(data, tag.get("type") or mime)
        if local_data:
            tag["data"] = local_data


def extract_inkml(html: str) -> str | None:
    match = re.search(
        r"(?is)<inkml:ink\b.*?</inkml:ink>|<ink\b[^>]*xmlns:inkml=[^>]*>.*?</ink>",
        html,
    )
    return match.group(0) if match else None


def remove_inkml(html: str) -> str:
    return re.sub(
        r"(?is)<inkml:ink\b.*?</inkml:ink>|<ink\b[^>]*xmlns:inkml=[^>]*>.*?</ink>",
        "<!-- inkml extracted; not rendered in this path -->",
        html,
        count=1,
    )


def rewrite_asset_prefix(html: str, prefix: str) -> str:
    """Change assets/… references to prefix/assets/… (prefix like ../source)."""
    return html.replace('src="assets/', f'src="{prefix}/assets/').replace(
        'data="assets/', f'data="{prefix}/assets/'
    ).replace(
        'data-fullres-src="assets/', f'data-fullres-src="{prefix}/assets/'
    )


def himetric_to_px(value: float, dpi: float = 96.0) -> float:
    return value * dpi / 2540.0


def _ext_for_mime(mime: str | None) -> str:
    if not mime:
        return ""
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }
    return mapping.get(mime.lower().split(";")[0].strip(), "")


def _ext_from_magic(path: Path) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as fh:
        head = fh.read(8)
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"%PDF"):
        return ".pdf"
    if head.startswith(b"GIF8"):
        return ".gif"
    return ""
