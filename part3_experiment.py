import json
import csv
import time
from collections import Counter

from agents_demo import planner, reviewer, finalize


with open("reports/hw01/cases/nondeterminism_input.json") as file:
    test_input = json.load(file)

title = test_input["title"]
content = test_input["content"]

results = []


def percentile(values, percent):
    values = sorted(values)
    position = (len(values) - 1) * percent
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    difference = position - lower

    return values[lower] + (values[upper] - values[lower]) * difference


def run_test(temperature):
    start = time.time()

    plan = planner(title, content, temperature)
    review = reviewer(title, content, plan, temperature)
    final = finalize(review)

    latency = (time.time() - start) * 1000

    return {
        "temperature": temperature,
        "tags": final["tags"],
        "summary": final["summary"],
        "latency_ms": round(latency, 2)
    }


for temperature in [0.7, 0.0]:
    print(f"\nRunning temperature {temperature}")

    for run_number in range(1, 21):
        result = run_test(temperature)
        result["run"] = run_number
        results.append(result)

        print(
            f"Run {run_number}/20 - "
            f"{result['latency_ms']} ms - "
            f"{result['tags']}"
        )


with open("reports/hw01/raw/part3_runs.json", "w") as file:
    json.dump(results, file, indent=2)


with open("reports/hw01/raw/part3_runs.csv", "w", newline="") as file:
    writer = csv.writer(file)

    writer.writerow([
        "temperature",
        "run",
        "tags",
        "summary",
        "latency_ms"
    ])

    for result in results:
        writer.writerow([
            result["temperature"],
            result["run"],
            " | ".join(result["tags"]),
            result["summary"],
            result["latency_ms"]
        ])


def calculate_metrics(temperature):
    temp_results = [
        result for result in results
        if result["temperature"] == temperature
    ]

    tag_sets = []
    tag_counter = Counter()
    latencies = []

    for result in temp_results:
        normalized_tags = [
            tag.strip().lower()
            for tag in result["tags"]
        ]

        tag_sets.append(tuple(sorted(normalized_tags)))
        tag_counter.update(set(normalized_tags))
        latencies.append(result["latency_ms"])

    distinct_sets = len(set(tag_sets))

    tags_all_runs = [
        tag for tag, count in tag_counter.items()
        if count == 20
    ]

    tags_one_run = [
        tag for tag, count in tag_counter.items()
        if count == 1
    ]

    return {
        "distinct_tag_sets": distinct_sets,
        "tags_all_runs": tags_all_runs,
        "tags_one_run": tags_one_run,
        "p50": round(percentile(latencies, 0.50), 2),
        "p95": round(percentile(latencies, 0.95), 2),
        "p99": round(percentile(latencies, 0.99), 2)
    }


metrics_07 = calculate_metrics(0.7)
metrics_00 = calculate_metrics(0.0)

print("\nPart 3 Results")

for temperature, metrics in [(0.7, metrics_07), (0.0, metrics_00)]:
    print(f"\nTemperature {temperature}")
    print("Distinct tag sets:", metrics["distinct_tag_sets"])
    print("Tags in all 20 runs:", metrics["tags_all_runs"])
    print("Tags in exactly 1 run:", metrics["tags_one_run"])
    print(
        "Latency p50 / p95 / p99:",
        metrics["p50"],
        "/",
        metrics["p95"],
        "/",
        metrics["p99"],
        "ms"
    )


with open("reports/hw01/METRICS.md", "w") as file:
    file.write("# Homework 1 Metrics\n\n")
    file.write("| Metric | Temp 0.7 | Temp 0.0 |\n")
    file.write("|---|---|---|\n")
    file.write(
        f"| Distinct tag sets | {metrics_07['distinct_tag_sets']} | "
        f"{metrics_00['distinct_tag_sets']} |\n"
    )
    file.write(
        f"| Tags in all 20 runs | {', '.join(metrics_07['tags_all_runs']) or 'None'} | "
        f"{', '.join(metrics_00['tags_all_runs']) or 'None'} |\n"
    )
    file.write(
        f"| Tags in exactly 1 run | {', '.join(metrics_07['tags_one_run']) or 'None'} | "
        f"{', '.join(metrics_00['tags_one_run']) or 'None'} |\n"
    )
    file.write(
        f"| Latency p50 / p95 / p99 (ms) | "
        f"{metrics_07['p50']} / {metrics_07['p95']} / {metrics_07['p99']} | "
        f"{metrics_00['p50']} / {metrics_00['p95']} / {metrics_00['p99']} |\n"
    )

print("\nFiles saved in reports/hw01/")