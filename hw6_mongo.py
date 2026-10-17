"""MongoDB connection, validators, and indexes for HW6."""

from threading import Lock

from pymongo import ASCENDING, DESCENDING, MongoClient

from hw6_config import settings


_client: MongoClient | None = None
_initialized = False
_lock = Lock()


VALIDATORS = {
    "rental_documents": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "title", "status", "property_type", "available_from",
                "created_at", "updated_at",
            ],
            "properties": {
                "title": {"bsonType": "string", "minLength": 1, "maxLength": 100},
                "description": {"bsonType": ["string", "null"]},
                "status": {"enum": ["available", "pending", "rented"]},
                "property_type": {
                    "enum": ["apartment", "condo", "house", "studio", "townhouse"]
                },
                "available_from": {"bsonType": "date"},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    },
    "messages": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "session_id", "role", "content", "created_at"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "session_id": {"bsonType": "string"},
                "role": {"enum": ["user", "assistant"]},
                "content": {"bsonType": "string", "minLength": 1},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "summaries": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "session_id", "scope", "text", "created_at"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "session_id": {"bsonType": ["string", "null"]},
                "scope": {"enum": ["session", "user"]},
                "text": {"bsonType": "string", "minLength": 1},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "episodes": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "user_id", "session_id", "fact", "importance", "embedding", "created_at"
            ],
            "properties": {
                "user_id": {"bsonType": "string"},
                "session_id": {"bsonType": "string"},
                "fact": {"bsonType": "string", "minLength": 1, "maxLength": 500},
                "importance": {"bsonType": ["double", "int"], "minimum": 0, "maximum": 1},
                "embedding": {
                    "bsonType": "array",
                    "minItems": 1,
                    "items": {"bsonType": ["double", "int"]},
                },
                "created_at": {"bsonType": "date"},
            },
        }
    },
}


def get_client() -> MongoClient:
    """Return a reusable Mongo client without exposing its URI."""
    global _client
    if _client is None:
        _client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=3000,
            tz_aware=True,
        )
    return _client


def get_database():
    return get_client()[settings.mongodb_db]


def ensure_hw6_database() -> None:
    """Idempotently create validators and query indexes."""
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        db = get_database()
        db.command("ping")
        existing = set(db.list_collection_names())
        for name, validator in VALIDATORS.items():
            if name in existing:
                db.command({
                    "collMod": name,
                    "validator": validator,
                    "validationLevel": "strict",
                    "validationAction": "error",
                })
            else:
                db.create_collection(
                    name,
                    validator=validator,
                    validationLevel="strict",
                    validationAction="error",
                )
        for name in ("memory_usage",):
            if name not in existing:
                db.create_collection(name)

        db.messages.create_index(
            [("user_id", ASCENDING), ("session_id", ASCENDING), ("created_at", DESCENDING)],
            name="user_session_time",
        )
        db.summaries.create_index(
            [("user_id", ASCENDING), ("scope", ASCENDING), ("created_at", DESCENDING)],
            name="user_scope_time",
        )
        db.episodes.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="user_episode_time",
        )
        db.memory_usage.create_index(
            [("user_id", ASCENDING), ("session_id", ASCENDING), ("timestamp", DESCENDING)],
            name="user_session_usage_time",
        )
        _initialized = True


def get_collection(name: str):
    ensure_hw6_database()
    return get_database()[name]


def validator_for(name: str) -> dict:
    """Return the live collection validator for objective verification."""
    info = get_database().command("listCollections", filter={"name": name})
    batch = info.get("cursor", {}).get("firstBatch", [])
    if not batch:
        return {}
    return batch[0].get("options", {}).get("validator", {})
