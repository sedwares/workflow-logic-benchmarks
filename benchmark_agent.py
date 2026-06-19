"""
agents/benchmark_agent.py  (data_tool_reviews niche only)

The credibility engine. Instead of charting numbers found on the web,
this agent runs REAL benchmarks on your machine against a reference
dataset (NYC TLC yellow taxi trips) and produces the chart_data that
feeds the rest of the pipeline.

Why this matters:
- vendor benchmarks are marketing; yours are reproducible
- "we ran it, here's the wall-clock time and the bill" is content nobody
  can call inauthentic, and practitioners actually trust
- every benchmark doubles as a portfolio artifact (publish the harness!)

Built-in scenarios benchmark local engines (DuckDB, pandas, Polars,
SQLite) on identical queries. Cloud tools (Snowflake, BigQuery, Athena)
get a manual-entry path: you run them yourself, paste the numbers, and
the agent records cost + latency with full methodology notes.
"""
import json
import os
import time
import urllib.request

from models import VideoJob, Stage

DATA_URL = ("https://d37ci6vzurychx.cloudfront.net/trip-data/"
            "yellow_tripdata_2024-01.parquet")          # ~48MB, ~3M rows
DATA_PATH = "data/yellow_tripdata_2024-01.parquet"

# The reference workload: same logical query for every engine.
QUERY_DESC = ("avg fare, trip count, and p95 distance grouped by "
              "passenger_count, filtered to trips > 1 mile")


def ensure_dataset() -> str:
    if not os.path.exists(DATA_PATH):
        os.makedirs("data", exist_ok=True)
        print(f"downloading reference dataset -> {DATA_PATH}")
        urllib.request.urlretrieve(DATA_URL, DATA_PATH)
    return DATA_PATH


def _timed(fn) -> float:
    t0 = time.perf_counter()
    fn()
    return round(time.perf_counter() - t0, 3)


# ------------------------- engine implementations --------------------------

def bench_duckdb(path: str) -> float:
    import duckdb
    sql = f"""
        SELECT passenger_count, COUNT(*) n, AVG(fare_amount) avg_fare,
               QUANTILE_CONT(trip_distance, 0.95) p95_dist
        FROM read_parquet('{path}')
        WHERE trip_distance > 1
        GROUP BY passenger_count"""
    return _timed(lambda: duckdb.sql(sql).fetchall())


def bench_polars(path: str) -> float:
    import polars as pl
    def run():
        (pl.scan_parquet(path)
           .filter(pl.col("trip_distance") > 1)
           .group_by("passenger_count")
           .agg(n=pl.len(),
                avg_fare=pl.col("fare_amount").mean(),
                p95_dist=pl.col("trip_distance").quantile(0.95))
           .collect())
    return _timed(run)


def bench_pandas(path: str) -> float:
    import pandas as pd
    def run():
        df = pd.read_parquet(path)
        (df[df.trip_distance > 1]
           .groupby("passenger_count")
           .agg(n=("fare_amount", "size"),
                avg_fare=("fare_amount", "mean"),
                p95_dist=("trip_distance", lambda s: s.quantile(0.95))))
    return _timed(run)


ENGINES = {"DuckDB": bench_duckdb, "Polars": bench_polars, "pandas": bench_pandas}


# ------------------------------ entry points -------------------------------

def run_local_benchmark(runs: int = 3) -> dict:
    """Run each engine `runs` times, keep the median. Returns chart_data."""
    import statistics
    path = ensure_dataset()
    results = {}
    for name, fn in ENGINES.items():
        try:
            times = [fn(path) for _ in range(runs)]
            results[name] = round(statistics.median(times), 3)
            print(f"  {name:<8} median {results[name]}s  (runs: {times})")
        except ImportError:
            print(f"  {name:<8} skipped (not installed)")
    return {
        "title": "Query speed: DuckDB vs Polars vs pandas (3M-row group-by)",
        "x_label": "Engine", "y_label": "Seconds (lower is better)",
        "series": [{"name": "median runtime",
                    "x": list(results.keys()),
                    "y": list(results.values())}],
        "source": "Own benchmark · NYC TLC Jan-2024 · methodology in description",
        "methodology": {
            "dataset": DATA_URL, "query": QUERY_DESC, "runs": runs,
            "machine": _machine_info(),
        },
    }


def manual_cloud_entry() -> dict:
    """Paste results from cloud warehouses you ran by hand."""
    print("Enter cloud results (blank name to finish):")
    names, secs, costs = [], [], []
    while True:
        name = input("  tool name: ").strip()
        if not name:
            break
        names.append(name)
        secs.append(float(input("  runtime seconds: ")))
        costs.append(float(input("  cost USD: ")))
    return {
        "title": f"Cloud warehouses: {QUERY_DESC}",
        "x_label": "Tool", "y_label": "Seconds",
        "series": [{"name": "runtime", "x": names, "y": secs},
                   {"name": "cost (USD)", "x": names, "y": costs}],
        "source": "Own benchmark runs · methodology in description",
    }


def _machine_info() -> str:
    import platform
    import multiprocessing
    return (f"{platform.system()} {platform.machine()}, "
            f"{multiprocessing.cpu_count()} cores")


def attach_benchmark(job: VideoJob, chart_data: dict) -> VideoJob:
    """Inject real benchmark results into the job's research before scripting."""
    job.research.setdefault("facts", []).append({
        "claim": f"Benchmark results: {json.dumps(chart_data['series'])}",
        "source_url": "own-benchmark",
        "source_name": "First-party benchmark (reproducible harness)",
        "verified": True,
    })
    job.research["chart_data"] = chart_data
    return job


if __name__ == "__main__":
    print(json.dumps(run_local_benchmark(), indent=2))
