# OneNote Full Archive Spec (Path A)

## Goal

Export **all OneNote notebooks** to a human-readable offline archive: self-contained HTML with canvas-rendered InkML ink, plus a matching tall single-page PDF per page, browsable via simple index pages.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Render pipeline | **Path A** (browser canvas ink + Playwright PDF) |
| Notebook scope | **All notebooks** (remove `"01 sfi"` filter) |
| Artifacts | `page.html` + `page.pdf` per page |
| Layout | Human-readable `archive/<Notebook>/<Section>/<Page>/` |
| Source of truth for sync | Keep UUID tree under `out/` untouched as Graph cache |
| Fallback | If ink/PDF fails, still write localized HTML (path-C style) and log the failure |
| Bake-off | Remains under `archive/_bakeoff/`; production tree is `archive/` excluding `_bakeoff` |

## Pipeline

```
Microsoft Graph
      │
      ▼
[1] Sync  →  out/<notebookId>/<sectionId>/<pageId>/page.html + assets
      │
      ▼
[2] Render (path A)  →  archive/<Notebook>/<Section>/<PageTitle>/
                              page.html, page.pdf, assets/, ink.inkml?
      │
      ▼
[3] Indexes  →  archive/index.html, archive/<Notebook>/index.html
```

### Stage 1 — Sync

- Extend `onenote_dl/download_onenote.py` (or extract a `sync_all` entrypoint) to iterate **every** notebook from Graph.
- Optional CLI filter: `--notebook SUBSTR` for partial runs; default = all.
- Preserve existing behavior: multipart HTML with `?includeinkML=true`, binary assets beside `page.html`, JSON metadata files.
- Do not delete existing `out/` data; skip re-download when files exist unless `--force`.

### Stage 2 — Render (path A)

For each `out/**/page.html`:

1. Resolve notebook/section/page display names from sibling `notebooks.json` / `sections.json` / `pages.json` (or page `<title>`).
2. `parse_multipart` → HTML + InkML; copy/localize assets with correct extensions.
3. Write self-contained HTML: absolute layout preserved, canvas ink via `ink_render.js` (inline InkML preferred for `file://`).
4. Playwright → one tall PDF (`print_background`, height from content).
5. On failure: write best-effort HTML without ink canvas if needed; append to `archive/failures.log`; continue.

Reuse/refactor bake-off modules under `archive_bakeoff/` into a production module (e.g. rename or promote to `onenote_archive/`) rather than duplicating logic.

### Stage 3 — Indexes

- `archive/index.html` — list of notebooks (links).
- `archive/<Notebook>/index.html` — sections and pages.
- Relative links only; works from local disk / static host.

## Output layout

```
archive/
  index.html
  failures.log                 # optional, created on errors
  <NotebookName>/
    index.html
    <SectionName>/
      <PageTitle>/
        page.html
        page.pdf
        assets/
          <resourceId>.png
          …
        ink.inkml              # when InkML part present
        ink_render.js          # or shared copy / inlined script
  _bakeoff/                    # existing experiments; ignored by production walker
```

Name sanitization: filesystem-safe (same rules as bake-off `sanitize_title`). Collisions: append short page-id suffix.

## CLI

```bash
# Sync all notebooks from Graph
uv run onenote_dl/download_onenote.py
# or: uv run -m onenote_dl.sync --all

# Render archive from out/ → archive/
uv run onenote_archive/run_archive.py
uv run onenote_archive/run_archive.py --notebook "01 sfi"   # optional filter
uv run onenote_archive/run_archive.py --skip-pdf            # HTML only
uv run onenote_archive/run_archive.py --force               # rebuild existing pages
```

Exact module names may be `onenote_archive/` promoted from `archive_bakeoff/`.

## Success criteria

- [ ] Sync downloads pages for every notebook (not only SFI)
- [ ] `archive/index.html` lists all synced notebooks that were rendered
- [ ] Spot-check ≥3 ink-heavy pages: ink visible in HTML and PDF
- [ ] Failed pages logged; run completes without aborting the whole archive
- [ ] Re-run is incremental (skips up-to-date `page.html`/`page.pdf` unless `--force`)

## Out of scope (v1)

- Perfect pressure / highlighter parity with OneNote desktop
- Section groups / nested section hierarchies beyond flat section list from Graph
- Live daemon / watch mode
- Mattermost notify per page (notebook/section level OK to keep on sync)
- Uploading archive to remote storage

## Dependencies

- Python via `uv`; BeautifulSoup4, Pillow (if shared helpers need it), Playwright + Chromium
- Existing OAuth / Graph helpers unchanged except notebook filter

## Follow-ups (later)

- Shared `ink_render.js` at archive root to shrink per-page HTML
- Parallel Playwright workers
- Content-hash cache so unchanged Graph pages skip PDF regeneration
