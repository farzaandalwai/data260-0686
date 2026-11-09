import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("reports/hw09")
RAW = ROOT / "raw"


def load(name):
    return json.loads((RAW / name).read_text())


def main():
    requests = load("cache_requests.json")
    hits = [row for row in requests if row["is_cached"]]
    misses = [row for row in requests if not row["is_cached"]]
    summary = load("threshold_summary.json")
    variants = load("agent_variants.json")
    lines = ["# HW9 measured results", "", "## Initial authenticated ingress run (threshold 0.85)",
             f"Requests: {len(requests)}; hits: {len(hits)}; hit rate: {len(hits)/len(requests):.2%}.",
             f"Mean hit latency: {sum(row['latency_ms'] for row in hits)/len(hits):.3f} ms; mean miss latency: {sum(row['latency_ms'] for row in misses)/len(misses):.3f} ms.",
             f"Wrong returned answers: {sum(not row['answer_correct'] for row in requests)}; cache speed alone is not correctness.",
             "Latency is measured inside the handler, including embedding, Redis search, version lookup, and (on misses) Kafka/local-model work; it excludes HTTP authentication overhead.",
             "", "## Threshold sweep", "", "| Threshold | Hit rate | False-hit rate | Mean latency (ms) | Total cost |", "|---|---|---|---|---|"]
    lines += [f"| {row['threshold']:.2f} | {row['hit_rate']:.1%} | {row['false_hit_rate']:.1%} | {row['mean_latency_ms']:.3f} | {row['total_cost']} |" for row in summary]
    lines += ["", "False-hit rate = wrong cached answers / 40. Costs were fixed before the sweep: miss=1 and false-hit/support=20 normalized units; total=misses+20*false_hits, not measured dollars. Each threshold starts from the same ten real warm-up answers; case misses do not populate that frozen benchmark cache. Normal ingress does populate misses.",
              "", "## Four independent held-out variants", "", "| Variant | Correct | Incorrect | Mean attempts | Mean latency (ms) |", "|---|---|---|---|---|"]
    lines += [f"| {name} | {row['correct']} | {row['incorrect']} | {row['average_attempts']:.3f} | {row['average_latency_ms']:.3f} |" for name, row in variants.items()]
    validation = load("lesson_validation.json")
    before = sum(row["final_evaluation"] == "PASS" for row in validation["before"])
    after = sum(row["final_evaluation"] == "PASS" for row in validation["after"])
    lines += ["", f"Proposed lesson validation: {before}/6 before, {after}/6 after; accepted={validation['accepted']}. The rejected extra lesson is not shipped. Validated Improvement therefore retains the prior lesson only. Memory is not claimed to beat Evaluator Repair.",
              "The no-memory controlled examples ended REVISE after two attempts. A separate training-only, memory-assisted controlled example repaired the deliberately omitted value and ended PASS at attempt two; no held-out input or answer was changed to obtain this demonstration.",
              "", "## Data integrity", "", "The original 5,000 rental records have the same checksum after restoring the staleness experiment. The new view counter was also restored to zero after the 25-access demonstration. Database backups are private under .hw9_runtime/backups/ and are not committed.", ""]
    (ROOT / "METRICS.md").write_text("\n".join(lines))
    rows = load("threshold_cases.json")
    keys = ["case_id", "category", "should_hit", "threshold", "query", "matched_query", "is_cached", "similarity_score", "answer", "correct_answer", "answer_correct", "label_prediction_correct", "latency_ms", "false_hit"]
    with (RAW / "threshold_cases.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row[key]) if isinstance(row[key], dict) else row[key] for key in keys})
    paths = sorted(RAW.glob("*.log")) + sorted(RAW.glob("hw9_events*.jsonl")) + sorted((RAW / "kafka").glob("events*.jsonl"))
    with (ROOT / "RUN_LOG.txt").open("w") as stream:
        stream.write("HW9 real console/event output; collected " + datetime.now(timezone.utc).isoformat() + "\n")
        stream.write("Earlier failed/debug runs are retained and distinguished by their filenames. Reported measurements use cache_requests.json, threshold_cases.json, agent_variants.json, and the final verification.json.\n")
        for path in paths:
            stream.write("\nSOURCE: " + str(path) + "\n" + path.read_text() + "\n")
    print("Generated METRICS.md, threshold_cases.csv, and RUN_LOG.txt from the actual saved runs.")


if __name__ == "__main__":
    main()
