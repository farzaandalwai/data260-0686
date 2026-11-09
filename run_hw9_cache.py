import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from uuid import uuid4

import requests
from sqlalchemy import text

from database import db_engine
from hw9_cache import PREFIX, RAW, RentalCache, SemanticCache, data_version, embed, invalidate_data, listing_facts, log
from hw9_test_support import reader_token


def save(name, data):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / name).write_text(json.dumps(data, indent=2) + "\n")


def is_correct(response, expected):
    try:
        return json.loads(response["answer"]) == expected
    except (ValueError, TypeError):
        return False


def counter():
    cache = RentalCache()
    listing_id, key = 1, PREFIX + ":views:listing:1"
    with db_engine.connect() as connection:
        original = connection.execute(text("SELECT view_count FROM rental_listings WHERE id=1")).scalar_one()
    if original != 0 or cache.redis_client.exists(key):
        raise RuntimeError("Counter demo needs an unused HW9 counter starting at zero; refusing to reset existing state")
    rows = []
    try:
        for access in range(1, 26):
            count = cache.increment_listing_views(listing_id)
            with db_engine.connect() as connection:
                persisted = connection.execute(text("SELECT view_count FROM rental_listings WHERE id=1")).scalar_one()
            row = log("counter_access", access=access, count=count, mysql_view_count=persisted)
            rows.append(row)
            print(f"Access #{access}: Total = {count}; MySQL = {persisted}", flush=True)
    finally:
        with db_engine.begin() as connection:
            connection.execute(text("UPDATE rental_listings SET view_count=:count WHERE id=1"), {"count": original})
        cache.redis_client.delete(key)
        log("counter_restored", listing_id=listing_id, mysql_view_count=original)
    save("views.json", rows)


def requests_demo():
    cases = json.loads(Path("cache_cases.yaml").read_text())
    examples = [next(row for row in cases if row["case_id"] == name) for name in
                ("exact_01", "exact_01", "paraphrase_01", "exact_02", "exact_02", "paraphrase_02",
                 "unrelated_01", "unrelated_01", "similar_01", "similar_01", "unrelated_02", "unrelated_02")]
    rows = []
    with reader_token() as token:
        for case in examples:
            response = requests.post("http://127.0.0.1:8686/api/hw9/ask", json={**{key: case[key] for key in ("query", "listing_id", "field")}, "threshold": 0.85},
                                     headers={"Authorization": "Bearer " + token}, timeout=240)
            response.raise_for_status()
            row = response.json()
            row["answer_correct"] = is_correct(row, listing_facts(case["listing_id"], case["field"]))
            rows.append(row)
            save("cache_requests.json", rows)
            log("demo_response", **row)


def sweep():
    assert not subprocess.check_output(["git", "status", "--porcelain", "--", "cache_cases.yaml"], text=True).strip()
    subprocess.run(["git", "ls-files", "--error-unmatch", "cache_cases.yaml"], check=True, capture_output=True)
    cases_bytes = Path("cache_cases.yaml").read_bytes()
    cases_hash = hashlib.sha256(cases_bytes).hexdigest()
    cases = json.loads(cases_bytes)
    assert Counter(row["category"] for row in cases) == {"exact": 10, "paraphrase": 10, "similar_different": 10, "unrelated": 10}
    run = uuid4().hex[:10]
    warm = []
    for case in sorted((row for row in cases if row["category"] == "exact"), key=lambda row: row["case_id"]):
        # Force a real miss for every seed by using a distinct empty namespace.
        seed_cache = SemanticCache("seed" + run + case["case_id"].replace("_", ""))
        response = seed_cache.answer(case["query"], case["listing_id"], case["field"])
        warm.append({"case": case, "response": response, "embedding": embed(case["query"])})
        save("warmup.json", warm)
    summary, all_rows, false_hit = [], [], None
    for threshold in (0.75, 0.80, 0.85, 0.90, 0.95):
        cache = SemanticCache("sweep" + run + str(int(threshold * 100)), threshold)
        version = data_version()
        for seed in warm:
            case = seed["case"]
            cache.put(case["query"], seed["embedding"], seed["response"], version, case["listing_id"], case["field"])
        rows = []
        for case in cases:
            response = cache.answer(case["query"], case["listing_id"], case["field"], store_miss=False)
            expected = listing_facts(case["listing_id"], case["field"])
            row = {**case, **response, "answer_correct": is_correct(response, expected), "correct_answer": expected,
                   "label_prediction_correct": response["is_cached"] == case["should_hit"]}
            row["false_hit"] = row["is_cached"] and not row["answer_correct"]
            rows.append(row)
            all_rows.append(row)
            save("threshold_cases.json", all_rows)
            if row["false_hit"] and false_hit is None:
                false_hit = row
                save("false_hit.json", row)
            log("threshold_case", case_id=case["case_id"], threshold=threshold, is_cached=row["is_cached"],
                score=row["similarity_score"], correct=row["answer_correct"], latency_ms=row["latency_ms"])
        hits = sum(row["is_cached"] for row in rows)
        false_hits = sum(row["false_hit"] for row in rows)
        result = {"threshold": threshold, "cases": len(rows), "hits": hits, "misses": len(rows) - hits,
                  "false_hits": false_hits, "hit_rate": hits / len(rows), "false_hit_rate": false_hits / len(rows),
                  "false_hit_given_hit": false_hits / hits if hits else 0,
                  "mean_latency_ms": round(sum(row["latency_ms"] for row in rows) / len(rows), 3),
                  "total_cost": len(rows) - hits + 20 * false_hits}
        summary.append(result)
        save("threshold_summary.json", summary)
        log("threshold_summary", **result)
    assert hashlib.sha256(Path("cache_cases.yaml").read_bytes()).hexdigest() == cases_hash
    selected = min(summary, key=lambda row: (row["total_cost"], -row["threshold"]))
    decision = {"threshold": selected["threshold"], "rule": "Minimum observed cost; higher threshold breaks ties",
                "case_sha256": cases_hash, "labels_commit": subprocess.check_output(["git", "log", "--diff-filter=A", "--format=%H", "--", "cache_cases.yaml"], text=True).strip(),
                "miss_cost": 1, "false_hit_cost": 20, "run_id": run, "summary": summary}
    Path("hw9_cache_config.json").write_text(json.dumps(decision, indent=2) + "\n")
    log("threshold_selected", **{key: value for key, value in decision.items() if key != "summary"})
    if false_hit is None:
        log("no_false_hit_observed", message="Do not invent one; report this unmet demonstration")


def stale():
    run = uuid4().hex[:10]
    cache = SemanticCache("stale" + run, 0.85)
    query = "How many available units does rental listing 2 currently have?"
    with db_engine.connect() as connection:
        original = dict(connection.execute(text("SELECT available_units,updated_at FROM rental_listings WHERE id=2")).mappings().one())
    sequence = {"query": query, "original_units": original["available_units"]}
    try:
        sequence["initial"] = cache.answer(query, 2, "available_units")
        with db_engine.begin() as connection:
            connection.execute(text("UPDATE rental_listings SET available_units=:units WHERE id=2"), {"units": original["available_units"] + 7})
        sequence["changed_database"] = listing_facts(2, "available_units")
        sequence["stale_hit"] = cache.answer(query, 2, "available_units")
        sequence["new_version"] = invalidate_data()
        sequence["fresh_after_invalidation"] = cache.answer(query, 2, "available_units")
    finally:
        with db_engine.begin() as connection:
            connection.execute(text("UPDATE rental_listings SET available_units=:units,updated_at=:updated WHERE id=2"),
                               {"units": original["available_units"], "updated": original["updated_at"]})
        invalidate_data()
        sequence["restored_database"] = listing_facts(2, "available_units")
        log("stale_record_restored", **sequence["restored_database"])
        save("staleness.json", sequence)
    log("staleness_complete", **sequence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("part", choices=["counter", "requests", "sweep", "stale"])
    args = parser.parse_args()
    {"counter": counter, "requests": requests_demo, "sweep": sweep, "stale": stale}[args.part]()
