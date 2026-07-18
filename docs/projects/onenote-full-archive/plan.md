# OneNote Full Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sync all OneNote notebooks to `out/`, then render every page with path A into a human-readable `archive/` tree with HTML, tall PDFs, and indexes.

**Architecture:** Promote bake-off preprocess + path-A render into an `onenote_archive` package. Sync removes the SFI-only filter (optional `--notebook` filter). A walker maps Graph UUID paths → display-name paths, renders incrementally, builds indexes, logs failures.

**Tech Stack:** Python 3.11+ via `uv`, BeautifulSoup4, Playwright/Chromium; reuse `archive_bakeoff` logic.

## Global Constraints

- Path A only for production render (canvas ink + Playwright PDF)
- All notebooks by default; optional `--notebook SUBSTR`
- Do not delete or rewrite Graph cache under `out/` except normal download overwrite with `--force`
- Human-readable `archive/<Notebook>/<Section>/<PageTitle>/`
- Skip `archive/_bakeoff/` in production walker
- Incremental: skip pages whose `page.html`+`page.pdf` exist unless `--force`
- On render failure: best-effort HTML + log; do not abort whole run

## File map

| File | Role |
|------|------|
| `onenote_archive/__init__.py` | Package |
| `onenote_archive/preprocess.py` | Moved/adapted from `archive_bakeoff/preprocess.py` |
| `onenote_archive/ink_render.js` | From bake-off |
| `onenote_archive/pdf_export.py` | Playwright PDF helper |
| `onenote_archive/render_a.py` | Path A page render → archive page dir |
| `onenote_archive/catalog.py` | Map `out/` UUIDs → display names via JSON sidecars |
| `onenote_archive/indexes.py` | Write notebook + root index.html |
| `onenote_archive/run_archive.py` | CLI walker |
| `onenote_dl/download_onenote.py` | Remove hard SFI filter; optional env/CLI filter |
| `archive_bakeoff/*` | Keep for bake-off; import from `onenote_archive` or thin wrappers |

---

### Task 1: Promote bake-off into `onenote_archive`

**Files:**
- Create: `onenote_archive/preprocess.py`, `ink_render.js`, `pdf_export.py`, `render_a.py`, `__init__.py`
- Modify: `archive_bakeoff/*` to re-export from `onenote_archive` (avoid duplication)
- Test: `tests/test_preprocess.py` (update imports)

**Interfaces:**
- Produces:
  - `prepare_page(page_html: Path, dest_dir: Path) -> PreparedPage` with fields `html_path`, `width`, `height`, `title`, `inkml_path | None`, `assets_dir`
  - `render_path_a(prepared: PreparedPage, dest_dir: Path, *, skip_pdf: bool = False) -> RenderResult` (`ok`, `html`, `pdf | None`, `error | None`)

- [ ] **Step 1:** Move/copy preprocess + path A + pdf + ink_render.js into `onenote_archive/`; adjust `prepare_source` to write directly into the final page dir (assets + ink beside `page.html`, not bake-off A/B/C layout).

- [ ] **Step 2:** Point `archive_bakeoff` imports at `onenote_archive` or leave bake-off as-is and copy code once — prefer **move shared code to `onenote_archive`**, bake-off re-exports.

- [ ] **Step 3:** Update tests; `PYTHONPATH=. uv run --with pytest --with beautifulsoup4 pytest tests/test_preprocess.py -v` → PASS

- [ ] **Step 4:** Commit

```bash
GIT_COMMIT_ACK=1 git commit -m "onenote-archive: promote path A render into shared package"
```

---

### Task 2: Catalog — UUID paths → display names

**Files:**
- Create: `onenote_archive/catalog.py`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Produces:
  - `dataclass PageRef: notebook_id, section_id, page_id, notebook_name, section_name, page_title, page_html: Path`
  - `iter_pages(out_dir: Path) -> Iterator[PageRef]`
  - Names from `out/notebooks.json`, `out/<nb>/sections.json`, `out/<nb>/<sec>/pages.json`; page title fallback = `<title>` in HTML

- [ ] **Step 1:** Write test with tiny fake `out/` tree (tmp_path)

```python
def test_iter_pages_resolves_names(tmp_path):
    # create notebooks.json, sections.json, pages.json, page.html
    refs = list(iter_pages(tmp_path))
    assert refs[0].notebook_name == "Demo NB"
    assert refs[0].section_name == "Sec"
    assert "Lecture" in refs[0].page_title
```

- [ ] **Step 2:** Implement `catalog.py`

- [ ] **Step 3:** Tests pass; commit

---

### Task 3: Archive CLI walker + incremental + failures

**Files:**
- Create: `onenote_archive/run_archive.py`
- Create: `onenote_archive/indexes.py` (stub ok until Task 4)

**Interfaces:**
- CLI args: `--out`, `--archive`, `--notebook SUBSTR`, `--skip-pdf`, `--force`, `--limit N` (for smoke)
- For each `PageRef`: dest = `archive/sanitize(nb)/sanitize(sec)/sanitize(title)/`; skip if html+pdf exist and not force; call `render_path_a`; append failures to `archive/failures.log`

- [ ] **Step 1:** Implement walker; smoke with `--limit 1` on existing Glycolysis page

- [ ] **Step 2:** Verify output under `archive/<Notebook>/.../page.html` and PDF

- [ ] **Step 3:** Commit

---

### Task 4: Index pages

**Files:**
- Modify: `onenote_archive/indexes.py`, `run_archive.py`

**Interfaces:**
- `write_indexes(archive_root: Path, pages: list[PageRef]) -> None`
- Root index lists notebooks; notebook index lists `Section / Page` links to `page.html`

- [ ] **Step 1:** Implement minimal clean HTML indexes (no framework)

- [ ] **Step 2:** Run archive on ≥1 notebook worth of already-downloaded pages; open `archive/index.html`

- [ ] **Step 3:** Commit

---

### Task 5: Sync all notebooks

**Files:**
- Modify: `onenote_dl/download_onenote.py`
- Optional: `onenote_dl/cli_sync.py` if cleaner than argparse in place

**Interfaces:**
- Remove hard-coded `if "01 sfi" not in ...: continue`
- Add optional filter: env `ONENOTE_NOTEBOOK_FILTER` or `--notebook` if script gains argparse; default sync all
- Keep Mattermost notifications at notebook/section level

- [ ] **Step 1:** Implement filter change

- [ ] **Step 2:** Document in README: sync then archive commands

- [ ] **Step 3:** Commit (do not run full Graph sync in CI; user runs locally)

---

### Task 6: End-to-end verification

- [ ] Run `uv run onenote_archive/run_archive.py` on current `out/` (all downloaded pages)
- [ ] Confirm indexes + spot-check ink on Glycolysis
- [ ] Update `docs/projects/onenote-full-archive/COMPARE-or-NOTES.md` with run stats (pages ok / failed)
- [ ] Commit docs + any fixes

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| Path A render | 1, 3 |
| Human-readable tree | 2, 3 |
| Indexes | 4 |
| All notebooks sync | 5 |
| Fallback + failures.log | 3 |
| Incremental / --force | 3 |
| Optional notebook filter | 3, 5 |
