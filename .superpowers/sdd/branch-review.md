# Whole-branch review: OneNote Full Archive (Path A)

**Range:** `a0359ad`…`c90cce3`  
**Reviewer:** Senior Code Reviewer (final branch review)  
**Sources:** `docs/projects/onenote-full-archive/spec.md`, `plan.md`, packed diff (`.superpowers/sdd/branch-review-pkg.md`), live `onenote_archive/` + sync entrypoint, NOTES E2E, prior task reviews

---

## Strengths

- **Spec/plan coverage is complete for Path A.** Bake-off promoted into `onenote_archive/` with thin bake-off re-exports; catalog maps UUID `out/` → display names; walker does incremental skip, `--force`, `--skip-pdf`, filters, failures.log; indexes + discover merge; sync defaults to all notebooks with env/CLI filter.
- **Clear package boundaries.** `prepare_page` → `render_path_a` → `html_to_pdf*` matches the locked pipeline; production layout (`page.html` / `page.pdf` / `assets/` / `ink.inkml`) matches the spec tree.
- **Failure isolation.** Per-page `try`/`except` and `RenderResult.ok` keep a full archive run from aborting; PDF failure still leaves HTML on disk (path-A best effort).
- **Collision + incremental design is thoughtful.** `.page_id` markers plus in-run `claimed` map; skip requires HTML+(PDF|skip-pdf); review fixes addressed unsafe overwrite of unmarked dirs.
- **Indexes are production-usable.** Relative links, HTML escaping (tested), `_bakeoff` skipped on discover, merge so filtered runs do not wipe the rest of the archive tree.
- **Ops/docs.** README Archival section, systemd unit documents all-notebook default + optional filter, NOTES.md records E2E (28 pages, Glycolysis ink/PDF spot-check, 0 failures).
- **Tests cover the new surfaces.** preprocess, prepare/render (+ ink canvas), catalog, indexes (incl. merge + XSS). Per-task Critical/Important items (PDF `ok` semantics, collision safety, pydantic sync import) were addressed in-branch.

---

## Issues

### Critical

*(none)*

### Important

1. **Failed renders leave unmarked dirs → retry lands on a collision-suffixed path**  
   `_write_page_id` runs only when `result.ok`. On PDF failure (or exception after `prepare_page`), `dest/` has `page.html` but no `.page_id`. Next run treats that dir as a collision (`stored is None` → suffix) and writes to `Title-<pageId8>/`, orphaning the original and risking duplicate index entries. PDF retries therefore do not repair the canonical path. **Fix:** write `.page_id` whenever this page claims the dest (including HTML-ok/PDF-fail), or reuse unmarked dirs that already contain this run’s output for the same `page_id`.

2. **Index merge keys display name vs filesystem slug → duplicate notebook/section groups on partial runs**  
   `discover_archived_pages` synthesizes `notebook_name`/`section_name`/`page_title` from directory slugs (`01-SFI`), while live `PageRef`s use Graph display names (`01 SFI`). `write_indexes` groups by those strings, then both sanitize to the same folder. After a filtered/partial run against a populated archive, root `index.html` can list the same notebook twice, and notebook indexes can split one section into slug vs spaced headings. Full unfiltered runs with all pages in `collected` override discovery and look fine (NOTES). **Fix:** group by `sanitize_title(name)` (or dest parent slug), and prefer non-`discovered` display names when merging.

### Minor

1. **Mattermost volume on full sync (ops)** — Default-all notebooks keep per-notebook and per-section notifications; first full library sync will be noisy. Spec allows notebook/section-level notify; throttle/batch later if needed.
2. **Single collision suffix attempt** — If `Title` and `Title-<suffix>` both conflict, walker still claims the suffixed path (rare).
3. **Playwright browser per page** — Correct but slow (~minutes for dozens of pages); parallel/shared browser is an acknowledged follow-up.
4. **README Todo** — “Regenerate annotated documents…” remains unchecked despite Archival section shipping the feature.
5. **E2E scope** — NOTES verify render on a partial single-notebook `out/`; multi-notebook Graph sync not exercised in-branch (acceptable; credentials/runtime).

---

## Spec success criteria

| Criterion | Status |
|-----------|--------|
| Sync every notebook (not only SFI) | ✅ Code/default; filter optional |
| `archive/index.html` lists rendered notebooks | ✅ (+ discover merge) |
| Spot-check ≥3 ink-heavy / Glycolysis HTML+PDF | ✅ NOTES (Glycolysis PDF ~5 MB, ink canvas) |
| Failures logged; run does not abort | ✅ |
| Incremental skip unless `--force` | ✅ (happy path); see Important #1 for fail-retry) |

---

## Assessment

**Ready to merge.**

No Critical defects. The Path A archive pipeline, sync-all default, indexes, CLI, and documented E2E satisfy the locked spec for the primary full-run workflow. The two Important items are real edge-case correctness bugs (failure retry path; partial-run index naming) and should be follow-up fixes before relying on repeated failure recovery or frequent filtered re-index runs against a large archive—but they do not block merging this feature branch.

---

## Fixes applied

- **Important #1 (`.page_id` on failure):** `_process_page` now writes `.page_id` as soon as a page is processed (before render) and backfills the marker on skip when missing, so PDF/HTML partial failures and retries reuse the canonical dest path instead of colliding into a suffixed orphan.
- **Important #2 (index slug vs display name):** `write_indexes` groups notebooks/sections by filesystem path segments under `archive_root`, preferring catalog `PageRef` display names over discovered slug labels when merging partial runs with prior archive content.
- **Tests:** Added coverage for page-id-on-fail, marked-dir retry reuse, and slug/display index grouping (`tests/test_onenote_archive.py`, `tests/test_indexes.py`).
