import csv
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean

from agent_graph import AgentState, graph
from src.model_client import MODEL


REPORTS_PATH = Path("reports/hw02")
RAW_PATH = REPORTS_PATH / "raw"
SCHEMA_CASE_PATH = REPORTS_PATH / "cases/schema_input.json"
ADVERSARIAL_CASE_PATH = REPORTS_PATH / "cases/adversarial_input.json"


def load_case(path):
    with open(path) as file:
        return json.load(file)


def run_graph(case, ceiling, experiment, run_number):
    state: AgentState = {
        **case,
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
        "planner_attempts": 0,
        "turn_ceiling": ceiling,
        "validation_error": "",
        "validation_errors": [],
        "status": "running",
    }

    start = time.time()
    result = graph.invoke(state, {"recursion_limit": 100})
    latency_ms = round((time.time() - start) * 1000, 2)

    attempts = result["planner_attempts"]
    status = result["status"]

    if status == "abandoned":
        classification = "abandoned_at_ceiling"
    elif attempts == 1:
        classification = "valid_first_attempt"
    elif attempts == 2:
        classification = "valid_after_1_retry"
    else:
        classification = "valid_after_2plus_retries"

    final_output = result.get("reviewer_feedback") or result.get(
        "planner_proposal", {}
    )

    return {
        "experiment": experiment,
        "run": run_number,
        "ceiling": ceiling,
        "status": status,
        "planner_attempts": attempts,
        "retries": max(attempts - 1, 0),
        "classification": classification,
        "latency_ms": latency_ms,
        "final_tags": final_output.get("tags", []),
        "final_summary": final_output.get("summary", ""),
        "validation_errors": result.get("validation_errors", []),
        "model": MODEL,
        "temperature": 0.0,
    }


def run_batch(case, ceiling, count, experiment):
    records = []

    for run_number in range(1, count + 1):
        record = run_graph(case, ceiling, experiment, run_number)
        records.append(record)
        print(
            f"{experiment} {run_number}/{count}: "
            f"{record['status']}, attempts={record['planner_attempts']}, "
            f"latency={record['latency_ms']} ms"
        )

    return records


def save_records(filename, records):
    RAW_PATH.mkdir(parents=True, exist_ok=True)

    with open(RAW_PATH / f"{filename}.json", "w") as file:
        json.dump(records, file, indent=2)

    fields = list(records[0].keys())
    with open(RAW_PATH / f"{filename}.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for record in records:
            row = record.copy()
            row["final_tags"] = json.dumps(row["final_tags"])
            row["validation_errors"] = json.dumps(row["validation_errors"])
            writer.writerow(row)


def outcome_rows(records):
    labels = [
        ("valid_first_attempt", "Valid first attempt"),
        ("valid_after_1_retry", "Valid after 1 retry"),
        ("valid_after_2plus_retries", "Valid after 2+ retries"),
        ("abandoned_at_ceiling", "Hit turn ceiling"),
    ]
    counts = Counter(record["classification"] for record in records)
    rows = []

    for classification, label in labels:
        matching = [
            record["latency_ms"]
            for record in records
            if record["classification"] == classification
        ]
        latency = f"{mean(matching):.2f}" if matching else "N/A"
        rows.append((label, counts[classification], latency))

    return rows


def ceiling_summary(records):
    completed = sum(record["status"] == "completed" for record in records)
    return {
        "runs": len(records),
        "completed": completed,
        "completion_rate": completed / len(records) * 100,
        "mean_latency": mean(record["latency_ms"] for record in records),
        "mean_attempts": mean(
            record["planner_attempts"] for record in records
        ),
    }


def choose_ceiling(summary_2, summary_10):
    if summary_10["completion_rate"] > summary_2["completion_rate"]:
        return 10, "it had the higher completion rate"

    if summary_2["completion_rate"] > summary_10["completion_rate"]:
        return 2, "it had the higher completion rate"

    if summary_2["mean_latency"] <= summary_10["mean_latency"]:
        return 2, "completion rates matched and it had lower mean latency"

    return 10, "completion rates matched and it had lower mean latency"


def write_metrics(schema_runs, ceiling_2_runs, ceiling_10_runs, adversarial):
    summary_2 = ceiling_summary(ceiling_2_runs)
    summary_10 = ceiling_summary(ceiling_10_runs)
    chosen_ceiling, reason = choose_ceiling(summary_2, summary_10)
    adversarial_hits = sum(
        record["status"] == "abandoned" for record in adversarial
    )

    lines = [
        "# HW2 Metrics",
        "",
        "## Schema Validation - 30 Runs",
        "",
        "| Outcome | Count | Mean latency (ms) |",
        "|---|---:|---:|",
    ]

    for label, count, latency in outcome_rows(schema_runs):
        lines.append(f"| {label} | {count} | {latency} |")

    lines.extend([
        "",
        "## Turn Ceiling Comparison",
        "",
        "| Ceiling | Runs | Completion Rate | Mean Latency (ms) |",
        "|---:|---:|---:|---:|",
        (
            f"| 2 | {summary_2['runs']} | "
            f"{summary_2['completion_rate']:.1f}% | "
            f"{summary_2['mean_latency']:.2f} |"
        ),
        (
            f"| 10 | {summary_10['runs']} | "
            f"{summary_10['completion_rate']:.1f}% | "
            f"{summary_10['mean_latency']:.2f} |"
        ),
        "",
        f"Ceiling {chosen_ceiling} is selected for deployment because {reason}.",
        "",
        "## Adversarial Test",
        "",
        "- Total runs: 5",
        f"- Ceiling used: {adversarial[0]['ceiling']}",
        f"- Runs that hit the ceiling: {adversarial_hits}",
        f"- Observed rate: {adversarial_hits / len(adversarial) * 100:.1f}%",
        (
            "- Why difficult: The rental text contains formatting instructions "
            "that conflict with the required schema."
        ),
        (
            "- Proposed fix: Clearly separate untrusted listing content from "
            "the model's output instructions."
        ),
        "",
    ])

    with open(REPORTS_PATH / "METRICS.md", "w") as file:
        file.write("\n".join(lines))

    return summary_2, summary_10, chosen_ceiling, adversarial_hits


def append_run_log(summary_2, summary_10, chosen_ceiling, adversarial_hits):
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "",
        "PART 4 - OUTPUT SCHEMA AND LOOP SAFETY",
        f"Timestamp: {timestamp}",
        "Command: python3.11 part4_experiment.py",
        f"Model: {MODEL}",
        f"Frozen input: {SCHEMA_CASE_PATH}",
        "Schema runs: 30 with ceiling 10",
        "Ceiling comparison: 20 runs at ceiling 2, 20 runs at ceiling 10",
        "Adversarial runs: 5 with ceiling 2",
        (
            f"Ceiling 2: {summary_2['completed']}/20 completed, "
            f"{summary_2['completion_rate']:.1f}%, "
            f"mean latency {summary_2['mean_latency']:.2f} ms"
        ),
        (
            f"Ceiling 10: {summary_10['completed']}/20 completed, "
            f"{summary_10['completion_rate']:.1f}%, "
            f"mean latency {summary_10['mean_latency']:.2f} ms"
        ),
        f"Deployment ceiling selected: {chosen_ceiling}",
        f"Adversarial ceiling hits: {adversarial_hits}/5",
    ]

    with open(REPORTS_PATH / "RUN_LOG.txt", "a") as file:
        file.write("\n".join(lines) + "\n")


def main():
    schema_case = load_case(SCHEMA_CASE_PATH)
    adversarial_case = load_case(ADVERSARIAL_CASE_PATH)

    schema_runs = run_batch(schema_case, 10, 30, "schema_validation")
    save_records("schema_validation_runs", schema_runs)

    ceiling_2_runs = run_batch(schema_case, 2, 20, "ceiling_2")
    save_records("ceiling_2_runs", ceiling_2_runs)

    ceiling_10_runs = run_batch(schema_case, 10, 20, "ceiling_10")
    save_records("ceiling_10_runs", ceiling_10_runs)

    adversarial_runs = run_batch(
        adversarial_case,
        2,
        5,
        "adversarial",
    )
    save_records("adversarial_runs", adversarial_runs)

    summary = write_metrics(
        schema_runs,
        ceiling_2_runs,
        ceiling_10_runs,
        adversarial_runs,
    )
    append_run_log(*summary)

    print("\nPart 4 complete")
    print(
        f"Ceiling 2 completion: {summary[0]['completion_rate']:.1f}%"
    )
    print(
        f"Ceiling 10 completion: {summary[1]['completion_rate']:.1f}%"
    )
    print(f"Deployment ceiling: {summary[2]}")
    print(f"Adversarial ceiling hits: {summary[3]}/5")


if __name__ == "__main__":
    main()
