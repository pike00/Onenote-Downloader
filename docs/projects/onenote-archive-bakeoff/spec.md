# OneNote Archive Bake-off Spec

## Goal

Compare three rendering pipelines on the same real OneNote page(s) so we can choose a primary archival path. Success means HTML and PDF outputs you can open side by side and judge ink fidelity, layout, and usefulness — not a full notebook export yet.

## Decisions (locked)

- **Delivery:** Staged — usable archive first, accurate ink as the north star.
- **Artifacts:** Self-contained HTML is the working archive; PDF is generated from / alongside it.
- **Layout:** Human-readable paths for the bake-off under `archive/_bakeoff/`.
- **Method:** Run approaches A, B, and C on the same sample page(s), then pick a winner for the full archive project.

## Sample input

Primary page (already downloaded under `out/`):

- Title: `20180830: Glycolysis and Pentose Phosphate Pathway`
- Traits: ~25 slide images, embedded InkML, attachment(s), absolute positioning
- Optional second page: another ink-heavy page from the same section if the first is too large to iterate on quickly

Source Graph HTML remains untouched under `out/`. Bake-off outputs only write under `archive/`.

## Output layout

```
archive/_bakeoff/<sanitized-page-title>/
  source/                 # shared: cleaned HTML + local asset copies
    page.html             # Graph multipart wrapper stripped; remote URLs rewritten later per path
    assets/               # binary resources keyed by Graph resource id
  A_browser/
    page.html             # self-contained; ink via canvas/SVG
    page.pdf              # Playwright, one tall page
  B_python/
    page.html             # static; ink pre-rasterized into overlay image(s)
    page.pdf
  C_opportunistic/
    page.html             # local assets; ink left as InkML sidecar / stub overlay
    inkml/                # extracted InkML if useful
    page.pdf              # optional slides-only PDF
  COMPARE.md              # short notes after visual review
```

Page title sanitization: filesystem-safe, keep date prefix and readable words (e.g. `20180830-Glycolysis-and-Pentose-Phosphate-Pathway`).

## Shared preprocessing (all paths)

1. Strip Microsoft Graph multipart MIME preamble/epilogue from downloaded `page.html`.
2. Copy referenced `$value` resources into `source/assets/` (use existing files under the page dir when present).
3. Preserve absolute `position` / `left` / `top` / width / height from the Graph HTML.
4. Prefer `data-fullres-src` image URLs when a local asset exists for that id.

## Approach A — Browser render pipeline

1. Rewrite `page.html` to load assets from relative `../source/assets/` (or copy assets into `A_browser/`).
2. Parse embedded InkML; render strokes with canvas or SVG positioned over the page coordinate system (adapt `inkml_parser/inkml.js` / related code; best-effort colors/width).
3. Open HTML in headless Chromium (Playwright); print/export one continuous tall PDF (`page.pdf`).
4. Record failures: missing brushes, coordinate scale mismatches, overflow, performance on large ink.

## Approach B — Python rasterize

1. Same local HTML/asset base as A, but without live ink JS.
2. Parse InkML traces in Python (reuse/adapt `inkml2img` / `inkml_parser` Python helpers).
3. Rasterize strokes to PNG overlay(s) sized to the page content box; composite onto a page canvas or inject as absolutely positioned `<img>`.
4. Emit static `B_python/page.html` and PDF (Chromium print of that HTML, or image→PDF if simpler for the spike).
5. Record fidelity gaps vs OneNote (pressure, color, layering, alignment).

## Approach C — Opportunistic archive

1. Local HTML + assets only; strip or comment out live Graph URLs.
2. Extract InkML to `inkml/` sidecar; do not fully render (optional stub note in HTML: “ink not rendered”).
3. Optional PDF of slides/images without ink — proves “archive now.”
4. Serves as the Stage-1 bulk path if A/B need more ink work.

## Success criteria (bake-off)

- [ ] Open `A_browser/page.html`, `B_python/page.html`, `C_opportunistic/page.html` in a browser
- [ ] Open PDFs for A and B (C optional)
- [ ] Visually judge which ink/layout is closest to OneNote
- [ ] `COMPARE.md` lists winner, blockers, and whether full archive should be A, B, C, or hybrid

## Out of scope

- Full notebook / section walk and Mattermost notifications
- Perfect InkML pressure/color parity with OneNote
- Production CLI polish, config flags, or renaming all of `out/`
- Migrating Pipfile → uv (may add a bake-off script with PEP 723 / small `pyproject` only if needed to run)

## Tooling notes

- Prefer `uv` for any new Python entrypoint (per project Python toolchain).
- Playwright Chromium for A (and likely B/C PDF) if available; document install step.
- Do not delete or rewrite files under `out/` during the bake-off.

## Follow-up (after bake-off)

Separate project: full human-readable `archive/<notebook>/<section>/<page>/` tree using the chosen pipeline, with ink fidelity improvements as needed.
