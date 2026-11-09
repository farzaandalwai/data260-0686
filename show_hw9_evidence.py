import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from hw9_cache import INDEX, RAW, redis_client


def load(name):
    return json.loads((RAW / name).read_text())


def pretty(value):
    print(json.dumps(value, indent=2))


def show(part):
    print("SAVED REAL RUN EVIDENCE - HW9 (live Redis inspection is labeled separately)")
    if part == "views":
        print("raw/views.json: accesses, returned count, actual MySQL persisted value")
        for row in load("views.json"):
            print(f"Access #{row['access']:2}: Total={row['count']:2}; MySQL={row['mysql_view_count']:2}" + ("  SYNC" if row["count"] % 10 == 0 else ""))
        pretty(load("database_before.json"))
        print("Original counter restored to 0; full rental data checksum is checked by the verifier.")
    elif part == "index":
        print("LIVE Redis FT.INFO:")
        raw = redis_client().execute_command("FT.INFO", INDEX)
        info = dict(zip(raw[::2], raw[1::2]))
        for key in (b"index_name", b"index_definition", b"num_docs"):
            print(key.decode() + ":", info[key])
        print("Selected actual FT.INFO field attributes:")
        for attribute in info[b"attributes"]:
            values = dict(zip(attribute[::2], attribute[1::2]))
            for key in (b"identifier", b"type", b"algorithm", b"data_type", b"dim", b"distance_metric"):
                if key in values:
                    print(" ", key.decode(), ":", values[key])
        print("Keys (examples):", [key.decode() for key in list(redis_client().scan_iter("s0686:hw9:*"))[:5]])
    elif part == "requests":
        rows = load("cache_requests.json")
        print("raw/cache_requests.json; initial threshold=0.85")
        print("n  cached  score     ms        correct  query")
        for index, row in enumerate(rows, 1):
            print(f"{index:2} {str(row['is_cached']):6} {row['similarity_score']:.5f} {row['latency_ms']:9.3f} {str(row['answer_correct']):7} {row['query']}")
        hits = [row for row in rows if row["is_cached"]]
        misses = [row for row in rows if not row["is_cached"]]
        print(f"Hit rate: {len(hits)}/{len(rows)} = {100 * len(hits)/len(rows):.2f}%")
        print(f"Mean cached: {sum(row['latency_ms'] for row in hits)/len(hits):.3f} ms; mean miss: {sum(row['latency_ms'] for row in misses)/len(misses):.3f} ms")
    elif part == "journey":
        rows = load("cache_requests.json")
        miss = next(row for row in rows if not row["is_cached"])
        hit = next(row for row in rows if row["is_cached"] and row["correlation_id"] == miss["correlation_id"])
        cid = miss["correlation_id"]
        print("Miss query:", miss["query"], "correlation_id:", cid)
        events = []
        for path in (RAW / "kafka").glob("events*.jsonl"):
            for line in path.read_text().splitlines():
                row = json.loads(line)
                if row.get("correlation_id") == cid and row["event"] in ("stage_receive", "stage_send"):
                    events.append(row)
        for row in sorted(events, key=lambda value: value["timestamp"]):
            print(row["timestamp"], row["event"], row["stage"], row["topic"], "partition", row["partition"], "offset", row["offset"])
        print("Actual final answer:", miss["answer"])
        print("Repeated request: cached=", hit["is_cached"], "same final correlation_id=", hit["correlation_id"])
        print("Writer model: llama3.2:latest; cache-hit no-publish behavior is separately smoke-tested.")
    elif part == "labels":
        cases = json.loads(Path("cache_cases.yaml").read_text())
        print(subprocess.check_output(["git", "log", "--diff-filter=A", "-1", "--format=%H%n%cI%n%s", "--", "cache_cases.yaml"], text=True))
        print("SHA256:", hashlib.sha256(Path("cache_cases.yaml").read_bytes()).hexdigest())
        print("VERIFY_SEED=260686; 40 cases")
        for category in ("exact", "paraphrase", "similar_different", "unrelated"):
            group = [row for row in cases if row["category"] == category]
            print(category, "count=", len(group), "should_hit=", group[0]["should_hit"])
            print("  Example:", group[0]["query"])
        print("Same ten warm-up answers at every threshold; misses are not added to the frozen sweep cache.")
    elif part == "thresholds":
        print("threshold hits/40 false_hits/40 mean_ms cost_units(misses + 20*false_hits)")
        for row in load("threshold_summary.json"):
            print(f"{row['threshold']:.2f}     {row['hits']:2}/40   {row['false_hits']:2}/40        {row['mean_latency_ms']:8.3f}    {row['total_cost']}")
        selected = json.loads(Path("hw9_cache_config.json").read_text())
        print("Shipped threshold:", selected["threshold"], selected["rule"])
        print("Assumed costs: miss=1, wrong cached answer=20 normalized units; not monetary measurements.")
    elif part == "falsehit":
        row = load("false_hit.json")
        print("Observed false hit: case", row["case_id"], "threshold", row["threshold"])
        print("Cached query:", row["matched_query"])
        print("Incoming query:", row["query"])
        print("Cosine similarity:", row["similarity_score"])
        print("Returned cached answer:", row["answer"])
        print("Correct MySQL answer:", json.dumps(row["correct_answer"]))
        print("is_cached:", row["is_cached"], "answer_correct:", row["answer_correct"])
        print("Likely confusion: same wording about listing codes; the changed numeric record ID is not separated enough by the embedding.")
    elif part == "stale":
        row = load("staleness.json")
        print("Query:", row["query"])
        for name in ("initial", "stale_hit", "fresh_after_invalidation"):
            item = row[name]
            print(name, "cached=", item["is_cached"], "version=", item["data_version"], "score=", item["similarity_score"], "answer=", item["answer"])
        print("Actually changed MySQL row:", row["changed_database"])
        print("After finally restore:", row["restored_database"])
        print("Normal API writes bump the MySQL version in the same transaction. Out-of-band SQL must explicitly invalidate.")
    elif part == "datasets":
        reference = json.loads(Path("hw9_reference.json").read_text())
        print("Separate reference snapshot:", len(reference), "real rental records")
        pretty(reference["32"])
        for name in ("training", "validation", "test"):
            path = Path(name + "_data.json")
            rows = json.loads(path.read_text())
            print(path.name, "count=", len(rows), "input keys=", list(rows[0]))
            print("  Input example:", json.dumps(rows[0]))
            print("  SHA256:", hashlib.sha256(path.read_bytes()).hexdigest())
    elif part == "repair":
        row = load("repair_with_memory.json")
        print("Controlled TRAINING example with the previously saved lesson; deliberate first-attempt omission")
        print("Question:", row["question"])
        for attempt in row["attempts"]:
            print("Attempt", attempt["attempt"], "loaded lessons", attempt["loaded_lessons"])
            print("Answer:", json.dumps(attempt["answer"]))
            print("Evaluator:", attempt["evaluation"]["result"], attempt["evaluation"]["feedback"])
        print("Final response:", json.dumps(row["final_answer"]), "result:", row["final_evaluation"], "attempts:", row["number_attempts"])
        print("Earlier no-memory controlled runs ended REVISE after two attempts; these are retained in repair_demo.json.")
    elif part == "lessons":
        pretty(json.loads(Path("lessons.json").read_text()))
        row = load("lesson_reuse.json")
        print("Later related training question:", row["question"])
        for attempt in row["attempts"]:
            print("attempt", attempt["attempt"], "loaded", attempt["loaded_lessons"], "answer", attempt["answer"], "evaluation", attempt["evaluation"]["result"])
    elif part == "validation":
        row = load("lesson_validation.json")
        print("Candidate:", row["candidate"])
        print("case before after")
        for index, (before, after) in enumerate(zip(row["before"], row["after"]), 1):
            print(index, before["final_evaluation"], after["final_evaluation"], after["question"])
            if before["final_evaluation"] != after["final_evaluation"]:
                print("  Regression:", after["attempts"][-1]["evaluation"]["feedback"])
        for key in ("no_regressions", "failure_cases_no_worse", "unrelated_supported", "accepted"):
            print(key, row[key])
        print("Rejected candidate is NOT in lessons.json; held-out tests were run only after this selection.")
    elif part == "variants":
        print("variant | correct | incorrect | mean_attempts | mean_latency_ms")
        for name, row in load("agent_variants.json").items():
            print(name, row["correct"], row["incorrect"], row["average_attempts"], row["average_latency_ms"])
            print("  Same held-out SHA256:", row["test_sha256"])
        print("Each variant uses its own lesson-state copy; no test answers were used for learning or selection.")
    elif part == "checks":
        row = json.loads(Path("reports/hw09/verification.json").read_text())
        for item in row["checks"]:
            print("PASS" if item["passed"] else "FAIL", item["name"], ":", str(item["actual"])[:110])
        print("RESULT:", sum(item["passed"] for item in row["checks"]), "/", len(row["checks"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("part")
    show(parser.parse_args().part)
