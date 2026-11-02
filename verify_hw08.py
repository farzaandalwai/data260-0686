import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import bcrypt
import jwt
import requests
from confluent_kafka.admin import AdminClient
from sqlalchemy import func, select

from database import SessionLocal
from homework_demo import SAMPLE
from hw8_kafka import BROKER, DEAD, DRAFTS, FINAL, INBOX, RAW, REQUESTS, RESPONSES, TASKS, read_events, request
from models import RentalListing, User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Require HEAD and the tested application files to match this tag")
    parser.add_argument("--output", default="reports/hw08/verification.json")
    args = parser.parse_args()
    checks = []

    def check(name, actual, expected=True):
        passed = actual == expected
        checks.append({"name": name, "passed": passed, "actual": actual, "expected": expected})
        print(f"{'PASS' if passed else 'FAIL'} {name}: {actual}", flush=True)

    metadata = AdminClient({"bootstrap.servers": BROKER}).list_topics(timeout=15)
    expected = {REQUESTS: 1, RESPONSES: 1, INBOX: 1, TASKS: 2, DRAFTS: 1, FINAL: 1, DEAD: 1}
    check("required topics and partitions", all(name in metadata.topics and len(metadata.topics[name].partitions) == partitions for name, partitions in expected.items()))
    created = request("CREATE_LISTING", SAMPLE)
    check("CREATE_LISTING success", created["success"])
    check("worker-generated UUID", str(UUID(created["listing_id"])) == created["listing_id"])
    fetched = request("GET_LISTING", {"listing_id": created["listing_id"]})
    check("GET_LISTING round trip", fetched.get("listing", {}).get("propertyTitle") == SAMPLE["propertyTitle"])
    failures = [("unknown operation", "DELETE_LISTING", {}, "Unknown operation"),
                ("unknown ID", "GET_LISTING", {"listing_id": str(uuid4())}, "Listing not found"),
                ("missing ID", "GET_LISTING", {}, "A valid listing_id UUID is required"),
                ("invalid ID", "GET_LISTING", {"listing_id": "not-a-uuid"}, "A valid listing_id UUID is required")]
    for name, operation, data, error in failures:
        cid = str(uuid4())
        response = request(operation, data, cid)
        check(name, not response["success"] and response.get("error") == error and response["correlation_id"] == cid)
    for field in SAMPLE:
        missing = {key: value for key, value in SAMPLE.items() if key != field}
        response = request("CREATE_LISTING", missing)
        check("required field " + field, not response["success"] and field in response.get("error", ""))
    for field, value in (("propertyTitle", " "), ("location", ""), ("submitterEmail", "bad"),
                         ("description", "short"), ("propertyType", "Boat"), ("termsAccepted", False)):
        response = request("CREATE_LISTING", {**SAMPLE, field: value})
        check("invalid field " + field, not response["success"] and field in response.get("error", ""))
    cid = str(uuid4())
    api = requests.post("http://127.0.0.1:8686/api/hw8/listings", json={"operation": "GET_LISTING", "data": {"listing_id": created["listing_id"]}, "correlation_id": cid}, timeout=30)
    check("FastAPI preserves supplied correlation", api.status_code == 200 and api.json().get("correlation_id") == cid and api.json().get("success"))
    check("HW7 missing token still 401", requests.get("http://127.0.0.1:8686/auth/me", timeout=10).status_code, 401)
    with SessionLocal() as db:
        before = db.scalar(select(func.count(RentalListing.id)))
        suffix = uuid4().hex[:10]
        user = User(name="HW8 smoke reader", username="hw8_" + suffix, email="hw8_" + suffix + "@example.com", role="reader", password_hash=bcrypt.hashpw(uuid4().hex.encode(), bcrypt.gensalt()).decode())
        db.add(user)
        db.commit()
        try:
            token = jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=2)}, os.environ["JWT_SECRET"], algorithm="HS256")
            response = requests.get("http://127.0.0.1:8686/api/listings", headers={"Authorization": "Bearer " + token}, timeout=20)
            page = response.json()
            check("existing MySQL listings API", response.status_code == 200 and bool(page.get("items")) and page.get("total") == before)
        finally:
            db.delete(user)
            db.commit()
        check("existing rental rows preserved", db.scalar(select(func.count(RentalListing.id))), before)
    mongo = requests.get("http://127.0.0.1:8686/api/document-listings", timeout=30)
    check("existing MongoDB documents API", mongo.status_code == 200 and isinstance(mongo.json(), list))
    from mcp_servers.rentals_server import search_listings
    check("existing MCP rental search", search_listings("San Jose", 2)["ok"])
    result = json.loads((RAW / "failure_results.json").read_text())
    check("baseline duplicate observed", result["before"]["duplicate"]["side_effects"], 2)
    check("idempotent replay makes one draft", result["duplicate"]["new_drafts"], 1)
    check("entity replay preserves UUID", result["entity_duplicate"]["same_uuid"])
    death = result["death"]
    check("killed Writer has not committed its input", death["committed_after_kill"] <= death["source"]["offset"])
    check("same offset redelivered", len(death["receives"]) == 2 and len({row["offset"] for row in death["receives"]}) == 1)
    check("commit after restart success", death["committed_after_success"], death["source"]["offset"] + 1)
    check("poison retry bound", result["poison"]["retry_count"], 3)
    check("dead-letter topic and later progress", result["poison"]["dead_letter"]["status"] == "dead_letter" and result["poison"]["later_completed"])
    check("two Writers and two unkeyed partitions", len(result["unkeyed"]["instances"]) == 2 and result["unkeyed"]["partitions"] == [0, 1])
    check("twenty unkeyed records", sorted(result["unkeyed"]["observed_order"]), list(range(1, 21)))
    check("one keyed partition and preserved order", len(result["keyed"]["partitions"]) == 1 and result["keyed"]["in_order"])
    journey = json.loads((RAW / "agent_journey.json").read_text())
    rows = read_events()
    stages = [row["stage"] for row in rows if row["event"] == "stage_send" and row.get("correlation_id") == journey["correlation_id"]]
    check("three-stage journey with same correlation", stages, ["planner", "writer", "reviewer"])
    check("final status and answer", journey["status"] in ("approved", "needs_review") and bool(journey["answer"]))
    source_paths = ["main.py", "hw8_kafka.py", "hw8_worker.py", "hw8_pipeline.py", "planner.py", "writer.py", "reviewer.py", "homework_demo.py", "send_question.py", "routers/hw8_listings.py", "compose.hw08.yml", "verify_hw08.py"]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if args.tag:
        tagged = subprocess.check_output(["git", "rev-parse", args.tag + "^{commit}"], text=True).strip()
        assert commit == tagged, "HEAD must be the tagged commit"
        subprocess.run(["git", "diff", "--exit-code", args.tag, "--", *source_paths], check=True)
    record = {"homework": 8, "sid4": "0686", "port_base": 8686, "prefix": "s0686", "seed": 686, "verify_seed": 260686,
              "domain_id": 6, "commit_hash": commit, "tested_tag": args.tag,
              "verification_scope": "tagged application" if args.tag else "pre-commit working tree; source hashes identify tested code",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(), "hardware": platform.platform(),
              "model": journey.get("model"), "ordering_model": "deterministic facts-only Writer; no model timing",
              "source_sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in source_paths},
              "checks": checks, "passed": all(item["passed"] for item in checks)}
    Path(args.output).write_text(json.dumps(record, indent=2))
    print(f"RESULT: {sum(item['passed'] for item in checks)}/{len(checks)} checks passed")
    if not record["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
