# Workflow Logic — Benchmarks

Reproducible benchmark harnesses for the data engineering tools we review on the [Workflow Logic YouTube channel](https://www.youtube.com/@WorkflowLogic).

Every benchmark on the channel publishes its harness here. You can run them yourself, change the parameters, and tell us how the numbers shift on your hardware.

---

## Video #1 — DuckDB vs Polars vs pandas (3M-row group-by)

**Dataset:** NYC TLC Yellow Taxi Trips, January 2024 (~3M rows, downloaded automatically)

**Query (identical across all engines):**
```sql
SELECT passenger_count, COUNT(*) AS n,
       AVG(fare_amount) AS avg_fare,
       QUANTILE_CONT(trip_distance, 0.95) AS p95_dist
FROM trips
WHERE trip_distance > 1
GROUP BY passenger_count
```

**Methodology:** median of 3 runs per engine, wall-clock time.

**Results — MacBook Air (fill in your specs):**

| Engine | Median runtime |
|--------|---------------:|
| Polars | 0.029s         |
| DuckDB | 0.038s         |
| pandas | 0.220s         |

### Reproduce it

```bash
pip install duckdb polars pandas pyarrow
python benchmark_agent.py
```

The dataset downloads from the NYC TLC public bucket (~48 MB) on first run and is cached locally.

Drop your machine specs and numbers in an issue or PR — we want to know how this scales across hardware.

---

## License

MIT. Use these freely.
