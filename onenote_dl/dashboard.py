"""Persistent OneNote sync status dashboard (Tailscale-bound)."""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

import definitions


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ONENOTE_DASHBOARD_", extra="ignore")

    host: str = Field(default="127.0.0.1", description="Bind address (Tailscale IP on ares)")
    port: int = Field(default=8747, ge=1024, le=65535)
    refresh_seconds: int = Field(default=5, ge=1, le=300)


SETTINGS = Settings()
ROOT = Path(definitions.ROOT_DIR)
LOG_PATH = ROOT / "onenote_sync.log"
TOKEN_PATH = Path(definitions.TOKEN_PATH)
OUT_DIR = Path(definitions.OUT_DIR)


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def _sync_running() -> tuple[bool, str]:
    out = _run(["pgrep", "-af", "onenote_dl.download_onenote"])
    if not out:
        return False, ""
    for line in out.splitlines():
        if "download_onenote" in line and "pgrep" not in line:
            return True, line
    return True, out.splitlines()[0]


def _du_human(path: Path) -> str:
    out = _run(["du", "-sh", str(path)])
    return out.split("\t")[0] if out else "—"


def _file_count(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for _root, _dirs, files in os.walk(path):
        total += len(files)
    return total


def _token_info() -> dict:
    if not TOKEN_PATH.exists():
        return {"present": False}
    try:
        data = json.loads(TOKEN_PATH.read_text())
        exp = data.get("expiration")
        minutes = None
        if exp:
            try:
                from dateutil import parser

                minutes = (parser.parse(exp) - datetime.now()).total_seconds() / 60
            except Exception:
                minutes = None
        return {
            "present": True,
            "has_refresh": bool(data.get("refresh_token")),
            "scope": data.get("scope", ""),
            "expiration": exp,
            "minutes_left": minutes,
        }
    except Exception as e:
        return {"present": True, "error": str(e)}


def _log_tail(n: int = 40) -> list[str]:
    if not LOG_PATH.exists():
        return []
    try:
        raw = LOG_PATH.read_bytes()[-12000:]
        text = raw.decode("utf-8", errors="replace").replace("\r", "\n")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return lines[-n:]
    except Exception:
        return []


def _parse_progress(lines: list[str]) -> dict:
    notebook = section = page = None
    for ln in lines:
        m = re.search(r"------NOTEBOOK:\s*(.+?)------", ln)
        if m:
            notebook = m.group(1).strip()
        m = re.search(r"^(.+?)\s*>\s*(.+?)\s*\(ID:", ln)
        if m:
            notebook = m.group(1).strip()
            section = m.group(2).strip()
        m = re.search(r"^\s*(.+?):\s+(\d+)%\|", ln)
        if m and "files/s" in ln:
            page = f"{m.group(1).strip()} ({m.group(2)}%)"
    return {"notebook": notebook, "section": section, "page": page}


def gather_status() -> dict:
    running, proc = _sync_running()
    lines = _log_tail()
    progress = _parse_progress(lines)
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "running": running,
        "process": proc,
        "out_size": _du_human(OUT_DIR),
        "out_files": _file_count(OUT_DIR),
        "token": _token_info(),
        "progress": progress,
        "log_tail": lines,
        "host": SETTINGS.host,
        "port": SETTINGS.port,
    }


def render_html(status: dict) -> str:
    running = status["running"]
    badge = "RUNNING" if running else "STOPPED"
    badge_color = "#1f7a3a" if running else "#8a1f1f"
    tok = status["token"]
    if not tok.get("present"):
        tok_html = "<span class='bad'>missing</span>"
    elif tok.get("error"):
        tok_html = f"<span class='bad'>{html.escape(tok['error'])}</span>"
    else:
        mins = tok.get("minutes_left")
        mins_s = f"{mins:.0f} min left" if mins is not None else "unknown expiry"
        refresh = "yes" if tok.get("has_refresh") else "no"
        tok_html = (
            f"refresh_token={refresh} · {html.escape(str(tok.get('expiration', '')))} "
            f"({html.escape(mins_s)})"
        )

    prog = status["progress"]
    log_block = "\n".join(html.escape(ln) for ln in status["log_tail"])
    refresh_s = SETTINGS.refresh_seconds

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta http-equiv="refresh" content="{refresh_s}"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>OneNote Sync · ares</title>
  <style>
    :root {{
      --bg: #0f1419;
      --panel: #1a222c;
      --text: #e7ecf1;
      --muted: #9aa7b5;
      --accent: #5b9fd4;
      --line: #2a3542;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: "IBM Plex Mono", "SF Mono", Menlo, monospace;
      background:
        radial-gradient(1200px 600px at 10% -10%, #1c3348 0%, transparent 55%),
        var(--bg);
      color: var(--text); min-height: 100vh; padding: 2rem;
    }}
    h1 {{ font-size: 1.6rem; font-weight: 600; margin: 0 0 .35rem; letter-spacing: -0.02em; }}
    .sub {{ color: var(--muted); margin-bottom: 1.5rem; font-size: .9rem; }}
    .badge {{
      display: inline-block; padding: .2rem .55rem; border-radius: 4px;
      background: {badge_color}; color: white; font-size: .75rem; font-weight: 700;
      letter-spacing: .04em;
    }}
    .grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem; margin-bottom: 1.25rem;
    }}
    .tile {{
      background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
      padding: 1rem 1.1rem;
    }}
    .label {{ color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; }}
    .value {{ margin-top: .35rem; font-size: 1.05rem; word-break: break-word; }}
    pre {{
      background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
      padding: 1rem; overflow: auto; max-height: 55vh; font-size: .78rem; line-height: 1.45;
      white-space: pre-wrap;
    }}
    .bad {{ color: #e07070; }}
  </style>
</head>
<body>
  <h1>OneNote Downloader</h1>
  <div class="sub">ares · auto-refresh {refresh_s}s · generated {html.escape(status['generated_at'])}</div>

  <div class="grid">
    <div class="tile">
      <div class="label">Status</div>
      <div class="value"><span class="badge">{badge}</span></div>
    </div>
    <div class="tile">
      <div class="label">Downloaded</div>
      <div class="value">{status['out_files']:,} files · {html.escape(status['out_size'])}</div>
    </div>
    <div class="tile">
      <div class="label">Notebook / section</div>
      <div class="value">{html.escape(prog.get('notebook') or '—')}<br/>{html.escape(prog.get('section') or '—')}</div>
    </div>
    <div class="tile">
      <div class="label">Current page</div>
      <div class="value">{html.escape(prog.get('page') or '—')}</div>
    </div>
    <div class="tile" style="grid-column: 1 / -1;">
      <div class="label">OAuth token</div>
      <div class="value">{tok_html}</div>
    </div>
  </div>

  <div class="label" style="margin-bottom:.4rem;">Recent log</div>
  <pre>{log_block or '(log empty)'}</pre>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path not in ("/", "/index.html", "/status"):
            self.send_error(404)
            return

        status = gather_status()
        if path == "/status":
            body = json.dumps(status, indent=2).encode()
            ctype = "application/json"
        else:
            body = render_html(status).encode()
            ctype = "text/html; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer((SETTINGS.host, SETTINGS.port), Handler)
    print(f"OneNote dashboard on http://{SETTINGS.host}:{SETTINGS.port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
