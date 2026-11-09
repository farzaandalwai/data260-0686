import argparse
import json
import os
import requests
from uuid import uuid4

from hw8_kafka import FINAL, INBOX, RAW, consumer, log, producer, send, wait_for


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", default="What is known about this San Jose rental?")
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--cache", action="store_true", help="Use the HW9 cache in the existing FastAPI app")
    parser.add_argument("--listing-id", type=int, default=1)
    parser.add_argument("--field", choices=["listing_code", "location", "available_units", "property_title"], default="listing_code")
    args = parser.parse_args()
    if args.cache:
        token = os.environ.get("HW9_TOKEN")
        if not token:
            parser.error("Set HW9_TOKEN from the existing login flow; never commit it")
        response = requests.post("http://127.0.0.1:8686/api/hw9/ask", json={"query": args.question, "listing_id": args.listing_id, "field": args.field},
                                 headers={"Authorization": "Bearer " + token}, timeout=240)
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))
        return
    cid = str(uuid4())
    final = consumer("s0686_question_" + cid, FINAL)
    message = {"correlation_id": cid, "question": args.question, "entity_key": "rental-0686",
               "facts": {"location": "San Jose", "available_units": 2}, "use_model": args.model}
    try:
        metadata = send(producer(), INBOX, message, key=message["entity_key"])
        log("question_send", correlation_id=cid, message=message, **metadata)
        result = wait_for(final, cid, timeout=180)
        log("final_receive", correlation_id=cid, message=result, topic=FINAL)
        (RAW / "agent_journey.json").write_text(json.dumps(result, indent=2))
        print("FINAL", json.dumps(result))
    finally:
        final.close()


if __name__ == "__main__":
    main()
