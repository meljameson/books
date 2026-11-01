"""Turn the raw Goodreads export into a work-safe data/books.csv.

Removes personal subcategories and all free-text fields (reviews, notes),
and fixes columns that the spreadsheet round-trip mangled.

Usage: uv run scripts/clean.py ["path/to/raw.csv"]
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "books - Sheet4.csv"
OUT = ROOT / "data" / "books.csv"

EXCLUDED_SUBCATEGORIES = {
    "Romantic relationships & attachment",
    "Sexuality & intimacy",
    "Trauma, family wounds & recovery",
}

EXCLUDED_CATEGORIES = {
    "Psychology & mental health",
}


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    excluded = raw["Subcategory"].isin(EXCLUDED_SUBCATEGORIES) | raw["Category"].isin(EXCLUDED_CATEGORIES)
    df = raw[~excluded].copy()

    # "Date Added" has "#########" cells from a too-narrow spreadsheet column;
    # the "Table Date Added" copy is complete.
    added = pd.to_datetime(df["Table Date Added"], format="%d-%b-%y")

    # Goodreads leaves "Original Publication Year" blank for some books.
    year = df["Original Publication Year"].fillna(df["Year Published"])

    rating = pd.to_numeric(df["My Rating"]).astype("Int64")

    return pd.DataFrame({
        "title": df["Title"],
        "author": df["Author"],
        "category": df["Category"],
        "subcategory": df["Subcategory"],
        "my_rating": rating.where(rating > 0),  # 0 means unrated
        "avg_rating": pd.to_numeric(df["Average Rating"]),
        "pages": pd.to_numeric(df["Number of Pages"]).astype("Int64"),
        "year_published": pd.to_numeric(year).astype("Int64"),
        "date_added": added.dt.date,
        "status": df["Exclusive Shelf"],
        "favorite": df["Bookshelves"].fillna("").str.contains("favorites"),
        "binding": df["Binding"],
        "publisher": df["Publisher"],
        "isbn13": df["ISBN13"],
    }).sort_values(["category", "subcategory", "title"])


def main() -> None:
    raw_path = Path(sys.argv[1]) if len(sys.argv) > 1 else RAW
    raw = pd.read_csv(raw_path, dtype=str)
    books = clean(raw)
    OUT.parent.mkdir(exist_ok=True)
    books.to_csv(OUT, index=False)
    print(f"Kept {len(books)} of {len(raw)} books -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
