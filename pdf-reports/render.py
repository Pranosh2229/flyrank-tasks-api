from datetime import date, datetime

from playwright.sync_api import sync_playwright

from db import get_connection


def _row(book: dict) -> str:
    return (
        f"<tr><td>{book['title']}</td><td>&pound;{book['price']:.2f}</td>"
        f"<td>{book['rating']}</td></tr>"
    )


def build_html(report: dict, all_books: list[dict]) -> str:
    top5_rows = "".join(_row(b) for b in report["top_5_expensive"])
    all_rows = "".join(_row(b) for b in all_books)
    rating_rows = "".join(
        f"<tr><td>{r['rating']} star</td><td>{r['count']}</td></tr>" for r in report["by_rating"]
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 18mm 14mm; }}
  body {{ font-family: Helvetica, Arial, sans-serif; color: #111827; font-size: 11px; }}
  h1 {{ font-size: 20px; margin-bottom: 2px; }}
  .date {{ color: #6b7280; font-size: 11px; margin-bottom: 18px; }}
  .totals {{ display: flex; gap: 24px; margin-bottom: 20px; }}
  .stat {{ border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px 16px; }}
  .stat .label {{ color: #6b7280; font-size: 10px; text-transform: uppercase; }}
  .stat .value {{ font-size: 20px; font-weight: bold; }}
  h2 {{ font-size: 14px; margin-top: 22px; margin-bottom: 8px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead {{ display: table-header-group; }}
  th {{ text-align: left; background: #f9fafb; padding: 5px 8px; font-size: 10px; text-transform: uppercase; color: #6b7280; border-bottom: 1px solid #e5e7eb; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid #f3f4f6; }}
  tr {{ break-inside: avoid; }}
</style>
</head>
<body>
  <h1>Books to Scrape &mdash; Catalogue Report</h1>
  <div class="date">Generated {date.today().isoformat()}</div>

  <div class="totals">
    <div class="stat"><div class="label">Total books</div><div class="value">{report['total_books']}</div></div>
    <div class="stat"><div class="label">Average price</div><div class="value">&pound;{report['average_price']:.2f}</div></div>
  </div>

  <h2>Top 5 most expensive</h2>
  <table>
    <thead><tr><th>Title</th><th>Price</th><th>Rating</th></tr></thead>
    <tbody>{top5_rows}</tbody>
  </table>

  <h2>Books by star rating</h2>
  <table>
    <thead><tr><th>Rating</th><th>Count</th></tr></thead>
    <tbody>{rating_rows}</tbody>
  </table>

  <h2>All books ({len(all_books)})</h2>
  <table>
    <thead><tr><th>Title</th><th>Price</th><th>Rating</th></tr></thead>
    <tbody>{all_rows}</tbody>
  </table>
</body>
</html>
"""


def render_pdf(html: str, output_path: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=output_path, format="A4", print_background=True)
        browser.close()


def generate_report_pdf(output_path: str) -> dict:
    from queries import get_report_data

    report = get_report_data()
    conn = get_connection()
    all_books = [dict(r) for r in conn.execute("SELECT title, price, rating, url FROM books ORDER BY title").fetchall()]
    conn.close()

    html = build_html(report, all_books)
    render_pdf(html, output_path)
    return report


if __name__ == "__main__":
    import os

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "test.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    generate_report_pdf(out)
    print(f"Wrote {out} at {datetime.now().isoformat()}")
