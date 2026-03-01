import csv
import os
import time

from flask import Flask, render_template, request

from ternary_search import TernarySearch
from bloom_search import BloomFilterSearch
from bplus_search import BPlusSearch


def load_movies(csv_path):
    rows = []

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            movie = r

            movie_id_value = movie["ID"]
            year_value = movie["Year"]

            movie_id_int = int(movie_id_value)
            year_int = int(year_value)

            movie["ID"] = movie_id_int
            movie["Year"] = year_int

            rows.append(movie)

    return rows


app = Flask(__name__)

DATA = []
BY_ID = {}

# Search engines
TST = TernarySearch()
BLOOM = BloomFilterSearch(false_positive_rate=0.01)
BPTREE = BPlusSearch(order=6)


def build_indexes(rows):
    # Build BY_ID dictionary
    for r in rows:
        record_id = r["ID"]
        BY_ID[record_id] = r

    # Build TST index on Title
    for r in rows:
        title_value = r["Title"]
        record_id = r["ID"]

        TST.insert(title_value, record_id)

    # Build Bloom index on Title (exact)
    bloom_items = []

    for r in rows:
        record_id = r["ID"]
        title_value = r["Title"]

        item_tuple = (record_id, title_value)
        bloom_items.append(item_tuple)

    BLOOM.build(bloom_items)

    # Build B+ index on Year
    bplus_items = []

    for r in rows:
        record_id = r["ID"]
        year_value = r["Year"]

        item_tuple = (record_id, year_value)
        bplus_items.append(item_tuple)

    BPTREE.build(bplus_items)


@app.route("/")
def home():
    return render_template(
        "index.html",
        mode="tst",
        q="",
        year_min="",
        year_max="",
        results=None,
        error=None,
        meta=None,
    )


@app.route("/search")
def search():
    mode_value = request.args.get("mode")
    if mode_value is None:
        mode_value = "tst"

    mode = mode_value.strip().lower()

    q_value = request.args.get("q")
    if q_value is None:
        q_value = ""

    q = q_value.strip()

    year_min_value = request.args.get("year_min")
    if year_min_value is None:
        year_min_value = ""

    year_min = year_min_value.strip()

    year_max_value = request.args.get("year_max")
    if year_max_value is None:
        year_max_value = ""

    year_max = year_max_value.strip()

    t0 = time.perf_counter()

    try:
        if mode == "tst":
            if not q:
                return render_template(
                    "index.html",
                    mode=mode,
                    q=q,
                    year_min=year_min,
                    year_max=year_max,
                    results=[],
                    error=None,
                    meta="Enter a title prefix for TST search.",
                )

            ids = TST.prefix_search(q, limit=50)

            results = []

            for record_id in ids:
                movie = BY_ID[record_id]
                results.append(movie)

            dt = (time.perf_counter() - t0) * 1000.0

            result_count = len(results)
            meta = f"TST prefix search returned {result_count} rows in {dt:.3f} ms."

            return render_template(
                "index.html",
                mode=mode,
                q=q,
                year_min=year_min,
                year_max=year_max,
                results=results,
                error=None,
                meta=meta,
            )

        if mode == "bloom":
            if not q:
                return render_template(
                    "index.html",
                    mode=mode,
                    q=q,
                    year_min=year_min,
                    year_max=year_max,
                    results=[],
                    error=None,
                    meta="Enter a full title for Bloom membership search.",
                )

            ids, bloom_meta = BLOOM.search(q)

            results = []

            for record_id in ids:
                movie = BY_ID[record_id]
                results.append(movie)

            dt = (time.perf_counter() - t0) * 1000.0

            result_count = len(results)
            meta = f"{bloom_meta} ({result_count} rows) in {dt:.3f} ms."

            return render_template(
                "index.html",
                mode=mode,
                q=q,
                year_min=year_min,
                year_max=year_max,
                results=results,
                error=None,
                meta=meta,
            )

        if mode == "bptree":
            if not year_min or not year_max:
                return render_template(
                    "index.html",
                    mode=mode,
                    q=q,
                    year_min=year_min,
                    year_max=year_max,
                    results=[],
                    error=None,
                    meta="Provide year_min and year_max for B+ tree range search.",
                )

            y0 = int(year_min)
            y1 = int(year_max)

            ids = BPTREE.search_range(y0, y1, limit=200)

            results = []

            for record_id in ids:
                movie = BY_ID[record_id]
                results.append(movie)

            dt = (time.perf_counter() - t0) * 1000.0

            min_year = min(y0, y1)
            max_year = max(y0, y1)
            result_count = len(results)

            meta = (
                f"B+ tree range search {min_year}..{max_year} "
                f"returned {result_count} rows in {dt:.3f} ms."
            )

            return render_template(
                "index.html",
                mode=mode,
                q=q,
                year_min=year_min,
                year_max=year_max,
                results=results,
                error=None,
                meta=meta,
            )

        return render_template(
            "index.html",
            mode=mode,
            q=q,
            year_min=year_min,
            year_max=year_max,
            results=[],
            error=f"Unknown mode: {mode}",
            meta=None,
        )

    except Exception as e:
        return render_template(
            "index.html",
            mode=mode,
            q=q,
            year_min=year_min,
            year_max=year_max,
            results=[],
            error=str(e),
            meta=None,
        )


def init_app():
    csv_path = os.environ.get("MOVIES_CSV")

    if csv_path is None:
        csv_path = "movies.csv"

    rows = load_movies(csv_path)

    for movie in rows:
        DATA.append(movie)

    build_indexes(DATA)


init_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
