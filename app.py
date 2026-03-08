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
    """
    Build all indexes from the loaded CSV rows.
    """
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


def ids_to_movies(record_ids, sort_results=True, limit=200):
    """
    Convert a list/set of record IDs into movie rows.
    """
    results = []

    for record_id in record_ids:
        movie = BY_ID.get(record_id)
        if movie is not None:
            results.append(movie)

    if sort_results:
        results.sort(key=lambda row: (row["Year"], row["Title"].lower(), row["ID"]))

    return results[:limit]


def parse_year_bounds(year_min_text, year_max_text):
    """
    Parse optional year bounds.
    """
    has_min = bool(year_min_text)
    has_max = bool(year_max_text)

    if not has_min and not has_max:
        return None, None, False

    if has_min and not has_max:
        year_value = int(year_min_text)
        return year_value, year_value, True

    if has_max and not has_min:
        year_value = int(year_max_text)
        return year_value, year_value, True

    y0 = int(year_min_text)
    y1 = int(year_max_text)

    min_year = min(y0, y1)
    max_year = max(y0, y1)

    return min_year, max_year, True


def combined_title_year_search(title_query, year_min_text, year_max_text, final_limit=200):
    """
    Combined search using:
    - TST for title prefix matching
    - B+ tree for year range matching

    The final result is the intersection of the two ID sets when both
    filters are present. If only one filter is provided, only that index is used.
    """
    normalized_title = title_query.strip() if title_query else ""
    min_year, max_year, has_year_filter = parse_year_bounds(year_min_text, year_max_text)

    has_title_filter = bool(normalized_title)

    if not has_title_filter and not has_year_filter:
        return [], "Enter a title prefix and/or a year filter."

    title_ids = None
    year_ids = None

    # Use the full dataset size as the retrieval cap from each index,
    # then apply the final UI limit after intersection/sorting.
    retrieval_limit = max(len(DATA), final_limit)

    if has_title_filter:
        title_ids = set(TST.prefix_search(normalized_title, limit=retrieval_limit))

    if has_year_filter:
        year_ids = set(BPTREE.search_range(min_year, max_year, limit=retrieval_limit))

    if has_title_filter and has_year_filter:
        # Intersect the two indexed result sets.
        matched_ids = title_ids & year_ids
        filter_desc = (
            f'title prefix "{normalized_title}" AND year range {min_year}..{max_year}'
        )
    elif has_title_filter:
        matched_ids = title_ids
        filter_desc = f'title prefix "{normalized_title}"'
    else:
        matched_ids = year_ids
        filter_desc = f"year range {min_year}..{max_year}"

    results = ids_to_movies(matched_ids, sort_results=True, limit=final_limit)
    return results, filter_desc


@app.route("/")
def home():
    return render_template(
        "index.html",
        mode="title_year",
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
        mode_value = "title_year"

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
        if mode == "title_year":
            results, filter_desc = combined_title_year_search(
                title_query=q,
                year_min_text=year_min,
                year_max_text=year_max,
                final_limit=200,
            )

            dt = (time.perf_counter() - t0) * 1000.0
            result_count = len(results)
            meta = (
                f"Combined indexed search ({filter_desc}) returned "
                f"{result_count} rows in {dt:.3f} ms."
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
            results = ids_to_movies(ids, sort_results=True, limit=50)

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
            results = ids_to_movies(ids, sort_results=True, limit=50)

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
            if not year_min and not year_max:
                return render_template(
                    "index.html",
                    mode=mode,
                    q=q,
                    year_min=year_min,
                    year_max=year_max,
                    results=[],
                    error=None,
                    meta="Provide year_min and/or year_max for B+ tree range search.",
                )

            min_year, max_year, _ = parse_year_bounds(year_min, year_max)
            ids = BPTREE.search_range(min_year, max_year, limit=200)
            results = ids_to_movies(ids, sort_results=True, limit=200)

            dt = (time.perf_counter() - t0) * 1000.0
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

    except ValueError:
        return render_template(
            "index.html",
            mode=mode,
            q=q,
            year_min=year_min,
            year_max=year_max,
            results=[],
            error="Year fields must be valid integers.",
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
