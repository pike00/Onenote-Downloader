# Bake-off comparison — 20180830: Glycolysis and Pentose Phosphate Pathway

Outputs (local, gitignored):

`archive/_bakeoff/20180830-Glycolysis-and-Pentose-Phosphate-Pathway/`

| Path | HTML | PDF | Ink | Notes |
|------|------|-----|-----|-------|
| **A browser** | `A_browser/page.html` (~3.5 MB inline InkML) | `page.pdf` (~5.1 MB) | Canvas — **2617 traces** | Colors, highlighters, alignment look good |
| **B python** | `B_python/page.html` | `page.pdf` (~4.7 MB) | Raster overlay PNG (~267 KB) | Very similar to A; slightly softer strokes |
| **C opportunistic** | `C_opportunistic/page.html` | `page.pdf` (~4.5 MB) | Sidecar only (`inkml/ink.inkml`) | Slides/attachments archived; **no ink on page** |

## Checklist

- [x] Ink alignment vs OneNote (A) — visually close on sample region (PEP/ATP diagram)
- [x] Ink alignment vs OneNote (B) — same coordinate math; usable
- [x] Slides/images look correct (C) — yes; proves Stage‑1 archive
- [x] PDF usable / zoomable — tall single-page PDFs generated for all three
- [ ] Winner for full archive: A / B / C / hybrid — **your call**

## Observed

- Graph downloads put InkML in a **separate MIME part** after `</html>` — preprocess must parse multipart (fixed in bake-off).
- Asset URLs contain `users('…')` quotes; naive regex missed them (fixed); assets need `.png` extensions for Chromium.
- A and B both recover handwritten ink (black/blue/yellow) over lecture slides.
- C is the right bulk “archive now” path while ink pipeline is refined.
- Likely full-archive approach: **C for every page immediately**, **A (or B) for ink-heavy pages** / final archival PDFs.

## How to re-run

```bash
# once per machine
uv run --with playwright playwright install chromium

uv run archive_bakeoff/run_bakeoff.py
```
