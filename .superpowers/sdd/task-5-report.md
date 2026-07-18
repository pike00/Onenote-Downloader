# Task 5 Report: Sync all notebooks

## Status

**Complete**

## Commits

- `onenote-dl: sync all notebooks with optional filter` — remove hard `"01 sfi"` filter; add `ONENOTE_NOTEBOOK_FILTER` env + `--notebook` CLI; README Archival section

## Summary

- **`onenote_dl/download_onenote.py`**
  - Removed hard-coded `if "01 sfi" not in notebook.displayName.lower(): continue`
  - Default: sync **all** notebooks returned by Graph
  - Optional filter via `Settings` (`ONENOTE_NOTEBOOK_FILTER`) or `--notebook SUBSTR` (CLI wins); substring match, case-insensitive
  - Mattermost notifications unchanged at notebook/section level
- **`README.md`**
  - Added **Archival** section: sync command, archive command with flags, Playwright Chromium install note

## Verification

```bash
uv run python -m onenote_dl.download_onenote --help
→ --notebook SUBSTR  Only sync notebooks whose name contains SUBSTR (overrides ONENOTE_NOTEBOOK_FILTER)
```

Full Graph sync not run (requires credentials and long runtime).

## Concerns

- First full sync of all notebooks will be significantly longer and noisier (Mattermost per notebook/section) than the previous SFI-only scope; consider throttling notifications or batching for large libraries.
- `deploy/onenote-sync.service` runs `python -m onenote_dl.download_onenote` with no filter — after deploy it will sync every notebook unless `ONENOTE_NOTEBOOK_FILTER` is set in the unit file.

---

## Task 5 review fixes (Critical/Important)

**Status:** Complete

**Commit:** (see SHA below)

### Changes

- **`onenote_dl/download_onenote.py`**
  - Removed `pydantic` / `pydantic_settings` (`Settings` class); filter via `os.environ.get("ONENOTE_NOTEBOOK_FILTER", "")` with `--notebook` CLI override
  - No pydantic import at module load — sync entrypoint runs without extra deps
- **`deploy/onenote-sync.service`**
  - Comment documenting optional `Environment=ONENOTE_NOTEBOOK_FILTER=` for partial sync
- **`README.md`**
  - Archival note: systemd unit syncs all notebooks unless filter set in unit
- **`Pipfile`**
  - Did not add `pydantic-settings` (only needed by untracked `dashboard.py`; sync script no longer uses it)

### Verification

```bash
PYTHONPATH=. uv run --with beautifulsoup4 python -c "import onenote_dl.download_onenote"
→ import ok

uv run python -m onenote_dl.download_onenote --help
→ --notebook SUBSTR  Only sync notebooks whose name contains SUBSTR (overrides ONENOTE_NOTEBOOK_FILTER)
```
