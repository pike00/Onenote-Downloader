from __future__ import annotations

from pathlib import Path


def html_to_pdf(html_path: Path, pdf_path: Path, width_px: int, height_px: int) -> bool:
    """Render a local HTML file to a single tall PDF via Playwright.

    Returns True on success, False if Playwright/Chromium unavailable.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed; skipping PDF for", html_path)
        return False

    html_uri = html_path.resolve().as_uri()
    # CSS pixels → inches at 96 DPI
    width_in = max(width_px, 800) / 96.0
    height_in = max(height_px, 800) / 96.0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": min(width_px, 1600), "height": 900})
            page.goto(html_uri, wait_until="networkidle")
            page.wait_for_timeout(500)
            # Prefer measured document height when larger
            measured = page.evaluate(
                """() => {
                    const b = document.body;
                    const e = document.documentElement;
                    return Math.max(
                        b.scrollHeight, b.offsetHeight,
                        e.clientHeight, e.scrollHeight, e.offsetHeight
                    );
                }"""
            )
            if measured and measured > height_px:
                height_in = measured / 96.0
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            page.pdf(
                path=str(pdf_path),
                width=f"{width_in}in",
                height=f"{height_in}in",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
        return True
    except Exception as exc:  # noqa: BLE001 — bake-off should continue other paths
        print(f"PDF export failed for {html_path}: {exc}")
        return False
