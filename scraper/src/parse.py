import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

_RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_catalogue_page(html: str, page_url: str):
    """Given a catalogue listing page, return (book_detail_urls, next_page_url_or_None),
    both converted to absolute URLs via proper URL-joining (never string concatenation)."""
    soup = BeautifulSoup(html, "html.parser")

    book_urls = []
    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")
        if link and link.get("href"):
            book_urls.append(urljoin(page_url, link["href"]))

    next_link = soup.select_one("li.next a")
    next_url = urljoin(page_url, next_link["href"]) if next_link and next_link.get("href") else None

    return book_urls, next_url


def _price_to_float(text: str) -> float:
    match = re.search(r"[\d]+\.[\d]+", text)
    if not match:
        raise ValueError(f"could not parse a price out of {text!r}")
    return float(match.group(0))


def parse_book_detail(html: str, detail_url: str) -> dict:
    """Extract the raw field values from a book detail page. Returns a plain
    dict (not yet validated) so the caller can attach provenance fields before
    handing everything to the Pydantic schema."""
    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one("div.product_main h1").get_text(strip=True)

    rating_p = soup.select_one("p.star-rating")
    rating_word = next((c for c in rating_p["class"] if c in _RATING_WORDS), None)
    rating = _RATING_WORDS.get(rating_word, 0)

    image_el = soup.select_one("div.item.active img") or soup.select_one("#product_gallery img")
    image_url = urljoin(detail_url, image_el["src"])

    rows = {tr.find("th").get_text(strip=True): tr.find("td").get_text(strip=True)
            for tr in soup.select("table.table.table-striped tr")}

    price_text = rows.get("Price (incl. tax)", rows.get("Price (excl. tax)", ""))
    price_gbp = _price_to_float(price_text)

    availability_text = rows.get("Availability", "").strip()
    in_stock = "in stock" in availability_text.lower()

    upc = rows.get("UPC", "")

    breadcrumb_items = soup.select("ul.breadcrumb li a")
    category = breadcrumb_items[-1].get_text(strip=True) if breadcrumb_items else "Unknown"

    return {
        "title": title,
        "price_gbp": price_gbp,
        "availability_text": availability_text,
        "in_stock": in_stock,
        "rating": rating,
        "upc": upc,
        "category": category,
        "image_url": image_url,
    }
