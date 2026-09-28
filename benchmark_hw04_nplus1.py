import csv
import json
import time
from pathlib import Path

import numpy as np
import requests


BASE_URL = "http://127.0.0.1:8686"
CONFIGS = [
    ("naive", 10),
    ("fixed", 10),
    ("naive", 50),
    ("fixed", 50),
    ("naive", 200),
    ("fixed", 200),
]
RUNS = 30
RAW_DIR = Path(__file__).resolve().parent / "reports" / "hw04" / "raw"
FIELDS = [
    "run",
    "page_size",
    "version",
    "status_code",
    "returned",
    "sql_statements",
    "latency_ms",
]


def percentile(values, percent):
    return float(np.percentile(np.asarray(values, dtype=float), percent))


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    login = session.post(
        BASE_URL + "/api/auth/login",
        json={"email": "farzaan@s0686.local", "password": "rental260"},
    )
    if login.status_code != 200:
        raise SystemExit("Login failed with status " + str(login.status_code))

    records = []
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    for version, page_size in CONFIGS:
        url = BASE_URL + "/api/measure/listings/" + version + "?page_size=" + str(page_size)
        for run in range(1, RUNS + 1):
            before = time.perf_counter()
            response = session.get(url)
            latency_ms = (time.perf_counter() - before) * 1000
            body = response.json()
            records.append(
                {
                    "run": run,
                    "page_size": page_size,
                    "version": version,
                    "status_code": response.status_code,
                    "returned": body["returned"],
                    "sql_statements": body["sql_statements"],
                    "latency_ms": latency_ms,
                }
            )
    finished = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    json_path = RAW_DIR / "nplus1_runs.json"
    csv_path = RAW_DIR / "nplus1_runs.csv"
    summary_path = RAW_DIR / "nplus1_summary.json"
    json_path.write_text(json.dumps(records, indent=2) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    configurations = []
    by_key = {}
    for version, page_size in CONFIGS:
        group = [
            record
            for record in records
            if record["page_size"] == page_size and record["version"] == version
        ]
        latencies = [record["latency_ms"] for record in group]
        sql_values = sorted(set(record["sql_statements"] for record in group))
        summary = {
            "page_size": page_size,
            "version": version,
            "sql_statements_per_request": sql_values[0] if len(sql_values) == 1 else sql_values,
            "p50_ms": percentile(latencies, 50),
            "p95_ms": percentile(latencies, 95),
            "p99_ms": percentile(latencies, 99),
        }
        configurations.append(summary)
        by_key[(page_size, version)] = summary

    speedups = []
    for page_size in (10, 50, 200):
        naive_p50 = by_key[(page_size, "naive")]["p50_ms"]
        fixed_p50 = by_key[(page_size, "fixed")]["p50_ms"]
        speedups.append(
            {
                "page_size": page_size,
                "naive_p50_ms": naive_p50,
                "fixed_p50_ms": fixed_p50,
                "speedup_x": naive_p50 / fixed_p50,
                "latency_reduction_percent": ((naive_p50 - fixed_p50) / naive_p50) * 100,
            }
        )

    summary_path.write_text(
        json.dumps(
            {
                "started": started,
                "finished": finished,
                "measured_requests": len(records),
                "configurations": configurations,
                "speedup": speedups,
            },
            indent=2,
        )
        + "\n"
    )

    print("HW4 N+1 BENCHMARK")
    print("Measured requests:", len(records))
    print("Started:", started)
    print("Finished:", finished)
    print()
    print(f"{'Page':<6}{'Version':<9}{'SQL':<6}{'p50(ms)':<12}{'p95(ms)':<12}{'p99(ms)'}")
    for item in configurations:
        print(
            f"{item['page_size']:<6}{item['version']:<9}{item['sql_statements_per_request']:<6}"
            f"{item['p50_ms']:<12.3f}{item['p95_ms']:<12.3f}{item['p99_ms']:.3f}"
        )
    print()
    print("Speed-up")
    for item in speedups:
        print(
            f"{item['page_size']:<6}{item['speedup_x']:.3f}x    {item['latency_reduction_percent']:.3f}%"
        )
    print()
    print("Raw JSON: reports/hw04/raw/nplus1_runs.json")
    print("Raw CSV: reports/hw04/raw/nplus1_runs.csv")
    print("Summary JSON: reports/hw04/raw/nplus1_summary.json")
    print()

    loaded = json.loads(json_path.read_text())
    with csv_path.open(newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    print("JSON records =", len(loaded))
    print("CSV rows =", len(csv_rows))
    ok = len(loaded) == 180 and len(csv_rows) == 180
    for page_size, version in ((10, "naive"), (10, "fixed"), (50, "naive"), (50, "fixed"), (200, "naive"), (200, "fixed")):
        count = sum(
            1
            for record in loaded
            if record["page_size"] == page_size and record["version"] == version
        )
        print(f"{page_size} {version} = {count}")
        ok = ok and count == 30
    for record in loaded:
        if record["status_code"] != 200 or record["returned"] != record["page_size"]:
            ok = False
        if record["latency_ms"] is None or record["sql_statements"] is None:
            ok = False
    print("SQL distribution")
    for version, page_size in CONFIGS:
        values = [
            record["sql_statements"]
            for record in loaded
            if record["page_size"] == page_size and record["version"] == version
        ]
        counts = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        print(page_size, version, counts)
    if not ok:
        raise SystemExit("validation failed")
    print("validation passed")


if __name__ == "__main__":
    main()
