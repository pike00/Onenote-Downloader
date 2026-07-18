# OneNote Full Archive — E2E Run Notes

**Date:** 2026-07-18  
**Branch:** `feature/onenote-full-archive`  
**Source:** `out/` (28 pages, notebook **01 SFI** partially synced)  
**Command:**

```bash
PYTHONPATH=. uv run onenote_archive/run_archive.py
```

**Runtime:** ~4.5 min (26 new renders + 2 incremental skips; Playwright PDF export).

## Results

| Outcome | Count |
|---------|------:|
| ok      | 26 |
| skipped | 2 |
| failed  | 0 |
| **Total processed** | **28** |

All 28 archived pages have both `page.html` and `page.pdf` (excluding `archive/_bakeoff/`).

### Skipped (incremental)

Pages already complete from prior run; `should_skip` saw existing HTML + PDF:

- `01-SFI/Biochemistry/20180830-Glycolysis-and-Pentose-Phosphate-Pathway`
- `01-SFI/Biochemistry/20180830-Oxidative-Phosphorylation-and-Glycolysis`

### failures.log

Not created — no render or PDF failures.

## Spot-check: Glycolysis

Path: `archive/01-SFI/Biochemistry/20180830-Glycolysis-and-Pentose-Phosphate-Pathway/`

| Check | Result |
|-------|--------|
| Ink canvas in HTML | `<canvas id="ink-canvas" … data-inkml-src="ink.inkml">` + inline `#inkml-data` + `ink_render.js` |
| Canvas boot path | `ink_render.js` waits for `DOMContentLoaded` when `document.readyState === "loading"` |
| `page.pdf` size | 5.1 MB (> 1 MB) |
| `ink.inkml` | 3.6 MB present |

## Indexes

- `archive/index.html` — lists notebook **01 SFI**
- `archive/01-SFI/index.html` — lists all 28 pages under Admin, Anatomy, Biochemistry

## Re-run

```bash
# Full incremental (skip pages with HTML + PDF already present)
PYTHONPATH=. uv run onenote_archive/run_archive.py

# Force rebuild everything
PYTHONPATH=. uv run onenote_archive/run_archive.py --force

# HTML only (skip Playwright PDF)
PYTHONPATH=. uv run onenote_archive/run_archive.py --skip-pdf

# Single notebook / page smoke
PYTHONPATH=. uv run onenote_archive/run_archive.py --notebook "SFI" --title Glycolysis --limit 1
```

Playwright Chromium is pulled automatically via the script's inline `uv` dependencies on first PDF export.

## Scope note

This run verified archival render on the **partial** Graph cache (~28 pages, one notebook). Full multi-notebook sync is tracked separately (Task 5).
