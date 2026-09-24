import os

# Books to Scrape (books.toscrape.com) is a public sandbox site built
# specifically for scraping practice — no login, no personal data, no
# robots.txt restrictions (the site returns 404 for /robots.txt, which
# per RFC 9309 means no crawl rules are defined for it).
BASE_URL = "https://books.toscrape.com/"
CATALOGUE_PAGE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
MAX_CATALOGUE_PAGES = 3

USER_AGENT = (
    "FlyRankInternPoliteScraper/1.0 "
    "(+educational internship project; contact: kalaimagalnithya.a@gmail.com)"
)
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.6  # minimum gap between real (non-cached) requests

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(_ROOT, "cache")
OUTPUT_DIR = os.path.join(_ROOT, "output")
