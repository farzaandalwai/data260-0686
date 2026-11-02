import json
import os
import sqlite3
import time
from pathlib import Path

from confluent_kafka import TopicPartition

from hw8_kafka import DEAD, consumer, log, producer, send
from src.model_client import complete


def plan(message: dict) -> dict:
    question = message.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question is required")
    return {**message, "plan": ["Read the supplied rental facts", "Explain the facts without inventing details"]}


def write(message: dict) -> dict:
    if not isinstance(message.get("question"), str) or not message["question"].strip():
        raise ValueError("question is required")
    facts = message.get("facts", {})
    if not isinstance(facts, dict) or not facts:
        raise ValueError("rental facts are required")
    answer = "; ".join(f"{key}: {value}" for key, value in facts.items())
    if message.get("use_model"):
        result = complete([{"role": "user", "content": f"Answer this rental question using only these facts. Keep it short. Question: {message['question']} Facts: {json.dumps(facts)}"}], temperature=0.0, num_predict=120)
        answer = result["message"]
        message = {**message, "model": result["model"]}
    return {**message, "draft": answer}


def review(message: dict) -> dict:
    answer = message.get("draft")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("draft is required")
    facts = message.get("facts", {})
    approved = all(str(value).lower() in answer.lower() for value in facts.values())
    return {**message, "status": "approved" if approved else "needs_review", "answer": answer,
            "correlation_id": message["correlation_id"]}


def state_db() -> sqlite3.Connection:
    root = Path(".hw8_runtime")
    root.mkdir(exist_ok=True)
    db = sqlite3.connect(root / "pipeline.sqlite", timeout=30)
    db.execute("CREATE TABLE IF NOT EXISTS processed (stage TEXT, cid TEXT, response TEXT, sent INTEGER DEFAULT 0, PRIMARY KEY(stage,cid))")
    db.commit()
    return db


def process(stage: str, payload: dict, output, destination: str, handler, db) -> bool:
    cid = payload.get("correlation_id")
    if not isinstance(cid, str) or not cid.strip():
        raise ValueError("correlation_id is required")
    db.execute("BEGIN IMMEDIATE")
    try:
        existing = db.execute("SELECT response,sent FROM processed WHERE stage=? AND cid=?", (stage, cid)).fetchone()
        if existing and existing[1]:
            db.commit()
            log("duplicate_skipped", stage=stage, correlation_id=cid, instance=os.getenv("HW8_INSTANCE", stage))
            return False
        if existing:
            response = json.loads(existing[0])
        else:
            response = handler(payload)
            db.execute("INSERT INTO processed(stage,cid,response) VALUES(?,?,?)", (stage, cid, json.dumps(response)))
        db.commit()
    except Exception:
        db.rollback()
        raise
    metadata = send(output, destination, response, key=payload.get("entity_key"))
    db.execute("UPDATE processed SET sent=1 WHERE stage=? AND cid=?", (stage, cid))
    db.commit()
    log("stage_send", stage=stage, correlation_id=cid, **metadata, message=response,
        instance=os.getenv("HW8_INSTANCE", stage))
    return True


def run_stage(stage: str, source: str, destination: str, handler):
    client = consumer("s0686_" + stage, source)
    output, db = producer(), state_db()
    instance = os.getenv("HW8_INSTANCE", stage)
    log("stage_ready", stage=stage, instance=instance, source=source, destination=destination)
    try:
        while True:
            record = client.poll(0.5)
            if record is None:
                continue
            if record.error():
                log("consumer_error", stage=stage, error=str(record.error()))
                continue
            try:
                payload = json.loads(record.value())
                if not isinstance(payload, dict):
                    raise ValueError("message must be an object")
            except (ValueError, TypeError):
                payload = {"correlation_id": f"invalid-{record.partition()}-{record.offset()}", "invalid_json": True}
            cid = payload.get("correlation_id")
            committed = client.committed([TopicPartition(source, record.partition())], timeout=10)[0].offset
            log("stage_receive", stage=stage, instance=instance, correlation_id=cid, topic=source,
                partition=record.partition(), offset=record.offset(), committed_before=committed,
                sequence=payload.get("sequence"), run_id=payload.get("run_id"))
            delay = min(30, max(0, float(payload.get("delay_seconds", 0)))) if stage == "writer" else 0
            if delay:
                log("processing_delay", stage=stage, instance=instance, correlation_id=cid, seconds=delay)
                time.sleep(delay)
            for attempt in range(1, 4):
                try:
                    emitted = process(stage, payload, output, destination, handler, db)
                    log("stage_complete", stage=stage, instance=instance, correlation_id=cid,
                        partition=record.partition(), offset=record.offset(), sequence=payload.get("sequence"),
                        run_id=payload.get("run_id"), emitted=emitted)
                    break
                except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
                    log("retry", stage=stage, instance=instance, correlation_id=cid, attempt=attempt,
                        error=str(error), partition=record.partition(), offset=record.offset())
                    if attempt == 3:
                        dead = {"correlation_id": cid, "status": "dead_letter", "stage": stage,
                                "attempts": attempt, "error": str(error), "original": payload,
                                "source_topic": source, "partition": record.partition(), "offset": record.offset()}
                        metadata = send(output, DEAD, dead, key=str(cid))
                        log("dead_letter", stage=stage, correlation_id=cid, **metadata, message=dead)
                    else:
                        time.sleep(0.2)
            client.commit(record, asynchronous=False)
            log("offset_commit", stage=stage, instance=instance, correlation_id=cid, topic=source,
                partition=record.partition(), processed_offset=record.offset(), committed_offset=record.offset() + 1)
    finally:
        client.close()
        db.close()
