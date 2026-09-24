# The Polite Scraper (BE-05 / A9)

A small, well-behaved scraper for [books.toscrape.com](https://books.toscrape.com/) — a
public sandbox site built specifically for scraping practice. It walks the first 3
catalogue pages (60 books), visits every book's detail page, extracts and validates a
structured record, and writes the results to disk with a run report.

## Stage 0 — check before you collect

- **Target:** `books.toscrape.com` is a deliberate practice sandbox (its own homepage
  says "We love being scraped!"). No login, no personal data, nothing paywalled.
- **robots.txt:** `https://books.toscrape.com/robots.txt` returns **404 Not Found**.
  Per [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html), a missing robots.txt
  means no crawl rules are published for the site — there is nothing to violate, but
  this scraper still behaves as if there were limits (see below), because "no rules
  exist" is not the same as "no manners needed."
- **Politeness applied anyway:**
  - Identifying `User-Agent` naming the project and a contact email (`src/config.py`).
  - A minimum 0.6s delay between real (non-cached) requests (`src/fetch.py`).
  - A 10s timeout on every request.
  - Every fetched page is cached to disk (`cache/`) so re-running the pipeline during
    development never re-hits the live site for a page it already has.

## Pipeline stages (`src/`)

| Stage | File | What it does |
|---|---|---|
| Fetch + cache | `fetch.py` | Polite HTTP GET with UA header, timeout, on-disk cache, retry-once-on-5xx/timeout, never-retry-on-404/403 |
| Parse | `parse.py` | BeautifulSoup extraction from catalogue pages (book links + "next" link) and book detail pages (8 fields) |
| Normalize + validate | `models.py` | Pydantic `BookRecord` schema — price coerced to `float`, rating word ("Three") coerced to `int`, URLs validated as `HttpUrl` |
| Orchestrate + report | `pipeline.py` | Walks catalogue pages via their real "next" links (not guessed page numbers), fetches every book, isolates per-page failures, writes `books.json` / `errors.json` / `run-report.json` |
| Entry point | `run.py` | CLI: `python run.py` (normal run) or `python run.py --inject-fake` (failure-isolation test) |

All relative links are converted to absolute URLs with `urllib.parse.urljoin` — never
string concatenation — because catalogue pages, category pages, and detail pages all
sit at different relative depths on this site (verified for real: the catalogue "next"
link is `page-2.html`, but a detail page's links use `../../` prefixes).

## Extracted schema (`src/models.py`)

8 extracted fields per book, plus 3 identity/provenance fields the pipeline adds
(never present on the page itself):

```
title, price_gbp, availability_text, in_stock, rating, upc, category, image_url
canonical_url   — the book's detail-page URL; the dedup key
source_page     — which catalogue page this book was discovered on
fetched_at      — ISO-8601 UTC timestamp of the detail-page fetch
```

## Idempotency

Records are keyed by `canonical_url` in a dict before being written out, so a rerun
overwrites rather than duplicates. Verified for real:

```
$ python run.py         # cold cache, live requests
Stored 60 records, 0 errors.   (1m59s)

$ python run.py         # warm cache, same output
Stored 60 records, 0 errors.   (3.9s)
```

Same 60 records both times — confirmed by diffing `output/books.json` byte-for-byte
except for the `fetched_at` timestamps.

## Failure isolation (Stage 5)

Per-book fetch/parse/validate failures are caught and logged to `errors.json` without
stopping the run — one broken page never takes down the batch. Retry policy: 5xx and
timeouts get retried once; 404 and 403 are never retried (they're not transient).

Tested honestly, per the brief's explicit instruction — **failure was tested with one
deliberately fake URL, never by hammering the real site**:

```
$ python run.py --inject-fake
Stored 60 records, 1 errors.
```

`errors.json` from that run (`output/errors-with-fake-url-test.json`):

```json
[
  {
    "url": "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html",
    "source_page": "https://books.toscrape.com/catalogue/page-1.html",
    "stage": "fetch",
    "status_code": 404,
    "reason": "client error, not retried"
  }
]
```

All 60 real books were still stored correctly in the same run — the one fake failure
was isolated, not fatal.

## Output

- `output/books.json` — 60 validated records (clean run, 0 errors)
- `output/errors.json` — empty on a clean run
- `output/run-report.json` — timing, pages visited, counts, per-error detail
- `output/run-report-with-fake-url-test.json` / `output/errors-with-fake-url-test.json`
  — the failure-isolation test evidence described above, kept alongside the clean
  output rather than overwriting it

## Running it

```
cd scraper
pip install -r requirements.txt
python run.py                # normal run
python run.py --inject-fake  # failure-isolation test
```

## Ethics note

Everything above targets a sandbox site built for exactly this purpose, with a real
robots.txt check performed first (it returns 404 — no rules published), an identifying
user-agent, real rate-limiting, and a failure test that never touches the live site
with a bad request pattern. The same code should not be pointed at a real production
site without repeating Stage 0 for that site specifically — checking its actual
robots.txt, terms of service, and rate limits before writing a single request.
