import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests
from dotenv import load_dotenv


load_dotenv()
BASE = "http://127.0.0.1:8686"
ACCOUNTS = Path(os.getenv("HW7_ACCOUNTS_FILE", "/tmp/s0686_hw7_accounts__86knqb7.json"))


def main():
    accounts = json.loads(ACCOUNTS.read_text())
    tokens = {}
    evidence = []

    def record(name, response, extra=None):
        item = {"case": name, "status": response.status_code}
        if extra:
            item.update(extra)
        evidence.append(item)
        suffix = f" {extra}" if extra else ""
        print(f"{name}: HTTP {response.status_code}{suffix}")

    for role in ("reader", "writer", "moderator"):
        username = role + "0686"
        response = requests.post(BASE + "/auth/login", json={"username": username, "password": accounts[username]}, timeout=10)
        tokens[role] = response.json()["access_token"]
        if role == "reader":
            record("login valid", response, {"jwt": tokens[role][:6] + "...[redacted]", "token_type": "bearer"})
    def head(role):
        return {"Authorization": "Bearer " + tokens[role]}
    record("login wrong password", requests.post(BASE + "/auth/login", json={"username": "reader0686", "password": "wrong"}, timeout=10))
    record("me missing token", requests.get(BASE + "/auth/me", timeout=10))
    record("me invalid token", requests.get(BASE + "/auth/me", headers={"Authorization": "Bearer invalid"}, timeout=10))
    expired = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, os.environ["JWT_SECRET"], algorithm="HS256")
    record("me expired token", requests.get(BASE + "/auth/me", headers={"Authorization": "Bearer " + expired}, timeout=10))
    record("list reader", requests.get(BASE + "/api/listings", headers=head("reader"), timeout=10))
    record("create reader", requests.post(BASE + "/api/listings", headers=head("reader"), json={}, timeout=10))
    record("delete writer", requests.delete(BASE + "/api/listings/999999", headers=head("writer"), timeout=10))
    listing_id = None
    try:
        payload = {"property_title": "HW7 auth evidence", "location": "San Jose, CA", "listing_code": f"RH-0686-{int(time.time())}", "available_units": 1, "property_manager_id": 1}
        created = requests.post(BASE + "/api/listings", headers=head("writer"), json=payload, timeout=10)
        record("create writer", created)
        if created.ok:
            listing_id = created.json()["id"]
            deleted = requests.delete(BASE + f"/api/listings/{listing_id}", headers=head("moderator"), timeout=10)
            record("delete moderator", deleted)
            listing_id = None
    finally:
        if listing_id is not None:
            requests.delete(BASE + f"/api/listings/{listing_id}", headers=head("moderator"), timeout=10)
    Path("reports/hw07/raw/part1_auth_http.json").write_text(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
