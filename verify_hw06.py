"""Objective, non-source-mutating verification for DATA 260 Homework 6."""

import json
from pathlib import Path
import subprocess

import requests
import yaml
from sqlalchemy import text

from database import SessionLocal
from hw6_config import ROOT, settings
from hw6_file_memory import contradiction_validation, count_memory_lines, verify_agent_compliance
from hw6_memory_service import clean_owned_user
from hw6_mongo import get_database, validator_for
from main import app


REPORTS = ROOT / "reports" / "hw06"
RAW = REPORTS / "raw"
BASE = "http://127.0.0.1:8686"
CHECKS: list[dict] = []


def add(name: str, passed: bool, detail: str) -> None:
    CHECKS.append({"name": name, "pass": bool(passed), "detail": detail})


def main() -> None:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    add("fastapi_import", app is not None, "main.app imported")
    try:
        response = requests.get(f"{BASE}/openapi.json", timeout=10)
        add("backend_port_8686", response.status_code == 200, f"HTTP {response.status_code}")
    except requests.RequestException as exc:
        add("backend_port_8686", False, exc.__class__.__name__)

    mongo = get_database()
    ping = mongo.command("ping").get("ok") == 1
    add("mongodb_responds", ping and mongo.name == "s0686_doc", f"database={mongo.name}, ping={ping}")
    validator = validator_for("rental_documents")
    add("rental_collection_validator", "$jsonSchema" in validator, "live $jsonSchema validator")

    created_id = None
    try:
        payload = {
            "title": "HW6 Verifier Temporary Rental",
            "property_type": "studio",
            "status": "available",
            "available_from": "2027-01-15T17:00:00Z",
        }
        created = requests.post(f"{BASE}/api/document-listings", json=payload, timeout=20)
        if created.status_code == 201:
            created_id = created.json()["id"]
        one = requests.get(f"{BASE}/api/document-listings/{created_id}", timeout=20) if created_id else None
        updated = requests.put(
            f"{BASE}/api/document-listings/{created_id}", json={"status": "pending"}, timeout=20
        ) if created_id else None
        deleted = requests.delete(f"{BASE}/api/document-listings/{created_id}", timeout=20) if created_id else None
        created_id = None if deleted is not None and deleted.status_code == 200 else created_id
        ok = (
            created.status_code == 201
            and one is not None and one.status_code == 200
            and updated is not None and updated.status_code == 200
            and deleted is not None and deleted.status_code == 200
        )
        add("part1_crud_round_trip_cleanup", ok, "POST/GET/PUT/DELETE over HTTP")
    finally:
        if created_id:
            requests.delete(f"{BASE}/api/document-listings/{created_id}", timeout=20)
    invalid = requests.post(
        f"{BASE}/api/document-listings", json={"title": "Invalid"}, timeout=20
    )
    add("part1_invalid_rejected", invalid.status_code == 422, f"HTTP {invalid.status_code}")

    verify_user = "verify-260686-chat"
    clean_owned_user(verify_user)
    chat = requests.post(
        f"{BASE}/api/chat",
        json={
            "user_id": verify_user,
            "session_id": "verify-260686-session",
            "message": "I need a quiet two-bedroom rental near light rail.",
        },
        timeout=240,
    )
    chat_json = chat.json() if chat.headers.get("content-type", "").startswith("application/json") else {}
    add(
        "chat_reply_and_memory_used",
        chat.status_code == 200 and bool(chat_json.get("reply")) and isinstance(chat_json.get("memory_used"), dict),
        f"HTTP {chat.status_code}",
    )
    memory = requests.get(f"{BASE}/api/memory/{verify_user}", timeout=20)
    aggregate = requests.get(f"{BASE}/api/aggregate/{verify_user}", timeout=20)
    add("memory_endpoint", memory.status_code == 200 and "messages" in memory.json(), f"HTTP {memory.status_code}")
    add(
        "aggregate_endpoint",
        aggregate.status_code == 200 and "daily_message_counts" in aggregate.json(),
        f"HTTP {aggregate.status_code}",
    )
    clean_owned_user(verify_user)

    collections = set(mongo.list_collection_names())
    required_collections = {"rental_documents", "messages", "summaries", "episodes"}
    add("required_mongodb_collections", required_collections.issubset(collections), ", ".join(sorted(collections)))
    episode = mongo.episodes.find_one({"embedding": {"$exists": True, "$ne": []}})
    numeric_embedding = bool(episode) and all(isinstance(value, (int, float)) for value in episode["embedding"])
    add("numeric_episode_embeddings", numeric_embedding, f"dimension={len(episode['embedding']) if episode else 0}")

    experiments = json.loads((RAW / "memory_experiment_results.json").read_text(encoding="utf-8"))
    metrics = experiments.get("condition_metrics", [])
    expected_conditions = {"SHORT_TERM_N=4", "SHORT_TERM_N=12", "SHORT_TERM_N=30", "relevance_aware_eviction"}
    condition_names = {item.get("condition") for item in metrics}
    row_counts_ok = len(metrics) == 4 and all(
        item.get("conversation_turns") == 30 and item.get("probe_turns") == 5 for item in metrics
    )
    add("experiment_conditions_and_rows", condition_names == expected_conditions and row_counts_ok, str(sorted(condition_names)))
    probe_file = yaml.safe_load((ROOT / "memory_probes.yaml").read_text(encoding="utf-8"))
    scores = json.loads((RAW / "memory_probe_scores.json").read_text(encoding="utf-8"))["results"]
    add("five_fixed_probes", len(probe_file.get("probes", [])) == 5, str(len(probe_file.get("probes", []))))
    add("all_probe_results_scored", len(scores) == 20 and all(1 <= item.get("score", 0) <= 5 for item in scores), str(len(scores)))

    original = (RAW / "memory_original_55.md").read_text(encoding="utf-8")
    consolidated = (RAW / "memory_consolidated.md").read_text(encoding="utf-8")
    add("original_memory_55_lines", count_memory_lines(original) == 55, str(count_memory_lines(original)))
    add("consolidated_memory_under_40", count_memory_lines(consolidated) < 40, str(count_memory_lines(consolidated)))
    contradiction = contradiction_validation(consolidated)
    add("duplicate_and_contradiction_checks", contradiction["all_pass"], contradiction["statement"])
    agent = verify_agent_compliance()
    add("agent_md_compliance", agent["pass"], agent["function"])

    with SessionLocal() as db:
        listings = db.execute(text("SELECT COUNT(*) FROM rental_listings")).scalar()
        notes = db.execute(text("SELECT COUNT(*) FROM listing_notes")).scalar()
        managers = db.execute(text("SELECT COUNT(*) FROM property_managers")).scalar()
    add("existing_mysql_counts", (listings, notes, managers) == (5000, 200, 1), f"{listings}/{notes}/{managers}")

    required_files = [
        "RUN_LOG.txt",
        "METRICS.md",
        "AI_USE.md",
        "report.pdf",
        "screenshots/SCREENSHOT_MANIFEST.md",
        "raw/part1_api_tests.json",
        "raw/chat_demo_10_messages.json",
        "raw/memory_experiment_results.json",
        "raw/memory_probe_scores.json",
        "raw/cost_calculations.json",
        "raw/memory_original_55.md",
        "raw/memory_consolidated.md",
        "raw/contradiction_validation.json",
        "raw/agent_compliance.json",
    ]
    missing = [name for name in required_files if not (REPORTS / name).exists()]
    add("required_report_evidence_files", not missing, "missing: " + ", ".join(missing) if missing else "all present")

    payload = {
        "homework": 6,
        "SID4": settings.sid4,
        "commit_hash_tested": commit,
        "model": settings.ollama_model,
        "configuration": {
            "PORT_BASE": settings.port_base,
            "MONGODB_DB": settings.mongodb_db,
            "SHORT_TERM_N_default": settings.short_term_n,
            "SUMMARIZE_EVERY_USER_MSGS": settings.summarize_every_user_msgs,
            "EPISODIC_TOP_K": settings.episodic_top_k,
            "temperature": 0.0,
            "num_ctx": 16384,
            "num_predict": 96,
        },
        "SEED": settings.seed,
        "VERIFY_SEED": settings.verify_seed,
        "checks": CHECKS,
        "overall_pass": all(item["pass"] for item in CHECKS),
    }
    (REPORTS / "verification.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not payload["overall_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
