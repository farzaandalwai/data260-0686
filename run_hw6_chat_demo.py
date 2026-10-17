"""Create the required real ten-message memory demonstration."""

from datetime import datetime, timezone
import json

import requests
from sqlalchemy import text

from database import SessionLocal
from hw6_config import ROOT
from hw6_memory_service import clean_owned_user


BASE = "http://127.0.0.1:8686"
USER_ID = "demo-260686-memory"
SESSION_ID = "demo-260686-session"
MESSAGES = [
    "I prefer to search for rentals in Santa Clara, California.",
    "My maximum monthly rental budget is $3,500.",
    "I need a two-bedroom apartment.",
    "I prefer a commute under 30 minutes to downtown San Jose.",
    "I want one covered parking space.",
    "I need an in-unit washer and dryer.",
    "I have one indoor cat, so the building must allow cats.",
    "I need a smoke-free property.",
    "I prefer to live near light rail.",
    "Which city did I say I prefer for my rental search?",
]


def main() -> None:
    raw = ROOT / "reports" / "hw06" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    clean_owned_user(USER_ID)
    turns = []
    for number, message in enumerate(MESSAGES, start=1):
        response = requests.post(
            f"{BASE}/api/chat",
            json={"user_id": USER_ID, "session_id": SESSION_ID, "message": message},
            timeout=240,
        )
        response.raise_for_status()
        turns.append({"turn": number, "message": message, "response": response.json()})
        print(number, response.json()["reply"], flush=True)

    memory_response = requests.get(f"{BASE}/api/memory/{USER_ID}", timeout=30)
    aggregate_response = requests.get(f"{BASE}/api/aggregate/{USER_ID}", timeout=30)
    memory_response.raise_for_status()
    aggregate_response.raise_for_status()
    memory = memory_response.json()
    aggregate = aggregate_response.json()
    final = turns[-1]["response"]
    with SessionLocal() as db:
        mysql_count = db.execute(text("SELECT COUNT(*) FROM rental_listings")).scalar()
    checks = {
        "part1_crud_tests_pass": json.loads((raw / "part1_api_tests.json").read_text())["all_pass"],
        "ten_message_session": len(turns) == 10,
        "sliding_window_observed": final["memory_used"]["short_term_count"] == 12,
        "session_summary_exists": memory["latest_session_summary"] is not None,
        "lifetime_summary_exists": memory["latest_lifetime_summary"] is not None,
        "episode_embeddings_nonempty": bool(memory["episodes"]) and all(item["embedding"] for item in memory["episodes"]),
        "relevant_earlier_fact_retrieved": any(
            "santa clara" in item["fact"].lower()
            for item in final["memory_used"]["episodic_facts"]
        ),
        "assistant_grounded_in_memory": "santa clara" in final["reply"].lower(),
        "existing_mysql_behavior_available": mysql_count == 5000,
    }
    milestone = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "all_pass": all(checks.values()),
    }
    (raw / "chat_demo_10_messages.json").write_text(json.dumps(turns, indent=2) + "\n")
    (raw / "memory_demo.json").write_text(json.dumps(memory, indent=2) + "\n")
    (raw / "aggregate_demo.json").write_text(json.dumps(aggregate, indent=2) + "\n")
    (raw / "fast_milestone.json").write_text(json.dumps(milestone, indent=2) + "\n")
    print(json.dumps(milestone, indent=2))
    if not milestone["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
