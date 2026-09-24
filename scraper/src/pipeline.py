import json
import os
import time
from datetime import datetime, timezone

from pydantic import ValidationError

from . import config
from .fetch import FetchError, fetch
from .models import BookRecord
from .parse import parse_book_detail, parse_catalogue_page


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_book_urls(max_pages: int = config.MAX_CATALOGUE_PAGES):
    """Stage 2: walk the catalogue's 'next' links, collecting every book detail
    URL along with the catalogue page it was found on. Stops after max_pages."""
    discovered = []  # list of (detail_url, source_page)
    seen = set()

    page_url = config.CATALOGUE_PAGE_URL.format(1)
    page_count = 0
    while page_url and page_count < max_pages:
        html = fetch(page_url)
        book_urls, next_url = parse_catalogue_page(html, page_url)
        for u in book_urls:
            if u not in seen:
                seen.add(u)
                discovered.append((u, page_url))
        page_count += 1
        page_url = next_url

    return discovered, page_count


def scrape_all(max_pages: int = config.MAX_CATALOGUE_PAGES, inject_fake_url: bool = False):
    """Stages 2-5: discover book URLs, fetch + parse + validate each detail
    page, and return (records, errors, run_report_dict). Per-page failures are
    isolated — one broken detail page never stops the rest of the run."""
    run_started = time.monotonic()
    started_at = _now_iso()

    discovered, pages_visited = collect_book_urls(max_pages=max_pages)

    if inject_fake_url:
        # Stage 5 checkpoint: prove failure isolation using a URL that does
        # not exist on the real site — never by hammering a real page.
        fake_page = config.CATALOGUE_PAGE_URL.format(1)
        discovered.append((
            "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html",
            fake_page,
        ))

    records_by_canonical = {}
    errors = []

    for detail_url, source_page in discovered:
        try:
            html = fetch(detail_url)
        except FetchError as exc:
            errors.append({
                "url": exc.url,
                "source_page": source_page,
                "stage": "fetch",
                "status_code": exc.status_code,
                "reason": exc.reason,
            })
            continue

        try:
            raw = parse_book_detail(html, detail_url)
        except Exception as exc:  # malformed page: isolate, don't crash the run
            errors.append({
                "url": detail_url,
                "source_page": source_page,
                "stage": "parse",
                "status_code": None,
                "reason": f"{type(exc).__name__}: {exc}",
            })
            continue

        raw["canonical_url"] = detail_url
        raw["source_page"] = source_page
        raw["fetched_at"] = _now_iso()

        try:
            record = BookRecord.model_validate(raw)
        except ValidationError as exc:
            errors.append({
                "url": detail_url,
                "source_page": source_page,
                "stage": "validate",
                "status_code": None,
                "reason": str(exc),
            })
            continue

        # Keyed by canonical_url so a rerun overwrites rather than duplicates.
        records_by_canonical[str(record.canonical_url)] = record

    records = list(records_by_canonical.values())
    duration_s = round(time.monotonic() - run_started, 2)

    report = {
        "started_at": started_at,
        "finished_at": _now_iso(),
        "duration_seconds": duration_s,
        "catalogue_pages_visited": pages_visited,
        "book_urls_discovered": len(discovered),
        "records_stored": len(records),
        "errors": len(errors),
        "error_detail": errors,
    }

    return records, errors, report


def write_output(records, errors, report):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    books_path = os.path.join(config.OUTPUT_DIR, "books.json")
    errors_path = os.path.join(config.OUTPUT_DIR, "errors.json")
    report_path = os.path.join(config.OUTPUT_DIR, "run-report.json")

    with open(books_path, "w", encoding="utf-8") as f:
        json.dump([json.loads(r.model_dump_json()) for r in records], f, indent=2, ensure_ascii=False)

    with open(errors_path, "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return books_path, errors_path, report_path
