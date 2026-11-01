"""Render charts from data/books.csv and refresh the stats block in README.md.

Each chart is saved twice (charts/<name>-light.png, charts/<name>-dark.png)
so the README can follow the viewer's GitHub theme.

Usage: uv run scripts/charts.py
"""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "books.csv"
CHARTS = ROOT / "charts"
README = ROOT / "README.md"

THEMES = {
    "light": {
        "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
        "grid": "#e1e0d9", "axis": "#c3c2b7", "accent": "#2a78d6", "accent2": "#eb6834",
        "negative": "#e34948",
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
        "grid": "#2c2c2a", "axis": "#383835", "accent": "#3987e5", "accent2": "#d95926",
        "negative": "#e66767",
    },
}


def short_title(title: str) -> str:
    return re.split(r"[:(]", title)[0].strip()


def new_figure(t: dict, title: str, subtitle: str, size=(9, 5.2)):
    fig, ax = plt.subplots(figsize=size, dpi=150)
    fig.patch.set_facecolor(t["surface"])
    ax.set_facecolor(t["surface"])
    fig.text(0.02, 0.965, title, fontsize=15, fontweight="bold", color=t["ink"], va="top")
    fig.text(0.02, 0.905, subtitle, fontsize=10.5, color=t["ink2"], va="top")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["axis"])
    ax.tick_params(colors=t["muted"], labelsize=9.5, length=0)
    ax.set_axisbelow(True)
    return fig, ax


def save(fig, name: str, mode: str) -> None:
    fig.savefig(CHARTS / f"{name}-{mode}.png", facecolor=fig.get_facecolor())
    plt.close(fig)


def hbar_labels(ax, t, bars, fmt):
    for bar in bars:
        w = bar.get_width()
        ax.text(w, bar.get_y() + bar.get_height() / 2, f"  {fmt(w)}",
                va="center", fontsize=9.5, color=t["ink2"])


def books_by_category(df, t, mode):
    counts = df["category"].value_counts().sort_values()
    fig, ax = new_figure(t, "What I read", f"{len(df)} books by category")
    bars = ax.barh(counts.index, counts.values, height=0.55, color=t["accent"])
    hbar_labels(ax, t, bars, lambda v: f"{v:.0f}")
    ax.tick_params(axis="y", colors=t["ink2"], labelsize=10)
    ax.xaxis.grid(True, color=t["grid"], linewidth=1)
    ax.set_xlim(0, counts.max() * 1.12)
    fig.subplots_adjust(left=0.27, right=0.97, top=0.84, bottom=0.08)
    save(fig, "books-by-category", mode)


def rating_vs_goodreads(df, t, mode, n=5):
    rated = df.dropna(subset=["my_rating"]).copy()
    rated["diff"] = rated["my_rating"] - rated["avg_rating"]

    # Most generous takes on top, harshest at the bottom, with an empty row between.
    generous = rated.nlargest(n, "diff")
    harsh = rated.nsmallest(n, "diff").iloc[::-1]
    rows = list(generous.itertuples()) + [None] + list(harsh.itertuples())
    y = np.arange(len(rows))[::-1]

    fig, ax = new_figure(t, "Me vs. Goodreads",
                         f"The {n} books I rated furthest above and below the Goodreads average",
                         size=(9, 5.6))
    ax.axvline(0, color=t["axis"], linewidth=1)
    for yi, row in zip(y, rows):
        if row is None:
            continue
        up = row.diff > 0
        ax.barh(yi, row.diff, height=0.55, color=t["accent"] if up else t["negative"])
        # Title on the zero side opposite the bar, stars at the bar tip.
        title = short_title(row.title)
        title = title if len(title) <= 34 else title[:33] + "…"
        ax.text(-0.06 if up else 0.06, yi, title, ha="right" if up else "left", va="center",
                fontsize=9.5, color=t["ink"])
        ax.text(row.diff + (0.06 if up else -0.06), yi,
                f"{row.my_rating:.0f}★ vs {row.avg_rating:.2f}★", ha="left" if up else "right",
                va="center", fontsize=9, color=t["ink2"])

    lim = rated["diff"].abs().max() + 1.3
    ax.set_xlim(-lim, lim)
    ax.set_yticks([])
    ax.xaxis.grid(True, color=t["grid"], linewidth=1)
    ax.set_xticks(range(-int(lim), int(lim) + 1),
                  [f"{v:+d}★" if v else "0" for v in range(-int(lim), int(lim) + 1)])
    ax.set_xlabel("← I liked it less          My rating minus Goodreads average          I liked it more →",
                  color=t["muted"], fontsize=9.5)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.85, bottom=0.11)
    save(fig, "rating-vs-goodreads", mode)


def rating_by_category(df, t, mode, min_books=3):
    g = df.dropna(subset=["my_rating"]).groupby("category")["my_rating"].agg(["mean", "size"])
    g = g[g["size"] >= min_books].sort_values("mean")
    fig, ax = new_figure(t, "Favorite topics",
                         f"My average rating by category (categories with {min_books}+ rated books)")
    bars = ax.barh(g.index, g["mean"], height=0.55, color=t["accent"])
    for bar, n in zip(bars, g["size"]):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f"  {bar.get_width():.1f}★  ({n} books)", va="center", fontsize=9.5, color=t["ink2"])
    ax.tick_params(axis="y", colors=t["ink2"], labelsize=10)
    ax.xaxis.grid(True, color=t["grid"], linewidth=1)
    ax.set_xlim(0, 5.9)
    ax.set_xticks(range(0, 6), [f"{i}★" for i in range(0, 6)])
    fig.subplots_adjust(left=0.27, right=0.97, top=0.84, bottom=0.08)
    save(fig, "rating-by-category", mode)


def books_per_year(df, t, mode):
    years = pd.to_datetime(df["date_added"]).dt.year.value_counts().sort_index()
    fig, ax = new_figure(t, "Books per year", "By date added to Goodreads, since I started using Goodreads",
                         size=(9, 4.6))
    bars = ax.bar(years.index.astype(str), years.values, width=0.55, color=t["accent"])
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():.0f}",
                ha="center", va="bottom", fontsize=9.5, color=t["ink2"])
    ax.yaxis.grid(True, color=t["grid"], linewidth=1)
    ax.tick_params(axis="x", colors=t["ink2"], labelsize=10)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.82, bottom=0.09)
    save(fig, "books-per-year", mode)


def publication_decades(df, t, mode, first_decade=1970):
    # Older books are rare, so they share one "Before" bar instead of a long empty axis.
    decade = (df["year_published"].dropna() // 10 * 10).astype(int).clip(lower=first_decade - 10)
    counts = decade.value_counts().reindex(range(first_decade - 10, decade.max() + 10, 10), fill_value=0)
    labels = [f"Before {first_decade}" if d < first_decade else f"{d}s" for d in counts.index]
    fig, ax = new_figure(t, "Book age", "Books by decade of original publication",
                         size=(9, 4.6))
    bars = ax.bar(labels, counts.values, width=0.55, color=t["accent"])
    for bar in bars:
        if bar.get_height():
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():.0f}",
                    ha="center", va="bottom", fontsize=9.5, color=t["ink2"])
    ax.yaxis.grid(True, color=t["grid"], linewidth=1)
    ax.tick_params(axis="x", colors=t["ink2"], labelsize=10)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.82, bottom=0.09)
    save(fig, "publication-decades", mode)


def stats_markdown(df) -> str:
    finished = df[df["status"] == "read"]
    rated = df.dropna(subset=["my_rating"]).copy()
    rated["diff"] = rated["my_rating"] - rated["avg_rating"]
    harshest = rated.loc[rated["diff"].idxmin()]
    longest = finished.loc[finished["pages"].idxmax()]
    oldest = df.loc[df["year_published"].idxmin()]
    top_author, top_author_n = df["author"].value_counts().head(1).items().__next__()
    dnf = df[df["status"] == "did-not-finish"]

    rows = [
        ("Books on the shelf", f"{len(df)}"),
        ("Finished", f"{len(finished)}"),
        ("Did not finish", f"{len(dnf)} ({len(dnf) / len(df):.0%})"),
        ("Pages read", f"{int(finished['pages'].sum()):,}"),
        ("Average book length", f"{finished['pages'].mean():.0f} pages"),
        ("My average rating", f"{rated['my_rating'].mean():.2f}★ (Goodreads: {rated['avg_rating'].mean():.2f}★)"),
        ("Favorites", f"{int(df['favorite'].sum())}"),
        ("Most-read author", f"{top_author} ({top_author_n} books)"),
        ("Longest finished book", f"*{short_title(longest['title'])}*, {int(longest['pages'])} pages"),
        ("Oldest book", f"*{short_title(oldest['title'])}* ({int(oldest['year_published'])})"),
        ("Hottest take", f"*{short_title(harshest['title'])}*: I gave it {int(harshest['my_rating'])}★, "
                         f"Goodreads says {harshest['avg_rating']:.2f}★"),
    ]
    lines = ["| Stat | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows]
    return "\n".join(lines)


def update_readme(stats: str) -> None:
    text = README.read_text()
    new = re.sub(r"(<!-- stats:start -->\n).*?(<!-- stats:end -->)",
                 lambda m: m.group(1) + stats + "\n" + m.group(2), text, flags=re.S)
    README.write_text(new)


def main() -> None:
    df = pd.read_csv(DATA)
    CHARTS.mkdir(exist_ok=True)
    for mode, t in THEMES.items():
        for chart in (books_by_category, rating_vs_goodreads, rating_by_category,
                      books_per_year, publication_decades):
            chart(df, t, mode)
    stats = stats_markdown(df)
    if README.exists():
        update_readme(stats)
    print(stats)


if __name__ == "__main__":
    main()
