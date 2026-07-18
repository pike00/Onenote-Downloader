# Task 4 Report: Index pages

## Status

**Complete**

## Commits

- `onenote-archive: implement static HTML archive indexes` — `write_indexes` in `indexes.py`, `run_archive.py` passes dest dirs, `tests/test_indexes.py`

## Implementation

### `onenote_archive/indexes.py`

- `write_indexes(archive_root, pages, dest_dirs)` writes:
  - `archive/index.html` — sorted notebook list linking to `<nb-slug>/index.html`
  - `archive/<nb-slug>/index.html` — sections (h2) with sorted page links to relative `page.html` paths
- Minimal inline CSS typography; no framework
- HTML-escapes notebook, section, and page titles
- Uses actual `dest_dir` paths from the walker (collision suffixes preserved)

### `onenote_archive/run_archive.py`

- Collects `(PageRef, dest_dir)` tuples for pages with `page.html` on disk
- Passes parallel `pages` / `dest_dirs` lists to `write_indexes`

### `tests/test_indexes.py`

- Root + notebook index structure, sort order, relative links
- XSS escape test for titles containing `<script>`, `&`, quotes

## Verification

```bash
PYTHONPATH=. uv run --with pytest pytest tests/test_indexes.py -q
→ 2 passed

PYTHONPATH=. uv run onenote_archive/run_archive.py --title Glycolysis
→ skip  01-SFI/Biochemistry/20180830-Glycolysis-and-Pentose-Phosphate-Pathway
→ skip  01-SFI/Biochemistry/20180830-Oxidative-Phosphorylation-and-Glycolysis
→ done: processed=2 ok=0 skipped=2 failed=0
```

Verified:

- `archive/index.html` exists; links to `01-SFI/index.html`
- `archive/01-SFI/index.html` lists Biochemistry section with two Glycolysis pages
- Link targets `Biochemistry/.../page.html` exist on disk

## Concerns

- ~~Filtered runs (`--title`, `--notebook`) regenerate indexes from the processed subset only; notebooks/sections not in the run are omitted from indexes until a full run.~~ **Fixed** — see follow-up commit below.
- Stale per-notebook `index.html` files may remain under `archive/` if a notebook drops out of a partial run (same as above).

---

## Follow-up: merge discovered pages into indexes

### Status

**Complete**

### Commit

- `onenote-archive: merge discovered pages into write_indexes` — `discover_archived_pages` scans `archive_root` for `nb/sec/page/page.html` (skips `_bakeoff/`), `write_indexes` unions by resolved dest path; provided `PageRef`s override synthesized names

### Changes

- **`discover_archived_pages(archive_root)`** — returns `(PageRef, dest_dir)` for each on-disk page; synthesizes display names from directory slugs and dummy ids when no catalog ref exists
- **`write_indexes`** — merges discovered pages with the caller's `pages`/`dest_dirs` keyed by `dest_dir.resolve()`; caller entries win on collision (preserves real notebook/section/page titles)
- **`run_archive`** — unchanged; relies on `write_indexes` scanning
- **`tests/test_indexes.py`** — `test_write_indexes_merges_discovered_pages`: two pages on disk, pass one `PageRef`, root index lists both notebooks

### Verification

```bash
PYTHONPATH=. uv run --with pytest pytest tests/test_indexes.py -q
→ 3 passed
```
