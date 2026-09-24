from db import get_connection


def get_report_data() -> dict:
    """One function, one report: total books, average price, top 5 most
    expensive, and a count per star rating. Every number here comes from
    the database -- nothing is computed in Python."""
    conn = get_connection()

    total_books = conn.execute("SELECT COUNT(*) AS n FROM books").fetchone()["n"]

    average_price = conn.execute("SELECT AVG(price) AS avg_price FROM books").fetchone()["avg_price"]

    top_5_expensive = [
        dict(row)
        for row in conn.execute(
            "SELECT title, price, rating, url FROM books ORDER BY price DESC LIMIT 5"
        ).fetchall()
    ]

    by_rating = [
        dict(row)
        for row in conn.execute(
            "SELECT rating, COUNT(*) AS count FROM books GROUP BY rating ORDER BY rating DESC"
        ).fetchall()
    ]

    conn.close()

    return {
        "total_books": total_books,
        "average_price": round(average_price, 2) if average_price is not None else 0,
        "top_5_expensive": top_5_expensive,
        "by_rating": by_rating,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(get_report_data(), indent=2))
