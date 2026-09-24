"""Entry point for the polite scraper (BE-05).

Usage:
    python run.py                # normal run: 3 catalogue pages, all book detail pages
    python run.py --inject-fake  # same, plus one deliberately broken URL, to prove
                                  # failure isolation (never run against a real page)
"""
import argparse

from src.pipeline import scrape_all, write_output


def main():
    parser = argparse.ArgumentParser(description="The Polite Scraper — books.toscrape.com")
    parser.add_argument("--inject-fake", action="store_true",
                         help="add one nonexistent URL to the run to test failure handling")
    args = parser.parse_args()

    records, errors, report = scrape_all(inject_fake_url=args.inject_fake)
    books_path, errors_path, report_path = write_output(records, errors, report)

    print(f"Stored {len(records)} records, {len(errors)} errors.")
    print(f"  {books_path}")
    print(f"  {errors_path}")
    print(f"  {report_path}")


if __name__ == "__main__":
    main()
