import json
import urllib.request
from pathlib import Path

from sqlalchemy import text

from database import SessionLocal
from hw5_tool_runtime import execute_tool
from main import app


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports" / "hw05"
CHECKS = []


def add(name, ok, detail):
    CHECKS.append({"name": name, "pass": bool(ok), "detail": detail})


def tool_names(module_name):
    module = __import__(module_name, fromlist=["mcp"])
    return sorted(module.mcp._tool_manager._tools)


def main():
    commit = __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    add("fastapi_import", app is not None, "main.app imported")

    try:
        with urllib.request.urlopen("http://127.0.0.1:8686/openapi.json", timeout=3) as response:
            status = response.status
        add("backend_port_8686", status == 200, f"openapi status {status}")
    except Exception as exc:
        add("backend_port_8686", False, f"not responding: {exc.__class__.__name__}")

    db = SessionLocal()
    try:
        listings = db.execute(text("SELECT COUNT(*) FROM rental_listings")).scalar()
        notes = db.execute(text("SELECT COUNT(*) FROM listing_notes")).scalar()
        managers = db.execute(text("SELECT COUNT(*) FROM property_managers")).scalar()
        orphan_notes = db.execute(text(
            "SELECT COUNT(*) FROM listing_notes n LEFT JOIN rental_listings r "
            "ON n.listing_id = r.id WHERE r.id IS NULL"
        )).scalar()
        orphan_managers = db.execute(text(
            "SELECT COUNT(*) FROM rental_listings l LEFT JOIN property_managers m "
            "ON l.property_manager_id = m.id WHERE m.id IS NULL"
        )).scalar()
    finally:
        db.close()
    counts_ok = (listings, notes, managers, orphan_notes, orphan_managers) == (5000, 200, 1, 0, 0)
    add("db_counts", counts_ok, f"{listings}, {notes}, {managers}, orphans {orphan_notes}/{orphan_managers}")

    meals = tool_names("mcp_servers.meals_server")
    rentals = tool_names("mcp_servers.rentals_server")
    add("meals_server_tools", len(meals) == 4, ", ".join(meals))
    add("rentals_server_three_tools", rentals == [
        "aggregate_by_manager", "detail_lookup", "search_listings"
    ], ", ".join(rentals))

    listings_fixture = {
        1: {"id": 1, "available_units": 2, "location": "San Jose, CA", "property_title": "Open"},
        2: {"id": 2, "available_units": 0, "location": "Milpitas, CA", "property_title": "Closed"},
    }

    def fake_search(query, limit=5):
        if not str(query).strip():
            return {"ok": False, "data": None, "error": "query must not be blank."}
        return {"ok": True, "data": [listings_fixture[1]], "error": None}

    def fake_detail(listing_id):
        if int(listing_id) <= 0:
            return {"ok": False, "data": None, "error": "listing_id must be positive."}
        row = listings_fixture.get(int(listing_id))
        if row is None:
            return {"ok": False, "data": None, "error": "Rental listing not found."}
        return {"ok": True, "data": dict(row), "error": None}

    tools = {
        "search_listings": fake_search,
        "detail_lookup": fake_detail,
        "aggregate_by_manager": lambda manager_id: {"ok": True, "data": {"manager_id": int(manager_id)}, "error": None},
    }
    valid = json.loads(execute_tool("search_listings", {"query": "San Jose", "limit": 5}, tools=tools))
    invalid = json.loads(execute_tool("search_listings", {"query": "", "limit": 5}, tools=tools))
    blocked = json.loads(execute_tool("detail_lookup", {"listing_id": 2}, tools=tools))
    add("execute_tool_valid_envelope", valid.get("ok") is True and "data" in valid and valid.get("error") is None, "search envelope")
    add("execute_tool_invalid_error", invalid == {"ok": False, "data": None, "error": "query must not be blank."}, invalid.get("error"))
    add("safety_rule_offline", blocked == {"ok": False, "data": None, "error": "Listing is unavailable"}, blocked.get("error"))

    part4 = (REPORTS / "raw" / "part4_tests.txt").read_text()
    add("part4_nine_of_nine", "9/9 tests passed" in part4 and part4.count("PASS:") == 9, "part4_tests.txt")

    part3 = json.loads((REPORTS / "raw" / "part3_calls.json").read_text())
    add("part3_call_count", len(part3) == 150, str(len(part3)))

    log_path = REPORTS / "raw" / "agent_runs.jsonl"
    rows = []
    log_ok = log_path.exists()
    if log_ok:
        for line in log_path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    add("agent_log_jsonl", log_ok and len(rows) > 0, f"{len(rows)} records")

    latest = {}
    for row in rows:
        if row.get("scenario") in ("search", "detail", "aggregate", "multi_step"):
            latest[row["scenario"]] = row
    corrected = all(
        latest.get(name, {}).get("stop_reason") == "normal_completion" and latest.get(name, {}).get("tool_calls", 0) >= 1
        for name in ("search", "detail", "aggregate", "multi_step")
    )
    add("corrected_agent_scenarios", corrected, ", ".join(
        f"{name}:{latest.get(name, {}).get('stop_reason')}" for name in ("search", "detail", "aggregate", "multi_step")
    ))

    required = [
        "METRICS.md",
        "REFLECTION.md",
        "AI_USE.md",
        "RUN_LOG.txt",
        "report.pdf",
    ]
    missing = [name for name in required if not (REPORTS / name).exists()]
    add("report_files", not missing, "missing " + ", ".join(missing) if missing else "present")

    shots = [
        "P2A_02_meals_by_ingredient.png",
        "P2A_03_random_meal.png",
        "P2A_04_meal_details.png",
        "P2B_01_search_success.png",
        "P2B_02_search_invalid.png",
        "P2B_03_detail_success.png",
        "P2B_04_detail_invalid.png",
        "P2B_05_aggregate_success.png",
        "P2B_06_aggregate_invalid.png",
        "P4_01_tool_tests.png",
    ]
    missing_shots = [name for name in shots if not (REPORTS / "screenshots" / name).exists()]
    add("required_screenshots", not missing_shots, "missing " + ", ".join(missing_shots) if missing_shots else "present")

    overall = all(item["pass"] for item in CHECKS)
    payload = {
        "homework": 5,
        "SID4": "0686",
        "commit": commit,
        "local_model": "llama3.2:latest",
        "SEED": 686,
        "VERIFY_SEED": 260686,
        "overall_pass": overall,
        "checks": CHECKS,
    }
    out = REPORTS / "verification.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"overall_pass {overall}")
    for item in CHECKS:
        mark = "PASS" if item["pass"] else "FAIL"
        print(f"{mark}: {item['name']} ({item['detail']})")
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
