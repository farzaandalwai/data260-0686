import argparse
import json
from uuid import uuid4

from hw8_kafka import FINAL, INBOX, RAW, consumer, log, producer, send, wait_for


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", default="What is known about this San Jose rental?")
    parser.add_argument("--model", action="store_true")
    args = parser.parse_args()
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
