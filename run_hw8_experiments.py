import csv
import json
import random
import subprocess
import sys
import time
from uuid import uuid4

from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient

from homework_demo import SAMPLE
from hw8_kafka import BROKER, DEAD, RAW, TASKS, consumer, log, producer, read_events, request, send, wait_for


COMPOSE = ["docker", "compose", "-f", "compose.hw08.yml"]


def events():
    return read_events()


def wait_event(event, cid=None, minimum=1, timeout=90, **filters):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rows = [row for row in events() if row["event"] == event and (cid is None or row.get("correlation_id") == cid)
                and all(row.get(key) == value for key, value in filters.items())]
        if len(rows) >= minimum:
            return rows
        time.sleep(0.1)
    raise TimeoutError(f"Waiting for {event}: {cid} {filters}")


def compose(*args):
    result = subprocess.run(COMPOSE + list(args), text=True, capture_output=True, check=True)
    print(result.stdout + result.stderr, flush=True)
    log("docker_action", arguments=list(args), output=result.stdout + result.stderr)


def position(group):
    probe = Consumer({"bootstrap.servers": BROKER, "group.id": group})
    try:
        return probe.committed([TopicPartition(TASKS, 0)], timeout=10)[0].offset
    finally:
        probe.close()


def high_water():
    probe = Consumer({"bootstrap.servers": BROKER, "group.id": "s0686_probe_" + str(uuid4())})
    try:
        return probe.get_watermark_offsets(TopicPartition(TASKS, 0), timeout=10)[1]
    finally:
        probe.close()


def task(cid, **fields):
    return {"correlation_id": cid, "question": "Describe this rental", "facts": {"location": "San Jose", "available_units": 2},
            "entity_key": "rental-0686", **fields}


def baseline(mode, run_id, output):
    group = "s0686_before_" + mode + "_" + run_id
    start = high_water()
    handle = (RAW / f"before_{mode}.log").open("w")
    command = [sys.executable, "-m", "scripts.hw8_baseline", mode, "--group", group, "--offset", str(start)]
    process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT)
    wait_event("baseline_ready", mode=mode, group=group)
    cid = run_id + "-before-" + mode
    payload = task(cid)
    if mode == "poison":
        payload["question"] = ""
    if mode == "early":
        payload["baseline_delay"] = 30
    first = send(output, TASKS, payload, partition=0)
    try:
        if mode == "duplicate":
            wait_event("baseline_effect", cid)
            send(output, TASKS, payload, partition=0)
            rows = wait_event("baseline_effect", cid, minimum=2)
            result = {"side_effects": len(rows), "records": rows}
        elif mode == "early":
            wait_event("baseline_early_commit", cid)
            process.kill()
            process.wait()
            committed = position(group)
            process = subprocess.Popen(command + ["--resume"], stdout=handle, stderr=subprocess.STDOUT)
            wait_event("baseline_ready", mode=mode, group=group, minimum=2)
            control = cid + "-later"
            send(output, TASKS, task(control), partition=0)
            wait_event("baseline_effect", control)
            result = {"source_offset": first["offset"], "committed_after_kill": committed,
                      "original_effects": len([e for e in events() if e["event"] == "baseline_effect" and e.get("correlation_id") == cid]),
                      "later_completed": True}
        else:
            later = cid + "-later"
            send(output, TASKS, task(later), partition=0)
            retries = wait_event("baseline_poison_retry", cid, minimum=5)
            later_done = [e for e in events() if e["event"] == "baseline_effect" and e.get("correlation_id") == later]
            result = {"observed_retries_before_kill": len(retries), "later_completed": bool(later_done)}
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        handle.close()
    result["correlation_id"] = cid
    return result


def ordering(output, run_id, keyed, inputs):
    name = "keyed" if keyed else "unkeyed"
    run = run_id + "-" + name
    sent = []
    for item in inputs:
        payload = task(f"{run}-{item['sequence']:02}", **item, run_id=run)
        metadata = send(output, TASKS, payload, key="rental-0686" if keyed else None,
                        partition=-1 if keyed else (item["sequence"] - 1) % 2)
        sent.append({**metadata, "sequence": item["sequence"], "correlation_id": payload["correlation_id"], "key": "rental-0686" if keyed else None})
    wait_event("stage_complete", minimum=20, stage="writer", run_id=run, timeout=120)
    rows = [row for row in events() if row["event"] == "stage_complete" and row.get("stage") == "writer" and row.get("run_id") == run]
    rows.sort(key=lambda row: row["timestamp"])
    assert len(rows) == 20
    with (RAW / f"ordering_{name}.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["processing_index", "sequence", "partition", "offset", "instance", "timestamp", "correlation_id"])
        writer.writeheader()
        for index, row in enumerate(rows, 1):
            writer.writerow({"processing_index": index, **{key: row[key] for key in writer.fieldnames if key != "processing_index"}})
    return {"sent": sent, "processed": rows, "observed_order": [row["sequence"] for row in rows],
            "partitions": sorted({row["partition"] for row in rows}), "instances": sorted({row["instance"] for row in rows}),
            "in_order": [row["sequence"] for row in rows] == list(range(1, 21))}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    run_id = "hw8-" + uuid4().hex[:10]
    log("experiments_start", run_id=run_id, verify_seed=260686)
    output = producer()
    result = {"run_id": run_id, "verify_seed": 260686}
    compose("stop", "writer", "writer2")
    result["before"] = {mode: baseline(mode, run_id, output) for mode in ("duplicate", "early", "poison")}
    compose("up", "-d", "writer")
    entity_cid = run_id + "-entity-duplicate"
    one = request("CREATE_LISTING", SAMPLE, entity_cid)
    two = request("CREATE_LISTING", SAMPLE, entity_cid)
    assert one == two and one["success"]
    result["entity_duplicate"] = {"first": one, "replay": two, "same_uuid": one["listing_id"] == two["listing_id"]}
    duplicate = run_id + "-duplicate"
    send(output, TASKS, task(duplicate), partition=0)
    wait_event("offset_commit", duplicate, stage="writer")
    send(output, TASKS, task(duplicate), partition=0)
    wait_event("duplicate_skipped", duplicate, stage="writer")
    wait_event("offset_commit", duplicate, stage="writer", minimum=2)
    result["duplicate"] = {"correlation_id": duplicate, "new_drafts": len([e for e in events() if e["event"] == "stage_send" and e.get("stage") == "writer" and e.get("correlation_id") == duplicate]), "replay_skipped": True}
    death = run_id + "-death"
    metadata = send(output, TASKS, task(death, delay_seconds=15), partition=0)
    wait_event("processing_delay", death, stage="writer")
    before = position("s0686_writer")
    compose("kill", "-s", "SIGKILL", "writer")
    killed = position("s0686_writer")
    log("writer_killed", correlation_id=death, source_offset=metadata["offset"], committed_before=before, committed_after_kill=killed)
    compose("up", "-d", "writer")
    wait_event("stage_receive", death, stage="writer", minimum=2)
    wait_event("offset_commit", death, stage="writer", timeout=120)
    result["death"] = {"correlation_id": death, "source": metadata, "committed_before": before,
                       "committed_after_kill": killed, "committed_after_success": position("s0686_writer"),
                       "receives": [e for e in events() if e["event"] == "stage_receive" and e.get("stage") == "writer" and e.get("correlation_id") == death]}
    poison, later = run_id + "-poison", run_id + "-after-poison"
    dead_client = consumer("s0686_dlq_test_" + run_id, DEAD)
    try:
        send(output, TASKS, task(poison, question=""), partition=0)
        send(output, TASKS, task(later), partition=0)
        dead = wait_for(dead_client, poison)
        wait_event("offset_commit", later, stage="writer")
        result["poison"] = {"correlation_id": poison, "dead_letter": dead,
                            "retry_count": len([e for e in events() if e["event"] == "retry" and e.get("correlation_id") == poison]),
                            "later_correlation_id": later, "later_completed": True}
    finally:
        dead_client.close()
    compose("--profile", "ordering", "up", "-d", "writer2")
    admin = AdminClient({"bootstrap.servers": BROKER})
    deadline = time.monotonic() + 40
    while True:
        group = admin.describe_consumer_groups(["s0686_writer"])["s0686_writer"].result()
        if len(group.members) == 2 and all(len(member.assignment.topic_partitions) == 1 for member in group.members):
            break
        if time.monotonic() > deadline:
            raise TimeoutError("Two Writer assignments did not settle")
        time.sleep(0.3)
    result["writer_group"] = [{"client_id": member.client_id, "partitions": [p.partition for p in member.assignment.topic_partitions]} for member in group.members]
    rng = random.Random(260686)
    inputs = [{"sequence": index, "delay_seconds": round(rng.uniform(0.04, 0.25), 3),
               "facts": {"location": "San Jose", "available_units": rng.randint(1, 5)}} for index in range(1, 21)]
    inputs[0]["delay_seconds"] = 0.8
    (RAW / "ordering_input.json").write_text(json.dumps({"verify_seed": 260686, "messages": inputs}, indent=2))
    result["unkeyed"] = ordering(output, run_id, False, inputs)
    result["keyed"] = ordering(output, run_id, True, inputs)
    (RAW / "failure_results.json").write_text(json.dumps(result, indent=2))
    log("experiments_complete", run_id=run_id, unkeyed_order=result["unkeyed"]["observed_order"], keyed_order=result["keyed"]["observed_order"])
    print("RESULTS", json.dumps({"duplicate_drafts": result["duplicate"]["new_drafts"], "death_receives": len(result["death"]["receives"]), "poison_retries": result["poison"]["retry_count"], "unkeyed": result["unkeyed"]["observed_order"], "keyed": result["keyed"]["observed_order"]}), flush=True)


if __name__ == "__main__":
    main()
