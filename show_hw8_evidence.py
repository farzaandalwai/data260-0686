import argparse
import csv
import json

from hw8_kafka import RAW, read_events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("part", choices=["roundtrip", "journey", "duplicate", "death", "poison", "unkeyed", "keyed", "checks"])
    args = parser.parse_args()
    rows = read_events()
    result = json.loads((RAW / "failure_results.json").read_text()) if (RAW / "failure_results.json").exists() else {}
    print("SAVED REAL RUN EVIDENCE:", args.part)
    if args.part == "roundtrip":
        demo = json.loads((RAW / "round_trip.json").read_text())
        for operation, response in (("CREATE_LISTING", demo["create"]), ("GET_LISTING", demo["get"])):
            cid = response["correlation_id"]
            print(operation, "correlation_id=" + cid)
            for row in demo["flow"]:
                if row["correlation_id"] != cid:
                    continue
                print(row["timestamp"][11:23], row["event"], row["message"]["correlation_id"], row.get("topic", ""))
            print("response:", json.dumps(response, indent=2))
    elif args.part == "journey":
        journey = json.loads((RAW / "agent_journey.json").read_text())
        print("correlation_id:", journey["correlation_id"])
        for row in rows:
            if row.get("correlation_id") == journey["correlation_id"] and row["event"] in ("question_send", "stage_receive", "stage_send", "final_receive"):
                print(row["timestamp"], row["event"], row.get("stage", "client"), row.get("topic", ""), "partition", row.get("partition", "-"), "offset", row.get("offset", "-"))
        print("Final JSON fields:", json.dumps({key: journey[key] for key in ("correlation_id", "status", "answer")}, indent=2))
        print("model:", journey.get("model"))
    elif args.part in ("unkeyed", "keyed"):
        with (RAW / f"ordering_{args.part}.csv").open() as stream:
            records = list(csv.DictReader(stream))
        print("VERIFY_SEED=260686; s0686_tasks: 2 partitions; group=s0686_writer; 2 instances")
        print("Key:", "rental-0686" if args.part == "keyed" else "none (round-robin partitions)")
        print("index seq partition offset instance  actual completion timestamp")
        for row in records:
            print(f"{row['processing_index']:>5} {row['sequence']:>3} {row['partition']:>9} {row['offset']:>6} {row['instance']:>8}  {row['timestamp']}")
        print("Observed order:", result[args.part]["observed_order"])
    elif args.part == "checks":
        record = json.loads(open("reports/hw08/verification.json").read())
        for item in record["checks"]:
            print("PASS" if item["passed"] else "FAIL", item["name"], ":", item["actual"])
        print("RESULT:", sum(item["passed"] for item in record["checks"]), "/", len(record["checks"]))
    else:
        data = result[args.part]
        cid = data["correlation_id"]
        print("correlation_id:", cid)
        if args.part == "duplicate":
            print("Before fix: side effects =", result["before"]["duplicate"]["side_effects"])
            for row in result["before"]["duplicate"]["records"]:
                print(row["timestamp"], row["event"], "effects", row["effects"], "offset", row["offset"])
            selected = [row for row in rows if row.get("correlation_id") == cid and row["event"] in ("stage_send", "duplicate_skipped", "offset_commit") and row.get("stage") == "writer"]
            print("After fix: new drafts=", data["new_drafts"], "replay skipped=", data["replay_skipped"])
            print("Entity replay same generated UUID:", result["entity_duplicate"]["same_uuid"], result["entity_duplicate"]["first"]["listing_id"])
        elif args.part == "death":
            print("Before fix: early commit", json.dumps(result["before"]["early"]))
            selected = [row for row in rows if row.get("correlation_id") == cid and row["event"] in ("stage_receive", "processing_delay", "writer_killed", "stage_complete", "offset_commit") and row.get("stage", "writer") == "writer"]
        else:
            print("Before fix:", json.dumps(result["before"]["poison"]))
            selected = [row for row in rows if row.get("correlation_id") in (cid, data["later_correlation_id"]) and row["event"] in ("retry", "dead_letter", "stage_complete", "offset_commit") and row.get("stage") == "writer"]
            print("Actual dead-letter fields:", json.dumps({key: value for key, value in data["dead_letter"].items() if key != "original"}, indent=2))
        for row in selected:
            print(row["timestamp"][11:26], row["event"], {key: row[key] for key in ("partition", "offset", "committed_before", "source_offset", "committed_after_kill", "processed_offset", "committed_offset", "attempt", "topic") if key in row})


if __name__ == "__main__":
    main()
