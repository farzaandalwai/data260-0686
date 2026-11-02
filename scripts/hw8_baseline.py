"""Deliberately unsafe consumers used only to measure the before-fix cases."""
import argparse
import json
import time

from confluent_kafka import Consumer, TopicPartition

from hw8_kafka import BROKER, TASKS, log
from hw8_pipeline import write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["duplicate", "early", "poison"])
    parser.add_argument("--group", required=True)
    parser.add_argument("--offset", type=int, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    client = Consumer({"bootstrap.servers": BROKER, "group.id": args.group, "enable.auto.commit": False})
    start = args.offset
    if args.resume:
        start = client.committed([TopicPartition(TASKS, 0)], timeout=10)[0].offset
    client.assign([TopicPartition(TASKS, 0, start)])
    log("baseline_ready", mode=args.mode, group=args.group, offset=start)
    effects = 0
    while True:
        record = client.poll(0.5)
        if record is None:
            continue
        if record.error():
            raise RuntimeError(str(record.error()))
        payload = json.loads(record.value())
        cid = payload["correlation_id"]
        log("baseline_receive", mode=args.mode, correlation_id=cid, offset=record.offset())
        if args.mode == "early":
            client.commit(record, asynchronous=False)
            log("baseline_early_commit", correlation_id=cid, committed_offset=record.offset() + 1)
            time.sleep(payload.get("baseline_delay", 0))
        while True:
            try:
                write(payload)
                break
            except ValueError:
                log("baseline_poison_retry", correlation_id=cid, offset=record.offset())
                time.sleep(0.25)
        effects += 1
        log("baseline_effect", mode=args.mode, correlation_id=cid, effects=effects, offset=record.offset())
        client.commit(record, asynchronous=False)


if __name__ == "__main__":
    main()
