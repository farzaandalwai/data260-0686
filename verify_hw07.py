import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests
from dotenv import load_dotenv

from hw7_bike_tools import PRICE_URL, calculator, csv_sql
from hw7_file_tools import is_destructive


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
RAW = ROOT / "reports/hw07/raw"
BASE = "http://127.0.0.1:8686"
ACCOUNTS = Path(os.getenv("HW7_ACCOUNTS_FILE", "/tmp/s0686_hw7_accounts__86knqb7.json"))


def main():
    checks = []
    brief = "--brief" in sys.argv

    def check(name, actual, expected):
        passed = actual == expected
        checks.append({"name": name, "passed": passed, "actual": actual, "expected": expected})
        if not brief:
            print(f"{'PASS' if passed else 'FAIL'} {name}: {actual}")

    credentials = json.loads(ACCOUNTS.read_text())
    tokens = {}
    for username, password in credentials.items():
        response = requests.post(BASE + "/auth/login", json={"username": username, "password": password}, timeout=10)
        check(f"{username} login", response.status_code, 200)
        if response.ok:
            tokens[username] = response.json()["access_token"]

    def header(role):
        return {"Authorization": "Bearer " + tokens[f"{role}0686"]}

    check("bad password", requests.post(BASE + "/auth/login", json={"username": "reader0686", "password": "wrong"}, timeout=10).status_code, 401)
    check("missing bearer", requests.get(BASE + "/auth/me", timeout=10).status_code, 401)
    check("old session cookie rejected", requests.get(BASE + "/api/listings", cookies={"hw4_session_token": "invalid"}, timeout=10).status_code, 401)
    check("invalid bearer", requests.get(BASE + "/auth/me", headers={"Authorization": "Bearer invalid"}, timeout=10).status_code, 401)
    expired = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, os.environ["JWT_SECRET"], algorithm="HS256")
    check("expired bearer", requests.get(BASE + "/auth/me", headers={"Authorization": "Bearer " + expired}, timeout=10).status_code, 401)
    check("reader profile", requests.get(BASE + "/auth/me", headers=header("reader"), timeout=10).status_code, 200)
    check("reader list", requests.get(BASE + "/api/listings", headers=header("reader"), timeout=10).status_code, 200)
    check("reader create forbidden", requests.post(BASE + "/api/listings", headers=header("reader"), json={}, timeout=10).status_code, 403)
    check("writer delete forbidden", requests.delete(BASE + "/api/listings/999999", headers=header("writer"), timeout=10).status_code, 403)

    listing_id = None
    try:
        payload = {
            "property_title": "HW7 verification rental",
            "location": "San Jose, CA",
            "listing_code": f"RH-0686-{int(time.time())}",
            "available_units": 1,
            "property_manager_id": 1,
        }
        created = requests.post(BASE + "/api/listings", headers=header("writer"), json=payload, timeout=10)
        check("writer create", created.status_code, 201)
        if created.ok:
            listing_id = created.json()["id"]
            check("moderator read", requests.get(BASE + f"/api/listings/{listing_id}", headers=header("moderator"), timeout=10).status_code, 200)
            deleted = requests.delete(BASE + f"/api/listings/{listing_id}", headers=header("moderator"), timeout=10)
            check("moderator delete", deleted.status_code, 200)
            listing_id = None
    finally:
        if listing_id is not None:
            requests.delete(BASE + f"/api/listings/{listing_id}", headers=header("moderator"), timeout=10)

    member = (RAW / "divvy_member.csv").read_text()
    sparse = (RAW / "divvy_sparse.csv").read_text()
    for name, csv_text in (("member", member), ("sparse", sparse)):
        result = csv_sql("SELECT COUNT(*) AS n, SUM(scenario_selected) AS selected FROM uploaded", csv_text)
        check(f"{name} CSV rows", result["data"]["rows"][0]["n"], 500)
        trace = json.loads((RAW / f"bike_{name}_trace.json").read_text())
        check(f"{name} framework stop", trace["stop_reason"], "success")
    check("member decision", json.loads((RAW / "bike_member_trace.json").read_text())["result"]["decision"], "Buy Monthly Membership")
    check("sparse decision", json.loads((RAW / "bike_sparse_trace.json").read_text())["result"]["decision"], "Pay Per Ride/Minute")
    check("non-SELECT SQL rejected", csv_sql("DELETE FROM uploaded", member)["success"], False)
    check("calculator expression rejected", calculator("__import__('os')")["success"], False)
    check("recursive delete detected", is_destructive("rm -rf ."), True)
    check("find delete detected", is_destructive("find . -delete"), True)
    check("sandbox gate", json.loads((RAW / "part6_sandbox.json").read_text())["passed"], True)
    check("baseline attempts", len(json.loads((RAW / "part2_attempts.json").read_text())), 20)
    check("injection matrix", len(json.loads((RAW / "part5_injection_traces.json").read_text())), 9)
    metadata = json.loads((RAW / "divvy_sources.json").read_text())
    check("pricing snapshot SHA-256", hashlib.sha256((RAW / "divvy_pricing.html").read_bytes()).hexdigest(), metadata["pricing"]["html_sha256"])

    response = requests.post(
        BASE + "/api/hw7/bike/analyze",
        files={"csv_file": ("divvy_sparse.csv", sparse, "text/csv")},
        data={"pricing_url": PRICE_URL},
        timeout=180,
    )
    check("live bike API", response.status_code, 200)
    if response.ok:
        check("live bike API decision", (response.json().get("result") or {}).get("decision"), "Pay Per Ride/Minute")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    record = {
        "homework": 7,
        "sid4": "0686",
        "port_base": 8686,
        "prefix": "s0686",
        "seed": 686,
        "verify_seed": 260686,
        "domain_id": 6,
        "model": "llama3.2:latest",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_head_at_run": head,
        "machine": platform.platform(),
        "python": sys.version.split()[0],
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
    if "--stdout-only" not in sys.argv:
        target = ROOT / "reports/hw07/verification.json"
        target.write_text(json.dumps(record, indent=2))
    if brief:
        names = ("reader list", "writer create", "reader create forbidden", "bad password", "expired bearer", "moderator delete", "live bike API decision")
        print("Live cases: " + ", ".join(f"{item['name']}={item['actual']}" for item in checks if item["name"] in names))
    print(f"RESULT: {sum(item['passed'] for item in checks)}/{len(checks)} checks passed")
    if not record["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
