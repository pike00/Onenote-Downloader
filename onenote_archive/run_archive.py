#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4>=4.12",
#     "playwright>=1.40",
# ]
# ///
"""Render OneNote Graph cache (out/) into human-readable archive/."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from onenote_archive.catalog import PageRef, iter_pages
from onenote_archive.indexes import write_indexes
from onenote_archive.preprocess import prepare_page, sanitize_title
from onenote_archive.render_a import render_path_a

PAGE_ID_MARKER = ".page_id"


def page_id_suffix(page_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]", "", page_id)
    return safe[-8:] if len(safe) >= 8 else safe or "page"


def _read_stored_page_id(dest_dir: Path) -> str | None:
    marker = dest_dir / PAGE_ID_MARKER
    if not marker.is_file():
        return None
    return marker.read_text(encoding="utf-8").strip() or None


def _write_page_id(dest_dir: Path, page_id: str) -> None:
    (dest_dir / PAGE_ID_MARKER).write_text(page_id, encoding="utf-8")


def _dest_needs_collision_suffix(path: Path, page_id: str, claimed: dict[Path, str]) -> bool:
    if path in claimed and claimed[path] != page_id:
        return True
    if not path.is_dir():
        return False
    stored = _read_stored_page_id(path)
    if stored is None:
        return True
    return stored != page_id


def resolve_dest_dir(
    archive_root: Path,
    ref: PageRef,
    claimed: dict[Path, str],
) -> Path:
    base = (
        archive_root
        / sanitize_title(ref.notebook_name)
        / sanitize_title(ref.section_name)
        / sanitize_title(ref.page_title)
    )
    dest = base
    if _dest_needs_collision_suffix(dest, ref.page_id, claimed):
        dest = base.parent / f"{base.name}-{page_id_suffix(ref.page_id)}"

    claimed[dest] = ref.page_id
    return dest


def should_skip(dest_dir: Path, *, skip_pdf: bool, force: bool) -> bool:
    if force:
        return False
    html_path = dest_dir / "page.html"
    if not html_path.is_file():
        return False
    if skip_pdf:
        return True
    return (dest_dir / "page.pdf").is_file()


def _append_failure(failures_log: Path, ref: PageRef, message: str) -> None:
    failures_log.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
        f"{ts}\t{ref.notebook_name}\t{ref.section_name}\t{ref.page_title}\t"
        f"{ref.page_id}\t{message}\n"
    )
    with failures_log.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _process_page(
    ref: PageRef,
    dest_dir: Path,
    archive_root: Path,
    *,
    skip_pdf: bool,
    force: bool,
    failures_log: Path,
) -> str:
    rel = dest_dir.relative_to(archive_root)
    if should_skip(dest_dir, skip_pdf=skip_pdf, force=force):
        print(f"skip  {rel}")
        return "skip"

    try:
        prepared = prepare_page(ref.page_html, dest_dir)
        result = render_path_a(prepared, dest_dir, skip_pdf=skip_pdf)
        if not result.ok:
            _append_failure(failures_log, ref, result.error or "render failed")
            print(f"FAIL  {rel}: {result.error}")
            return "fail"

        _write_page_id(dest_dir, ref.page_id)
        print(f"ok    {rel}")
        return "ok"
    except Exception as exc:  # noqa: BLE001
        _append_failure(failures_log, ref, str(exc))
        print(f"FAIL  {rel}: {exc}")
        return "fail"


def run_archive(
    out_dir: Path,
    archive_root: Path,
    *,
    notebook_filter: str | None = None,
    title_filter: str | None = None,
    skip_pdf: bool = False,
    force: bool = False,
    limit: int | None = None,
) -> None:
    archive_root.mkdir(parents=True, exist_ok=True)
    failures_log = archive_root / "failures.log"
    claimed: dict[Path, str] = {}
    collected: list[tuple[PageRef, Path]] = []
    processed = 0
    ok_count = 0
    skip_count = 0
    fail_count = 0

    for ref in iter_pages(out_dir):
        if notebook_filter and notebook_filter.lower() not in ref.notebook_name.lower():
            continue
        if title_filter and title_filter.lower() not in ref.page_title.lower():
            continue

        dest_dir = resolve_dest_dir(archive_root, ref, claimed)

        outcome = _process_page(
            ref,
            dest_dir,
            archive_root,
            skip_pdf=skip_pdf,
            force=force,
            failures_log=failures_log,
        )
        if (dest_dir / "page.html").is_file():
            collected.append((ref, dest_dir))
        if outcome == "ok":
            ok_count += 1
        elif outcome == "skip":
            skip_count += 1
        else:
            fail_count += 1

        processed += 1
        if limit is not None and processed >= limit:
            break

    refs, dests = zip(*collected, strict=False) if collected else ([], [])
    write_indexes(archive_root, list(refs), list(dests))
    print(
        f"done: processed={processed} ok={ok_count} skipped={skip_count} failed={fail_count}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "out",
        help="Graph cache root (default: repo out/)",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "archive",
        help="Archive output root (default: repo archive/)",
    )
    parser.add_argument(
        "--notebook",
        metavar="SUBSTR",
        help="Only process notebooks whose name contains SUBSTR",
    )
    parser.add_argument(
        "--title",
        metavar="SUBSTR",
        help="Only process pages whose title contains SUBSTR",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Write HTML only; skip Playwright PDF export",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild pages even when outputs already exist",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Process at most N pages (smoke tests)",
    )
    args = parser.parse_args(argv)

    if not args.out.is_dir():
        print(f"error: --out not found: {args.out}", file=sys.stderr)
        return 1

    run_archive(
        args.out,
        args.archive,
        notebook_filter=args.notebook,
        title_filter=args.title,
        skip_pdf=args.skip_pdf,
        force=args.force,
        limit=args.limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
