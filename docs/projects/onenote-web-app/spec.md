# OneNote Archive Web App — Spec

## Goal

A clear Tailscale-only web app that **automatically** archives all OneNote notebooks in series (sync → Path A render), while showing a polished live status UI. The app is primarily a **status viewer** with Start / Pause / Resume — not a notebook picker.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Product role | Status viewer + auto pipeline (all notebooks in sequence) |
| Stack | FastAPI + Jinja2 + HTMX + Tailwind CSS (CDN) |
| Process model | **Web** + **serial worker** (two systemd user units) |
| Job state | SQLite (`jobs.db`) |
| Network | Bind Tailscale IPv4 only (same trust model as Fava) |
| Sync scope | **All notebooks** (remove `"01 sfi"` hardcode) |
| Render default | **Path A** (browser canvas ink + Playwright tall PDF) |
| Compare paths | B/C optional via config flag only (not a selection UI) |
| Disk layout | `out/` = Graph UUID cache; `archive/` = human-readable Path A tree |
| Controls | Start / Pause / Resume only |
| Auth | None beyond Tailscale |

## Non-goals (v1)

- Per-notebook / per-page checkbox scoping
- React/Vite SPA
- Redis/Celery
- Public internet exposure / IdP login
- Running B/C on every page by default

## Architecture

```
Browser (tailnet)
      │  HTMX poll / SSE-ish refresh
      ▼
onenote-web  (FastAPI, Tailscale :8747)
      │  read-only status + control endpoints
      ▼
jobs.db (SQLite)
      ▲
      │  claim next page job
onenote-worker  (serial)
      │
      ├─[1] Graph sync → out/<nbId>/<secId>/<pageId>/
      └─[2] Path A render → archive/<Notebook>/<Section>/<Page>/
```

### Web process (`onenote-web`)

- Serves status UI and minimal control API.
- Does **not** download or render itself.
- Reads `jobs.db` + light filesystem stats for progress.
- Endpoints (illustrative):
  - `GET /` — status dashboard
  - `GET /partials/progress` — HTMX fragment (bars + current item)
  - `POST /control/start|pause|resume`
  - `GET /archive/...` — static/browse rendered archive (or reverse-proxy static files)

### Worker process (`onenote-worker`)

- On Start (or if already running and unpaused): ensure a run exists covering **all** Graph notebooks.
- Enumerate notebooks → sections → pages; enqueue missing work if needed; process **one page at a time**.
- Per page:
  1. Sync HTML + assets to `out/` (skip existing unless force flag in config).
  2. Path A render → `archive/.../page.html` + `page.pdf`.
  3. On failure: mark page failed, log, continue to next page.
- Respect Pause: finish current page, then stop claiming new ones until Resume.
- Optional: if `COMPARE_BC=true` in settings, also write B/C artifacts under `archive/_compare/...` after A succeeds.

### Shared state (`jobs.db`)

Suggested tables (logical):

- `runs` — id, status (`running|paused|completed|failed`), started_at, finished_at
- `pages` — run_id, notebook/section/page ids + display names, status (`pending|syncing|rendering|done|failed`), error, progress fields, timestamps
- `events` — append-only log lines for the UI tail

Progress derivation:

- Overall = done_pages / total_pages
- Notebook / section bars = aggregates of page rows
- Current page = the single `syncing` or `rendering` row

## UI

### Status home (`/`)

One composition, not a dashboard of unrelated widgets:

- Brand/title: **OneNote Archive**
- Run state badge: Running / Paused / Idle / Completed
- Controls: Start · Pause · Resume
- Progress:
  - Overall bar + counts (`342 / 1200 pages`)
  - Current notebook bar
  - Current section bar
  - Current page bar + stage label (`Syncing assets` / `Rendering PDF`)
- Current path text: `01 SFI > Biochemistry > Glycolysis…`
- Compact failure count + link to failures list
- Recent event log (last ~30 lines)

Styling: Tailwind CDN; expressive typography; subtle gradient background; clear progress bars (not generic purple SaaS chrome). Auto-refresh via HTMX (`hx-get` every 1s on the progress partial while running).

### Archive browse

- Index pages listing notebooks → sections → pages with badges (`synced`, `rendered`, `failed`).
- Links to `page.html` / `page.pdf` under `archive/`.

### Failures

- Table of failed pages with error snippet and Retry (re-queues those pages only).

## Pipeline details

Aligned with `docs/projects/onenote-full-archive/spec.md`:

1. **Sync** — Graph `?includeinkML=true`, multipart-aware, assets beside `page.html`, skip-if-exists.
2. **Render A** — preprocess → self-contained HTML + canvas ink → Playwright tall PDF.
3. **Indexes** — maintain `archive/index.html` (and per-notebook indexes) as pages complete (or batch at notebook end).

Rate limiting / OAuth: reuse existing `onenote_dl.helpers` + silent refresh (`offline_access`).

## Deploy (ares)

Replace the old single sync/dashboard units with:

| Unit | Command |
|------|---------|
| `onenote-web.service` | `uvicorn` / `python -m onenote_web` bound to `$(tailscale ip -4):8747` |
| `onenote-worker.service` | `python -m onenote_worker` |

- `Restart=always`, user lingering on.
- Secrets remain in `keys/` (gitignored).
- Mattermost: optional notify on run complete / crash (reuse existing helper).

## Error handling

- Graph 429: existing backoff; page stays `syncing` until success or terminal failure.
- OAuth refresh failure: pause run, surface error on status page, Mattermost notify.
- Playwright/render failure: mark page failed, continue.
- Worker crash: systemd restarts worker; run resumes from next `pending` page (current in-flight page reset to `pending` if lock expired).

## Testing

- Unit: progress aggregation from fake `pages` rows; pause stops claiming.
- Integration: fake Graph fixture → one notebook sync+render path marked done in DB.
- Manual: Start on ares, watch HTMX bars advance; Pause mid-notebook; Resume; open an archive PDF.

## Success criteria

1. Opening the Tailscale URL shows live, attractive progress for an automatic full-library run.
2. No notebook picker required; Start kicks off all notebooks in series.
3. `archive/` fills with Path A HTML+PDF; failures are visible and retryable.
4. Web restart does not kill worker progress; Pause/Resume work as specified.
