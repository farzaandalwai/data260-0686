import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import requests
import hw8_kafka
import bcrypt
import jwt
from datetime import timedelta
from sqlalchemy import text

from database import SessionLocal, db_engine
from hw8_kafka import BROKER, FINAL, INBOX, consumer, producer, read_events, request, send, wait_for
from homework_demo import SAMPLE
from hw9_agents import EvaluatorAgent, load_reference
from hw9_cache import INDEX, RAW, SemanticCache, listing_facts, redis_client
from scripts.hw9_database_digest import database_digest
from models import User
from confluent_kafka import Consumer, TopicPartition


def main():
    hw8_kafka.RAW = RAW / "kafka"
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag")
    parser.add_argument("--output", default="reports/hw09/verification.json")
    args = parser.parse_args()
    checks = []

    def check(name, actual, expected=True):
        passed = actual == expected
        checks.append({"name": name, "passed": passed, "actual": actual, "expected": expected})
        print(f"{'PASS' if passed else 'FAIL'} {name}: {actual}", flush=True)

    def load(name):
        return json.loads((RAW / name).read_text())

    views = load("views.json")
    check("25 real view increments", [row["count"] for row in views], list(range(1, 26)))
    check("MySQL sync at 10 and 20 only", [row["mysql_view_count"] for row in views], [0] * 9 + [10] * 10 + [20] * 6)
    with db_engine.connect() as connection:
        check("counter restored", connection.execute(text("SELECT view_count FROM rental_listings WHERE id=1")).scalar_one(), 0)
        check("all 5000 rental records remain", connection.execute(text("SELECT COUNT(*) FROM rental_listings")).scalar_one(), 5000)
    current_digest, original_digest = database_digest(), load("database_before.json")
    check("all original rental fields restored", current_digest, original_digest)
    client = redis_client()
    check("all Redis keys use s0686 prefix", all(key.startswith(b"s0686") for key in client.scan_iter()))
    info = client.execute_command("FT.INFO", INDEX)
    check("real Redis vector index", b"attributes" in info and b"index_name" in info)
    demo = load("cache_requests.json")
    check("at least ten ingress requests", len(demo) >= 10)
    check("cache demo contains hits and misses", {row["is_cached"] for row in demo} == {True, False})
    check("response score and measured latency", all("similarity_score" in row and row["latency_ms"] > 0 for row in demo))
    cache = SemanticCache("verify" + uuid4().hex[:10], 0.85)
    query = "What is the location of rental listing 1?"
    miss = cache.answer(query, 1, "location")
    probe = Consumer({"bootstrap.servers": BROKER, "group.id": "s0686_verify_probe_" + uuid4().hex})
    before_count = probe.get_watermark_offsets(TopicPartition(INBOX, 0), timeout=10)[1]
    hit = cache.answer(query, 1, "location")
    after_count = probe.get_watermark_offsets(TopicPartition(INBOX, 0), timeout=10)[1]
    probe.close()
    check("new miss actually runs pipeline", not miss["is_cached"])
    check("miss answer matches MySQL", json.loads(miss["answer"]), listing_facts(1, "location"))
    check("exact hit returns same final answer", hit["is_cached"] and hit["answer"] == miss["answer"])
    check("hit does not rerun Kafka pipeline", after_count, before_count)
    check("HW8 three-stage miss journey", sorted({row["stage"] for row in read_events() if row["event"] == "stage_send" and row.get("correlation_id") == miss["correlation_id"]}), ["planner", "reviewer", "writer"])
    cases = json.loads(Path("cache_cases.yaml").read_text())
    check("40 fixed balanced labeled cases", dict(Counter(row["category"] for row in cases)), {"exact": 10, "paraphrase": 10, "similar_different": 10, "unrelated": 10})
    frozen = subprocess.check_output(["git", "show", "0cdc5328e78881f95f5756247ba0ee95c55162a6:cache_cases.yaml"])
    check("labels unchanged since pre-sweep commit", hashlib.sha256(Path("cache_cases.yaml").read_bytes()).hexdigest(), hashlib.sha256(frozen).hexdigest())
    rows, summary = load("threshold_cases.json"), load("threshold_summary.json")
    check("200 per-case threshold measurements", len(rows), 200)
    check("five required thresholds", [row["threshold"] for row in summary], [0.75, 0.8, 0.85, 0.9, 0.95])
    for result in summary:
        subset = [row for row in rows if row["threshold"] == result["threshold"]]
        hits = sum(row["is_cached"] for row in subset)
        false_hits = sum(row["is_cached"] and not row["answer_correct"] for row in subset)
        valid = result["hits"] == hits and result["false_hits"] == false_hits and result["total_cost"] == 40 - hits + 20 * false_hits
        valid = valid and result["mean_latency_ms"] == round(sum(row["latency_ms"] for row in subset) / 40, 3)
        check("recalculated threshold " + str(result["threshold"]), valid)
    selected = json.loads(Path("hw9_cache_config.json").read_text())
    check("ships minimum-cost threshold", selected["threshold"], min(summary, key=lambda row: (row["total_cost"], -row["threshold"]))["threshold"])
    false_hit = load("false_hit.json")
    check("observed false hit has full evidence", false_hit["is_cached"] and not false_hit["answer_correct"] and bool(false_hit["matched_query"]) and bool(false_hit["correct_answer"]))
    stale = load("staleness.json")
    check("actual stale hit", stale["stale_hit"]["is_cached"] and stale["stale_hit"]["answer"] == stale["initial"]["answer"] and json.loads(stale["stale_hit"]["answer"]) != stale["changed_database"])
    fresh = stale["fresh_after_invalidation"]
    check("version invalidation causes fresh answer", not fresh["is_cached"] and json.loads(fresh["answer"]) == stale["changed_database"] and fresh["data_version"] > stale["stale_hit"]["data_version"])
    check("stale test record restored", stale["restored_database"], {"listing_id": 2, "available_units": stale["original_units"]})
    splits = [json.loads(Path(name + "_data.json").read_text()) for name in ("training", "validation", "test")]
    check("input datasets contain no answers", all(set(item) == {"question", "listing_id", "fields"} for split in splits for item in split))
    check("disjoint input questions", len({item["question"] for split in splits for item in split}), sum(map(len, splits)))
    repair, reuse = load("repair_demo.json"), load("lesson_reuse.json")
    check("controlled failure revised, reevaluated, and stopped at two", all(row["number_attempts"] == 2 and row["attempts"][0]["evaluation"]["result"] == "REVISE" and row["attempts"][1]["evaluation"]["result"] in ("PASS", "REVISE") for row in repair))
    repaired_with_memory = load("repair_with_memory.json")
    check("training-only memory-assisted controlled repair passes", repaired_with_memory["number_attempts"] == 2 and repaired_with_memory["attempts"][0]["evaluation"]["result"] == "REVISE" and repaired_with_memory["final_evaluation"] == "PASS")
    lessons = json.loads(Path("lessons.json").read_text())
    check("five required lesson fields", all({"lesson_id", "failure_pattern", "correction", "created_at", "use_count"} <= set(row) for row in lessons))
    check("later question loads saved lesson", "lesson_001" in reuse["attempts"][0]["loaded_lessons"])
    validation = load("lesson_validation.json")
    old = [row["final_evaluation"] == "PASS" for row in validation["before"]]
    new = [row["final_evaluation"] == "PASS" for row in validation["after"]]
    no_regressions = all(not value or new[index] for index, value in enumerate(old))
    check("validation gate preserves correct answers", not validation["accepted"] or no_regressions)
    check("candidate kept only if accepted", ("lesson_002" in [row["lesson_id"] for row in lessons]), validation["accepted"])
    variants = load("agent_variants.json")
    check("four independent variants", list(variants), ["Baseline", "Evaluator Repair", "Lesson Memory", "Validated Improvement"])
    test_hash = hashlib.sha256(Path("test_data.json").read_bytes()).hexdigest()
    evaluator, reference = EvaluatorAgent(load_reference()), load_reference()
    for name, result in variants.items():
        actual = sum(evaluator.evaluate(item, row["final_answer"])["result"] == "PASS" for item, row in zip(splits[2], result["rows"]))
        check(name + " held-out accounting", result["correct"] == actual and result["correct"] + result["incorrect"] == len(splits[2]) and result["test_sha256"] == test_hash and all(row["number_attempts"] <= 2 for row in result["rows"]))
    check("all reference facts still match MySQL", all(all(listing_facts(int(key), field)[field] == record[field] for field in ("listing_code", "location", "available_units", "property_title")) for key, record in reference.items()))
    created = request("CREATE_LISTING", SAMPLE)
    fetched = request("GET_LISTING", {"listing_id": created["listing_id"]})
    check("existing HW8 CREATE/GET still works", created["success"] and fetched["success"] and fetched["listing"]["propertyTitle"] == SAMPLE["propertyTitle"])
    check("existing HW7 auth still requires token", requests.get("http://127.0.0.1:8686/auth/me", timeout=10).status_code, 401)
    check("HW9 ingress preserves JWT protection", requests.post("http://127.0.0.1:8686/api/hw9/ask", json={"query": query, "listing_id": 1, "field": "location"}, timeout=10).status_code, 401)
    check("FastAPI existing listing routes remain", "/api/listings" in requests.get("http://127.0.0.1:8686/openapi.json", timeout=10).json()["paths"])
    cid = str(uuid4())
    reply = consumer("s0686_hw9_legacy_" + cid, FINAL)
    try:
        send(producer(), INBOX, {"correlation_id": cid, "question": "Describe the known facts about this rental.", "facts": {"location": "San Jose", "available_units": 2}, "use_model": True}, key="rental-legacy")
        legacy = wait_for(reply, cid, timeout=180)
        (RAW / "legacy_hw8.json").write_text(json.dumps(legacy, indent=2) + "\n")
        check("existing HW8 freeform local-model path", legacy["correlation_id"] == cid and "San Jose" in legacy["answer"] and "2" in legacy["answer"])
    finally:
        reply.close()
    with SessionLocal() as db:
        suffix = uuid4().hex[:10]
        user = User(name="HW9 smoke reader", username="hw9_" + suffix, email="hw9_" + suffix + "@example.com", role="reader", password_hash=bcrypt.hashpw(uuid4().hex.encode(), bcrypt.gensalt()).decode())
        db.add(user)
        db.commit()
        try:
            token = jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=2)}, os.environ["JWT_SECRET"], algorithm="HS256")
            page = requests.get("http://127.0.0.1:8686/api/listings", headers={"Authorization": "Bearer " + token}, timeout=20)
            check("existing authenticated MySQL endpoint", page.status_code == 200 and bool(page.json().get("items")) and page.json().get("total") == 5000)
            cli = subprocess.check_output([os.sys.executable, "send_question.py", "What is the location of rental listing 1?", "--cache", "--listing-id", "1", "--field", "location"], text=True, env={**os.environ, "HW9_TOKEN": token})
            cached_cli = json.loads(cli)
            check("existing question CLI uses authenticated cache ingress", "is_cached" in cached_cli and cached_cli["threshold"] == selected["threshold"] and json.loads(cached_cli["answer"]) == listing_facts(1, "location"))
        finally:
            db.delete(user)
            db.commit()
    mongo = requests.get("http://127.0.0.1:8686/api/document-listings", timeout=30)
    check("existing MongoDB document endpoint", mongo.status_code == 200 and isinstance(mongo.json(), list))
    from mcp_servers.rentals_server import search_listings
    check("existing MCP rental search", search_listings("San Jose", 2)["ok"])
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    sources = ["main.py", "models.py", "hw9_cache.py", "hw9_agents.py", "hw8_pipeline.py", "hw8_kafka.py", "src/model_client.py", "routers/hw9_cache.py", "routers/hw4_listings.py", "verify_hw09.py", "run_hw9_agents.py", "run_hw9_cache.py", "cache_cases.yaml", "hw9_reference.json", "training_data.json", "validation_data.json", "test_data.json", "lessons.json", "hw9_cache_config.json", "compose.hw09.yml", "send_question.py", "hw9_test_support.py"]
    sources += ["requirements.txt", "requirements-hw08.txt", "Dockerfile.hw09", "scripts/hw9_setup.py", "scripts/hw9_repair_with_memory.py"]
    if args.tag:
        assert commit == subprocess.check_output(["git", "rev-parse", args.tag + "^{commit}"], text=True).strip()
        subprocess.run(["git", "diff", "--exit-code", args.tag, "--", *sources], check=True)
    record = {"homework": 9, "sid4": "0686", "port_base": 8686, "prefix": "s0686", "seed": 686,
              "verify_seed": 260686, "domain_id": 6, "commit_hash": commit, "tested_tag": args.tag,
              "scope": "tagged application" if args.tag else "pre-commit working tree identified by source hashes",
              "timestamp": datetime.now(timezone.utc).isoformat(), "model": "llama3.2:latest",
              "embedding_model": "nomic-embed-text:latest", "checks": checks,
              "shipped_threshold": selected["threshold"],
              "source_sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
              "passed": all(row["passed"] for row in checks)}
    Path(args.output).write_text(json.dumps(record, indent=2) + "\n")
    print(f"RESULT: {sum(row['passed'] for row in checks)}/{len(checks)}")
    if not record["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    os.environ.setdefault("HW8_RAW_DIR", "reports/hw09/raw/kafka")
    main()
