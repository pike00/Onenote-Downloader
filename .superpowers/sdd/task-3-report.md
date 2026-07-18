# Task 3 Report: Archive CLI walker + incremental + failures

## Status

**Complete**

## Commits

- `onenote-archive: add run_archive CLI walker with incremental skip` — adds `onenote_archive/run_archive.py` and stub `onenote_archive/indexes.py`

## Implementation

### `onenote_archive/run_archive.py`

- PEP 723 uv script header (`beautifulsoup4`, `playwright`)
- CLI: `--out` (default `out/`), `--archive` (default `archive/`), `--notebook SUBSTR`, `--skip-pdf`, `--force`, `--limit N`
- Walks `iter_pages(out_dir)`; filters notebooks by case-insensitive substring
- Dest path: `archive/<sanitize(nb)>/<sanitize(sec)>/<sanitize(title)>/`
- Collision: if dest exists with different `.page_id` marker (or claimed in-run), appends last 8 safe chars of page_id
- Incremental: skip when `page.html` exists and (`page.pdf` exists or `--skip-pdf`) unless `--force`
- Pipeline: `prepare_page` → `render_path_a`; writes `.page_id` marker on success
- Failures: append tab-separated line to `archive/failures.log`; continue run
- Calls stub `write_indexes(archive_root, collected_pages)` at end

### `onenote_archive/indexes.py`

- Stub `write_indexes(archive_root, pages)` — no-op until Task 4

## Smoke test

```bash
PYTHONPATH=. uv run onenote_archive/run_archive.py --limit 1 --skip-pdf
→ ok    01-SFI/Admin/20180806-Intro-to-Sci-Foundations-I
→ done: processed=1 ok=1 skipped=0 failed=0
```

Verified:

- `archive/01-SFI/Admin/20180806-Intro-to-Sci-Foundations-I/page.html` exists (2.5M, with ink canvas assets)
- Output under `archive/`, not `archive/_bakeoff/`
- Re-run with same args: `skip` (incremental)

## Concerns

- Collision handling for pre-existing archive dirs without `.page_id` marker assumes same page on re-run; true title collisions before marker exists could overwrite once.
- Smoke used first catalog page (Admin intro), not Glycolysis specifically — Glycolysis page is in `out/` and will render on full run.
- `write_indexes` is a stub; no `archive/index.html` until Task 4.

## Next

Task 4: implement `write_indexes` and notebook/section index pages.

---

## Task 3 review fixes

**Status:** Complete

### Code changes (`onenote_archive/run_archive.py`)

1. **Collision safety:** Existing dest dirs without `.page_id` (or with mismatched id) now get a page-id suffix instead of being overwritten in place. Reuse only when `.page_id` matches the current page.
2. **Indexes input:** `write_indexes` receives only pages with `page.html` present at dest (successful render or valid incremental skip), not failed pages.
3. **CLI `--title SUBSTR`:** Case-insensitive filter on `PageRef.page_title`, parallel to `--notebook`.

### Glycolysis PDF smoke test

```bash
PYTHONPATH=. uv run onenote_archive/run_archive.py --title Glycolysis --force
→ ok    01-SFI/Biochemistry/20180830-Glycolysis-and-Pentose-Phosphate-Pathway
→ ok    01-SFI/Biochemistry/20180830-Oxidative-Phosphorylation-and-Glycolysis
→ done: processed=2 ok=2 skipped=0 failed=0
```

Verified:

- `archive/01-SFI/Biochemistry/20180830-Glycolysis-and-Pentose-Phosphate-Pathway/page.pdf` — **4.9 MB** (> 1 MB)
- `page.html` co-located in same dir
- Playwright chromium available; PDF export succeeded (~14 s for 2 pages)
- `--title Glycolysis` matched 2 pages (both titles contain "Glycolysis"); primary target page rendered with PDF

### Test notes

- Collision fix: dirs without `.page_id` marker no longer treated as same-page reuse.
- Index collection: failed pages excluded from `collected` passed to stub `write_indexes`.
- Title filter smoke confirms ink-heavy Glycolysis PDF path end-to-end (not `--skip-pdf`).
