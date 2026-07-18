# OneNote Archive Bake-off Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render one real OneNote page three ways (browser ink, Python raster ink, opportunistic local HTML) under `archive/_bakeoff/` so we can pick a full archival pipeline.

**Architecture:** Shared preprocessing copies a Graph-downloaded page into `source/` with local assets and stripped MIME. Paths A/B/C each consume that source and write their own `page.html` (+ PDF where applicable). A uses Playwright + canvas ink; B uses Python InkML→PNG overlay; C ships local HTML with InkML sidecar and slides-only PDF.

**Tech Stack:** Python 3.12+ via `uv`, BeautifulSoup4, Pillow, Playwright (Chromium). Optional reuse of `inkml_parser/inkml.js` for path A.

## Global Constraints

- Do not modify or delete files under `out/`
- Write outputs only under `archive/_bakeoff/`
- Prefer `uv` for new Python entrypoints (PEP 723 script or small package)
- Sample page: Glycolysis page already under `out/` (title contains `Glycolysis`)
- Human-readable folder name from page `<title>`
- PDF for A/B must be one tall page when Playwright is used

## File map

| File | Role |
|------|------|
| `archive_bakeoff/__init__.py` | Package marker |
| `archive_bakeoff/preprocess.py` | MIME strip, asset copy, URL rewrite helpers |
| `archive_bakeoff/path_a.py` | Browser HTML + ink JS + Playwright PDF |
| `archive_bakeoff/path_b.py` | Python ink raster + static HTML + PDF |
| `archive_bakeoff/path_c.py` | Opportunistic local HTML + InkML sidecar + slides PDF |
| `archive_bakeoff/ink_render.js` | Minimal InkML→canvas for path A (no jQuery dependency) |
| `archive_bakeoff/run_bakeoff.py` | CLI: find sample page, run A/B/C, write COMPARE.md stub |
| `docs/projects/onenote-archive-bakeoff/plan.md` | This plan |

---

### Task 1: Shared preprocess + CLI scaffold

**Files:**
- Create: `archive_bakeoff/__init__.py`
- Create: `archive_bakeoff/preprocess.py`
- Create: `archive_bakeoff/run_bakeoff.py`
- Test: `tests/test_preprocess.py`

**Interfaces:**
- Produces:
  - `strip_multipart(html: str) -> str`
  - `sanitize_title(title: str) -> str`
  - `find_sample_page(out_dir: Path) -> Path` — first `page.html` whose title matches Glycolysis, else first page
  - `prepare_source(page_html_path: Path, bakeoff_root: Path) -> Path` — returns page bakeoff dir; writes `source/page.html` + `source/assets/*`; rewrites Graph `$value` URLs to `assets/<id>` relative paths; extracts title

- [ ] **Step 1: Write failing tests for MIME strip and title sanitize**

```python
from archive_bakeoff.preprocess import strip_multipart, sanitize_title

def test_strip_multipart_keeps_html():
    raw = "--abc\nContent-Type: text/html\n\n<html><body>hi</body></html>\n--abc--"
    out = strip_multipart(raw)
    assert out.strip().startswith("<html")
    assert "hi" in out

def test_sanitize_title():
    assert sanitize_title("20180830: Glycolysis / PPP?") == "20180830-Glycolysis-PPP"
```

- [ ] **Step 2: Run tests — expect FAIL (module missing)**

Run: `uv run --with pytest pytest tests/test_preprocess.py -v`

- [ ] **Step 3: Implement preprocess + CLI that only builds `source/`**

`prepare_source` must:
1. Read raw HTML; `strip_multipart`
2. Parse title with BeautifulSoup
3. Create `archive/_bakeoff/<sanitize_title>/source/assets/`
4. For each `src`, `data-fullres-src`, `data` attribute pointing at Graph `.../resources/<id>/$value`, copy sibling file named `<id>` from the original page directory into `assets/` when present; rewrite attribute to `assets/<id>`
5. Prefer rewriting `src` to the fullres asset when `data-fullres-src` maps to a local file
6. Write cleaned HTML to `source/page.html`
7. CLI: `uv run archive_bakeoff/run_bakeoff.py` → prepare source, print paths

- [ ] **Step 4: Run tests — expect PASS; run CLI once and confirm `source/` exists**

- [ ] **Step 5: Commit**

```bash
git add archive_bakeoff tests/test_preprocess.py && git commit -m "archive-bakeoff: add shared preprocess for Graph HTML"
```

---

### Task 2: Path C — opportunistic archive

**Files:**
- Create: `archive_bakeoff/path_c.py`
- Modify: `archive_bakeoff/run_bakeoff.py`

**Interfaces:**
- Consumes: bakeoff page dir from Task 1 (`source/page.html`)
- Produces: `build_path_c(page_dir: Path) -> None` writing `C_opportunistic/page.html`, `C_opportunistic/inkml/ink.inkml`, optional `page.pdf`

- [ ] **Step 1: Implement `build_path_c`**
  - Copy `source/page.html` → `C_opportunistic/page.html` with asset paths adjusted to `../source/assets/`
  - Extract `<inkml:ink>...</inkml:ink>` (or `ink` with xmlns) to `inkml/ink.inkml`; replace in HTML with an HTML comment noting ink not rendered
  - Add a visible banner at top: `Path C — opportunistic archive (ink not rendered)`
  - If Playwright available: PDF of the HTML (slides only); else skip PDF and note in stdout

- [ ] **Step 2: Wire into CLI; run; open HTML manually**

- [ ] **Step 3: Commit**

```bash
git commit -m "archive-bakeoff: add path C opportunistic local HTML"
```

---

### Task 3: Path B — Python ink raster

**Files:**
- Create: `archive_bakeoff/path_b.py`
- Modify: `archive_bakeoff/run_bakeoff.py`

**Interfaces:**
- Consumes: `source/page.html`, assets, extracted ink or inline InkML
- Produces: `build_path_b(page_dir: Path) -> None` → `B_python/page.html`, `B_python/ink_overlay.png`, `B_python/page.pdf`

- [ ] **Step 1: Implement InkML trace parser for OneNote-style traces**
  - Parse traces as comma-separated points; support simple `x y` or `x y f` channels
  - Convert himetric/ink units: use scale heuristic — if coords are large (>10000), treat as HIMETRIC (units/1000 inches) and convert to CSS pixels assuming 96 DPI: `px = himetric * 96 / 2540`
  - Compute bounding box; draw strokes with Pillow `ImageDraw.line` (black, width from brush or default 2)
  - Canvas size = max of content extents from HTML absolute positions (`left+width`, `top+height`) and ink bounds

- [ ] **Step 2: Build HTML**
  - Body with absolute-positioned images from `../source/assets/`
  - Overlay `<img src="ink_overlay.png" style="position:absolute;left:0;top:0;...">`
  - Banner: `Path B — Python raster ink`

- [ ] **Step 3: PDF via Playwright print of `B_python/page.html` (tall page: height = content height)**

- [ ] **Step 4: Run CLI path B; visually check overlay alignment**

- [ ] **Step 5: Commit**

```bash
git commit -m "archive-bakeoff: add path B Python ink raster"
```

---

### Task 4: Path A — Browser ink + Playwright PDF

**Files:**
- Create: `archive_bakeoff/ink_render.js`
- Create: `archive_bakeoff/path_a.py`
- Modify: `archive_bakeoff/run_bakeoff.py`

**Interfaces:**
- Consumes: source HTML + inkml file from path C extract (or extract inline)
- Produces: `build_path_a(page_dir: Path) -> None` → `A_browser/page.html`, `page.pdf`

- [ ] **Step 1: Write `ink_render.js`**
  - Parse InkML DOM; for each `trace`, split points; convert himetric→px same formula as B
  - Draw on a full-page canvas with `position:absolute; left:0; top:0; pointer-events:none; z-index:10`
  - Stroke style: round joins/caps; color from brush `color` property if present else `#000`

- [ ] **Step 2: Build `A_browser/page.html`**
  - Local assets via `../source/assets/`
  - Inline or `<script src="ink_render.js">` + `<script>` boot that loads `../C_opportunistic/inkml/ink.inkml` or embedded XML
  - Set body min-height from content extents
  - Banner: `Path A — browser ink`

- [ ] **Step 3: Playwright**
  - `page.goto(file://...)`; `wait_for_timeout` for ink draw; set viewport width ~1200; evaluate document height; `page.pdf(width, height, print_background=True)`

- [ ] **Step 4: Run full bakeoff; write `COMPARE.md` stub with checklist**

- [ ] **Step 5: Commit**

```bash
git commit -m "archive-bakeoff: add path A browser ink and Playwright PDF"
```

---

### Task 5: Smoke run + COMPARE.md

**Files:**
- Modify: `archive/_bakeoff/<page>/COMPARE.md` (generated)

- [ ] **Step 1: Run** `uv run archive_bakeoff/run_bakeoff.py`
- [ ] **Step 2: Confirm A/B/C HTML exist; A/B PDFs exist (or document Playwright install)**
- [ ] **Step 3: Fill COMPARE.md with observed results (alignment, ink presence, file sizes, blockers)**
- [ ] **Step 4: Commit generated bakeoff outputs only if small enough; otherwise gitignore `archive/` and commit COMPARE notes under docs

**Note:** Large binaries under `archive/` should be gitignored; keep `COMPARE.md` copy in `docs/projects/onenote-archive-bakeoff/COMPARE.md` if archive is ignored.

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Shared preprocess / MIME / assets | 1 |
| Path C opportunistic | 2 |
| Path B Python raster | 3 |
| Path A browser + PDF | 4 |
| COMPARE.md / success criteria | 5 |
| Do not touch `out/` | All tasks |
| Human-readable bakeoff paths | 1 |
