"""Seeds report.db's books table from the real data collected in BE-05
(the polite scraper). Safe to run twice: it deletes all rows first, so a
second run leaves exactly one clean copy, never doubled.
"""
import json
import os

from db import get_connection, init_db

BOOKS_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "scraper", "output", "books.json"
)


def seed():
    init_db()
    with open(BOOKS_JSON, "r", encoding="utf-8") as f:
        books = json.load(f)

    conn = get_connection()
    conn.execute("DELETE FROM books")
    conn.executemany(
        "INSERT INTO books (title, price, rating, url) VALUES (?, ?, ?, ?)",
        [(b["title"], b["price_gbp"], b["rating"], b["canonical_url"]) for b in books],
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) AS n FROM books").fetchone()["n"]
    conn.close()
    print(f"Seeded {count} books from {os.path.basename(BOOKS_JSON)}")


if __name__ == "__main__":
    seed()
