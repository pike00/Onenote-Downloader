# Task 1 Report: Promote bake-off into `onenote_archive`

## Status

**COMPLETE**

## What implemented

Created `onenote_archive/` package with shared production render pipeline:

- **`preprocess.py`** — Moved all multipart parsing, asset localization, and title/extent helpers from bake-off. Added `PreparedPage` dataclass and `prepare_page(page_html, dest_dir)` which writes `page.html`, `assets/`, and optional `ink.inkml` directly into the destination page directory (production layout).
- **`render_a.py`** — Path A render: `render_path_a(prepared, dest_dir, *, skip_pdf=False) -> RenderResult`. Writes final `page.html`, copies `ink_render.js`, inlines InkML on canvas, optional PDF via Playwright.
- **`pdf_export.py`** — `html_to_pdf` and `html_to_pdf_with_ink_wait` (ink canvas wait extracted from bake-off path A).
- **`ink_render.js`** — Copied from bake-off (unchanged).
- **`__init__.py`** — Exports `PreparedPage`, `RenderResult`, `prepare_page`, `render_path_a`.

Refactored **`archive_bakeoff/`** to thin wrappers:

- `preprocess.py` re-exports shared helpers; `prepare_source` delegates to `prepare_page` with bake-off `source/` subdir layout.
- `pdf_export.py` re-exports from `onenote_archive.pdf_export`.
- `path_a.py`, `path_b.py`, `path_c.py` import HTML helpers from `onenote_archive.render_a`; path A uses `html_to_pdf_with_ink_wait`.
- `inkml_common.py` imports `himetric_to_px` from `onenote_archive.preprocess`.

## Tests + output

```text
PYTHONPATH=. uv run --with pytest --with beautifulsoup4 pytest tests/test_preprocess.py tests/test_onenote_archive.py -v
```

```
tests/test_preprocess.py::test_strip_multipart_keeps_html PASSED
tests/test_preprocess.py::test_parse_multipart_extracts_inkml_sibling PASSED
tests/test_preprocess.py::test_sanitize_title PASSED
tests/test_onenote_archive.py::test_prepare_page_writes_assets_and_inkml PASSED
tests/test_onenote_archive.py::test_render_path_a_writes_html PASSED

5 passed in 0.08s
```

## Files changed

| File | Change |
|------|--------|
| `onenote_archive/__init__.py` | Created |
| `onenote_archive/preprocess.py` | Created (moved + `prepare_page`) |
| `onenote_archive/render_a.py` | Created |
| `onenote_archive/pdf_export.py` | Created |
| `onenote_archive/ink_render.js` | Created (copied) |
| `archive_bakeoff/preprocess.py` | Thin wrapper + `prepare_source` |
| `archive_bakeoff/pdf_export.py` | Re-export |
| `archive_bakeoff/path_a.py` | Uses shared PDF + HTML helpers |
| `archive_bakeoff/path_b.py` | Import from `render_a` |
| `archive_bakeoff/path_c.py` | Import from `render_a` |
| `archive_bakeoff/inkml_common.py` | Import from `onenote_archive` |
| `tests/test_preprocess.py` | Import from `onenote_archive.preprocess` |
| `tests/test_onenote_archive.py` | Created (prepare_page + render_path_a) |

## Commit

- `a75bca8` — `onenote-archive: promote path A render into shared package`

## Self-review

**Strengths**

- Shared logic lives in one place; bake-off remains runnable via `prepare_source` + path builders.
- `prepare_page` matches spec layout (`dest_dir/page.html`, `assets/`, `ink.inkml`).
- `render_path_a` mirrors bake-off path A minus banner and `../source` prefix (assets already local).
- Existing preprocess tests pass unchanged in behavior; two new integration tests cover new interfaces.

**Notes / minor items**

- `_inject_after_body` and `_ensure_body_size` are imported by bake-off from `render_a` (private by convention but shared intentionally to avoid a third module).
- `archive_bakeoff/ink_render.js` kept for path A copy source; duplicate of `onenote_archive/ink_render.js` — acceptable until bake-off is retired or symlinked.
- Did not run full `run_bakeoff.py` end-to-end (requires sample `out/` data + Playwright); structural imports verified via unit tests.

## Concerns

- None blocking. Full bake-off smoke test with Playwright PDF generation was not run in this task (optional follow-up).

---

## Task 1 review fixes

**Status:** COMPLETE

### Changes

1. **`RenderResult.ok` respects PDF export** — `render_path_a` now checks `html_to_pdf*` return value and `page.pdf` existence. When PDF is requested and export fails, returns `ok=False`, `html=page_html`, `pdf=None`, `error="PDF export failed"`. `skip_pdf=True` unchanged.
2. **Ink canvas test** — `test_render_path_a_injects_ink_canvas` runs `prepare_page` → `render_path_a(..., skip_pdf=True)` on a multipart InkML fixture; asserts canvas, `inkml-data`, `ink_render.js`, and `remove_inkml` comment in output.
3. **`prepared.inkml_path` fallback** — When `extract_inkml(html)` returns None, reads sidecar from `prepared.inkml_path` if present.

### Tests + output

```text
PYTHONPATH=. uv run --with pytest --with beautifulsoup4 pytest tests/test_onenote_archive.py tests/test_preprocess.py -v
```

```
tests/test_onenote_archive.py::test_prepare_page_writes_assets_and_inkml PASSED
tests/test_onenote_archive.py::test_render_path_a_writes_html PASSED
tests/test_onenote_archive.py::test_render_path_a_injects_ink_canvas PASSED
tests/test_preprocess.py::test_strip_multipart_keeps_html PASSED
tests/test_preprocess.py::test_parse_multipart_extracts_inkml_sibling PASSED
tests/test_preprocess.py::test_sanitize_title PASSED

6 passed in 0.09s
```

### Commit

- `b01a842` — `onenote-archive: fix render_path_a PDF ok semantics and ink coverage`
