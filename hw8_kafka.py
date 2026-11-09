import json
import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from confluent_kafka import Consumer, Producer


PREFIX = "s0686"
REQUESTS = PREFIX + "_entity_requests"
RESPONSES = PREFIX + "_entity_responses"
INBOX, TASKS, DRAFTS, FINAL, DEAD = [PREFIX + "_" + name for name in ("inbox", "tasks", "drafts", "final", "dead_letter")]
BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
RAW = Path(os.getenv("HW8_RAW_DIR", "reports/hw08/raw"))


def log(event: str, **fields) -> dict:
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "pid": os.getpid(), **fields}
    line = json.dumps(record, separators=(",", ":")) + "\n"
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / f"events_{socket.gethostname()}_{os.getpid()}.jsonl"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, line.encode())
    finally:
        os.close(descriptor)
    print(line, end="", flush=True)
    return record


def read_events() -> list[dict]:
    records = {}
    for path in RAW.glob("events*.jsonl"):
        text = path.read_text()
        for line in text.rsplit("\n", 1)[0].splitlines():
            if line.strip():
                records[line] = json.loads(line)
    return sorted(records.values(), key=lambda row: row["timestamp"])


def producer() -> Producer:
    return Producer({"bootstrap.servers": BROKER, "enable.idempotence": True, "message.timeout.ms": 15000})


def consumer(group: str, topic: str) -> Consumer:
    client = Consumer({"bootstrap.servers": BROKER, "group.id": group, "auto.offset.reset": "earliest",
                       "enable.auto.commit": False, "enable.auto.offset.store": False,
                       "session.timeout.ms": 6000, "max.poll.interval.ms": 300000})
    client.subscribe([topic])
    return client


def send(client: Producer, topic: str, payload: dict, key: str | None = None, partition: int = -1) -> dict:
    delivered = []

    def callback(error, message):
        if error:
            delivered.append(error)
        else:
            delivered.append({"topic": message.topic(), "partition": message.partition(), "offset": message.offset()})

    client.produce(topic, value=json.dumps(payload).encode(), key=key, partition=partition, on_delivery=callback)
    if client.flush(20) or not delivered or not isinstance(delivered[0], dict):
        raise RuntimeError("Kafka delivery failed")
    return delivered[0]


def wait_for(client: Consumer, correlation_id: str, timeout: float = 60) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = client.poll(0.5)
        if message is None:
            continue
        if message.error():
            raise RuntimeError(str(message.error()))
        payload = json.loads(message.value())
        if payload.get("correlation_id") == correlation_id:
            return payload
    raise TimeoutError("No matching Kafka response")


def request(operation: str, data: dict, correlation_id: str | None = None) -> dict:
    correlation_id = correlation_id or str(uuid4())
    reply = consumer(PREFIX + "_client_" + str(uuid4()), RESPONSES)
    try:
        payload = {"correlation_id": correlation_id, "reply_to": RESPONSES, "operation": operation, "data": data}
        log("client_send", topic=REQUESTS, message=payload, correlation_id=correlation_id)
        send(producer(), REQUESTS, payload, key=correlation_id)
        response = wait_for(reply, correlation_id)
        log("client_receive", topic=RESPONSES, message=response, correlation_id=correlation_id)
        return response
    finally:
        reply.close()
