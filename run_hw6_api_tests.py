"""Exercise real HW6 document CRUD and validation over HTTP."""

from datetime import datetime, timezone
import json
from pathlib import Path

import requests

from hw6_config import ROOT


BASE = "http://127.0.0.1:8686"
OUT = ROOT / "reports" / "hw06" / "raw" / "part1_api_tests.json"


def capture(name: str, response: requests.Response, expected: int) -> dict:
    try:
        body = response.json()
    except ValueError:
        body = {"text": response.text}
    return {
        "name": name,
        "status": response.status_code,
        "expected_status": expected,
        "pass": response.status_code == expected,
        "body": body,
    }


def main() -> None:
    results = []
    payload = {
        "title": "HW6 Temporary API Test Rental",
        "description": "Temporary record deleted by the test runner.",
        "status": "available",
        "property_type": "apartment",
        "available_from": "2026-12-01T17:00:00Z",
    }
    create = requests.post(f"{BASE}/api/document-listings", json=payload, timeout=20)
    results.append(capture("create", create, 201))
    create.raise_for_status()
    identifier = create.json()["id"]
    try:
        results.append(capture("retrieve_all", requests.get(f"{BASE}/api/document-listings", timeout=20), 200))
        results.append(capture("retrieve_one", requests.get(f"{BASE}/api/document-listings/{identifier}", timeout=20), 200))
        results.append(capture(
            "update",
            requests.put(f"{BASE}/api/document-listings/{identifier}", json={"status": "pending"}, timeout=20),
            200,
        ))
        results.append(capture(
            "missing_required_field",
            requests.post(f"{BASE}/api/document-listings", json={"property_type": "house"}, timeout=20),
            422,
        ))
        invalid_enum = {**payload, "status": "archived"}
        results.append(capture(
            "invalid_enum",
            requests.post(f"{BASE}/api/document-listings", json=invalid_enum, timeout=20),
            422,
        ))
        incorrect_type = {**payload, "available_from": ["not", "a", "date"]}
        results.append(capture(
            "incorrect_data_type",
            requests.post(f"{BASE}/api/document-listings", json=incorrect_type, timeout=20),
            422,
        ))
        results.append(capture(
            "invalid_object_id",
            requests.get(f"{BASE}/api/document-listings/not-an-object-id", timeout=20),
            400,
        ))
        results.append(capture(
            "missing_resource",
            requests.get(f"{BASE}/api/document-listings/000000000000000000000000", timeout=20),
            404,
        ))
        results.append(capture(
            "empty_update",
            requests.put(f"{BASE}/api/document-listings/{identifier}", json={}, timeout=20),
            400,
        ))
    finally:
        results.append(capture(
            "delete",
            requests.delete(f"{BASE}/api/document-listings/{identifier}", timeout=20),
            200,
        ))
    payload_out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "all_pass": all(row["pass"] for row in results),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload_out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload_out, indent=2))
    if not payload_out["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
