import json
import os
import re
import time
from array import array
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import redis
import requests
from sqlalchemy import text

from database import db_engine
from hw8_kafka import FINAL, INBOX, consumer, producer, send, wait_for


PREFIX = "s0686:hw9"
INDEX = PREFIX + ":semantic_index"
FIELDS = ("listing_code", "location", "available_units", "property_title")
RAW = Path("reports/hw09/raw")


class ListingNotFoundError(ValueError):
    pass


def log(event: str, **fields) -> dict:
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    RAW.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, separators=(",", ":")) + "\n"
    with (RAW / f"hw9_events_{os.getpid()}.jsonl").open("a") as stream:
        stream.write(line)
    print(line, end="", flush=True)
    return record


def redis_client():
    return redis.Redis.from_url(os.getenv("HW9_REDIS_URL", "redis://127.0.0.1:6386/0"), socket_timeout=20, protocol=2)


def listing_facts(listing_id: int, field: str) -> dict:
    if field not in FIELDS or listing_id < 1:
        raise ValueError("A positive listing ID and supported field are required")
    with db_engine.connect() as connection:
        row = connection.execute(text("SELECT id AS listing_id,listing_code,location,available_units,property_title FROM rental_listings WHERE id=:id"), {"id": listing_id}).mappings().first()
    if row is None:
        raise ListingNotFoundError("Listing not found")
    return {"listing_id": row["listing_id"], field: row[field]}


def bump_data_version(db) -> None:
    db.execute(text("UPDATE s0686_cache_version SET version=version+1 WHERE id=1"))


def invalidate_data() -> int:
    with db_engine.begin() as connection:
        bump_data_version(connection)
        version = connection.execute(text("SELECT version FROM s0686_cache_version WHERE id=1")).scalar_one()
    log("data_invalidated", version=version)
    return version


def data_version() -> int:
    with db_engine.connect() as connection:
        return connection.execute(text("SELECT version FROM s0686_cache_version WHERE id=1")).scalar_one()


class RentalCache:
    def __init__(self):
        self.redis_client = redis_client()

    def increment_listing_views(self, listing_id: int) -> int:
        key = f"{PREFIX}:views:listing:{listing_id}"
        if not self.redis_client.exists(key):
            with db_engine.connect() as connection:
                count = connection.execute(text("SELECT view_count FROM rental_listings WHERE id=:id"), {"id": listing_id}).scalar_one_or_none()
            if count is None:
                raise ListingNotFoundError("Listing not found")
            self.redis_client.set(key, count, nx=True)
        count = self.redis_client.incr(key)
        if count % 10 == 0:
            with db_engine.begin() as connection:
                connection.execute(text("UPDATE rental_listings SET view_count=GREATEST(view_count,:count) WHERE id=:id"), {"count": count, "id": listing_id})
            log("views_synced", listing_id=listing_id, count=count, message="Synced views to database")
        return count


def embed(query: str) -> list[float]:
    response = requests.post(os.getenv("HW9_EMBED_URL", "http://127.0.0.1:11434/api/embed"),
                             json={"model": "nomic-embed-text:latest", "input": query}, timeout=120)
    response.raise_for_status()
    vector = response.json()["embeddings"][0]
    if len(vector) != 768:
        raise ValueError("Expected 768-dimensional nomic embedding")
    return vector


def pipeline_answer(query: str, facts: dict) -> dict:
    cid = str(uuid4())
    reply = consumer("s0686_hw9_" + cid, FINAL)
    try:
        message = {"correlation_id": cid, "question": query, "facts": facts, "use_model": True,
                   "response_json": True, "entity_key": "rental-" + str(facts["listing_id"])}
        metadata = send(producer(), INBOX, message, key=message["entity_key"])
        log("pipeline_ingress", correlation_id=cid, query=query, **metadata)
        result = wait_for(reply, cid, timeout=180)
        log("pipeline_final", correlation_id=cid, status=result["status"], answer=result["answer"], model=result.get("model"))
        return result
    finally:
        reply.close()


class SemanticCache:
    def __init__(self, namespace="live", threshold=0.85):
        if not re.fullmatch(r"[a-zA-Z0-9]+", namespace) or not 0 <= threshold <= 1:
            raise ValueError("Invalid cache namespace or threshold")
        self.namespace, self.threshold = namespace, threshold
        self.client = redis_client()
        try:
            self.client.execute_command("FT.CREATE", INDEX, "ON", "HASH", "PREFIX", 1, PREFIX + ":entry:",
                                        "SCHEMA", "namespace", "TAG", "version", "NUMERIC", "embedding", "VECTOR", "FLAT", 6,
                                        "TYPE", "FLOAT32", "DIM", 768, "DISTANCE_METRIC", "COSINE")
        except redis.ResponseError as error:
            if "Index already exists" not in str(error):
                raise

    def put(self, query: str, vector: list[float], result: dict, version: int, listing_id: int, field: str):
        key = f"{PREFIX}:entry:{self.namespace}:{uuid4().hex}"
        self.client.hset(key, mapping={"namespace": self.namespace, "version": version, "query": query,
                                      "embedding": array("f", vector).tobytes(), "answer": result["answer"],
                                      "correlation_id": result["correlation_id"], "listing_id": listing_id, "field": field})
        self.client.expire(key, 3600)
        return key

    def answer(self, query: str, listing_id: int, field: str, store_miss=True) -> dict:
        started = time.perf_counter()
        vector, version = embed(query), data_version()
        self.client.set(PREFIX + ":data_version", version)
        search = f"(@namespace:{{{self.namespace}}} @version:[{version} {version}])=>[KNN 1 @embedding $vector AS distance]"
        found = self.client.execute_command("FT.SEARCH", INDEX, search, "PARAMS", 2, "vector", array("f", vector).tobytes(),
                                            "SORTBY", "distance", "RETURN", 7, "query", "answer", "version", "correlation_id", "listing_id", "field", "distance", "DIALECT", 2)
        match = dict(zip(found[2][::2], found[2][1::2])) if found[0] else {}
        similarity = max(-1.0, min(1.0, 1 - float(match[b"distance"]))) if match else 0.0
        hit = bool(match) and similarity >= self.threshold
        if hit:
            answer, cid = match[b"answer"].decode(), match[b"correlation_id"].decode()
        else:
            result = pipeline_answer(query, listing_facts(listing_id, field))
            answer, cid = result["answer"], result["correlation_id"]
            if store_miss:
                self.put(query, vector, result, version, listing_id, field)
        response = {"query": query, "listing_id": listing_id, "field": field, "answer": answer,
                    "is_cached": hit, "similarity_score": round(similarity, 8), "data_version": version,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 3), "correlation_id": cid,
                    "matched_query": match.get(b"query", b"").decode(), "threshold": self.threshold}
        log("cache_hit" if hit else "cache_miss", namespace=self.namespace, **response)
        return response


def shipped_threshold() -> float:
    path = Path("hw9_cache_config.json")
    return json.loads(path.read_text())["threshold"] if path.exists() else 0.85
