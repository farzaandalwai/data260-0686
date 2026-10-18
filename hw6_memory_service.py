"""Short-, long-, episodic-, and file-memory logic for HW6."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
from threading import Lock
import uuid

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from hw6_config import ROOT, settings
from hw6_file_memory import file_memory_prompt, handle_file_command
from hw6_mongo import get_collection
from hw6_schemas import ChatRequest
from src.model_client import complete


SYSTEM_PRIMER = (
    "You are a concise rental-housing assistant. Use the supplied memory when it is "
    "relevant, clearly distinguish remembered user preferences from general advice, "
    "and never invent a preference. Answer the current message directly."
)
COMPONENT_TOKENIZER = "MiniLM WordPiece estimate (not the exact llama3.2 tokenizer)"
COMMANDS = {"/memory", "/compact", "/dream", "/help"}
USAGE_LOG = ROOT / "reports" / "hw06" / "raw" / "chat_usage.jsonl"


@dataclass(frozen=True)
class RuntimeMemoryConfig:
    short_term_n: int = settings.short_term_n
    summarize_every_user_msgs: int = settings.summarize_every_user_msgs
    episodic_top_k: int = settings.episodic_top_k
    policy: str = "sliding"
    include_file_memory: bool = settings.file_memory_enabled


_embedding_model = None
_tokenizer = None
_embedding_lock = Lock()
_message_embedding_cache: dict[str, list[float]] = {}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_embedding_model():
    """Reuse the cached local Hugging Face embedding approach from HW3."""
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                from llama_index.embeddings.huggingface import HuggingFaceEmbedding

                _embedding_model = HuggingFaceEmbedding(model_name=settings.embedding_model)
    return _embedding_model


def embed_text(text: str) -> list[float]:
    vector = get_embedding_model().get_text_embedding(text)
    return [float(value) for value in vector]


def cached_embedding(text: str) -> list[float]:
    if text not in _message_embedding_cache:
        if len(_message_embedding_cache) > 1000:
            _message_embedding_cache.clear()
        _message_embedding_cache[text] = embed_text(text)
    return _message_embedding_cache[text]


def estimated_tokens(text: str) -> int:
    """Use one documented, reproducible local tokenizer for component estimates."""
    global _tokenizer
    if not text:
        return 0
    if _tokenizer is None:
        try:
            from transformers import AutoTokenizer

            _tokenizer = AutoTokenizer.from_pretrained(
                settings.embedding_model,
                local_files_only=True,
            )
        except Exception:
            _tokenizer = False
    if _tokenizer:
        return len(_tokenizer.encode(text, add_special_tokens=False))
    return len(re.findall(r"\w+|[^\w\s]", text))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def serialize_message(document: dict) -> dict:
    created_at = document.get("created_at")
    return {
        "role": document.get("role"),
        "content": document.get("content"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
    }


def serialize_summary(document: dict | None) -> dict | None:
    if document is None:
        return None
    created_at = document.get("created_at")
    return {
        "scope": document.get("scope"),
        "session_id": document.get("session_id"),
        "text": document.get("text"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
    }


def serialize_episode(document: dict, include_embedding: bool = False) -> dict:
    created_at = document.get("created_at")
    result = {
        "fact": document.get("fact"),
        "importance": document.get("importance"),
        "session_id": document.get("session_id"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
    }
    if include_embedding:
        result["embedding"] = document.get("embedding", [])
    return result


def latest_summary(user_id: str, scope: str, session_id: str | None = None) -> dict | None:
    query = {"user_id": user_id, "scope": scope}
    if scope == "session" and session_id is not None:
        query["session_id"] = session_id
    return get_collection("summaries").find_one(query, sort=[("created_at", DESCENDING)])


def standard_short_term(user_id: str, session_id: str, current_id: ObjectId, limit: int) -> list[dict]:
    query = {"user_id": user_id, "session_id": session_id, "_id": {"$ne": current_id}}
    rows = list(get_collection("messages").find(query).sort("created_at", DESCENDING).limit(limit))
    rows.reverse()
    return rows


def relevance_aware_short_term(
    user_id: str,
    session_id: str,
    current_id: ObjectId,
    query_embedding: list[float],
) -> list[dict]:
    """Keep four recent messages plus up to eight relevant older messages."""
    query = {"user_id": user_id, "session_id": session_id, "_id": {"$ne": current_id}}
    candidates = list(
        get_collection("messages").find(query).sort("created_at", DESCENDING).limit(30)
    )
    candidates.reverse()
    if len(candidates) <= 12:
        return candidates
    recent = candidates[-4:]
    older = candidates[:-4]
    scored = [
        (cosine_similarity(query_embedding, cached_embedding(row["content"])), row)
        for row in older
    ]
    selected = [row for _, row in sorted(scored, key=lambda item: item[0], reverse=True)[:8]]
    ids = {row["_id"] for row in selected + recent}
    return [row for row in candidates if row["_id"] in ids]


def retrieve_episodes(user_id: str, query_embedding: list[float], top_k: int) -> list[dict]:
    candidates = list(
        get_collection("episodes")
        .find({"user_id": user_id})
        .sort("created_at", DESCENDING)
        .limit(300)
    )
    scored = []
    for episode in candidates:
        score = cosine_similarity(query_embedding, episode.get("embedding", []))
        scored.append((score, episode))
    results = []
    for score, episode in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]:
        item = serialize_episode(episode)
        item["similarity"] = round(score, 6)
        results.append(item)
    return results


def extract_facts(message: str) -> list[dict]:
    """Deterministically extract up to three explicit user facts without a hosted API."""
    facts = []
    sentences = [" ".join(part.split()) for part in re.split(r"[.!?]+", message) if part.strip()]
    for sentence in sentences:
        lower = sentence.lower()
        explicit = re.search(r"\b(i|i'm|i'd|my|we|our)\b", lower)
        preference = any(
            marker in lower
            for marker in (
                "prefer", "need", "must", "budget", "move", "pet", "bedroom",
                "parking", "commute", "lease", "allergic", "work", "want",
            )
        )
        if not (explicit and preference):
            continue
        importance = 0.6
        if any(marker in lower for marker in ("must", "need", "allergic")):
            importance = 0.9
        elif any(marker in lower for marker in ("prefer", "budget", "move")):
            importance = 0.8
        facts.append({"fact": sentence[:500], "importance": importance})
        if len(facts) == 3:
            break
    return facts


def save_episodes(user_id: str, session_id: str, message: str) -> list[dict]:
    saved = []
    collection = get_collection("episodes")
    for item in extract_facts(message):
        document = {
            "user_id": user_id,
            "session_id": session_id,
            "fact": item["fact"],
            "importance": float(item["importance"]),
            "embedding": embed_text(item["fact"]),
            "created_at": utc_now(),
        }
        collection.insert_one(document)
        saved.append(serialize_episode(document))
    return saved


def deterministic_summary(user_messages: list[str]) -> str:
    unique = []
    for message in user_messages:
        compact = " ".join(message.split())[:240]
        if compact and compact not in unique:
            unique.append(compact)
    return "\n".join(f"- {message}" for message in unique[-10:])


def refresh_summaries(user_id: str, session_id: str, every: int) -> dict:
    messages = get_collection("messages")
    user_count = messages.count_documents({
        "user_id": user_id,
        "session_id": session_id,
        "role": "user",
    })
    result = {"user_message_count": user_count, "session_created": False, "lifetime_created": False}
    if user_count == 0 or user_count % every != 0:
        return result
    user_rows = list(
        messages.find({"user_id": user_id, "session_id": session_id, "role": "user"})
        .sort("created_at", ASCENDING)
    )
    text = deterministic_summary([row["content"] for row in user_rows])
    summaries = get_collection("summaries")
    summaries.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "scope": "session",
        "text": text,
        "created_at": utc_now(),
    })
    result["session_created"] = True

    session_summaries = list(
        summaries.find({"user_id": user_id, "scope": "session"})
        .sort("created_at", DESCENDING)
        .limit(6)
    )
    if len(session_summaries) >= 2 and len(session_summaries) % 2 == 0:
        lifetime_lines = []
        for summary in reversed(session_summaries):
            for line in summary["text"].splitlines():
                if line and line not in lifetime_lines:
                    lifetime_lines.append(line)
        summaries.insert_one({
            "user_id": user_id,
            "session_id": None,
            "scope": "user",
            "text": "\n".join(lifetime_lines[-20:]),
            "created_at": utc_now(),
        })
        result["lifetime_created"] = True
    return result


def format_short_term(messages: list[dict]) -> str:
    if not messages:
        return "(none)"
    return "\n".join(f"{row['role'].upper()}: {row['content']}" for row in messages)


def format_episodes(episodes: list[dict]) -> str:
    if not episodes:
        return "(none)"
    return "\n".join(
        f"- {episode['fact']} (similarity={episode['similarity']:.3f})"
        for episode in episodes
    )


def build_prompt_parts(
    current_message: str,
    short_term: list[dict],
    session_summary: dict | None,
    lifetime_summary: dict | None,
    episodes: list[dict],
    include_file_memory: bool,
) -> dict:
    system = SYSTEM_PRIMER
    if include_file_memory:
        system += "\n\n" + file_memory_prompt()
    long_term = (
        "=== LATEST SESSION SUMMARY ===\n"
        + (session_summary["text"] if session_summary else "(none)")
        + "\n\n=== LATEST LIFETIME SUMMARY ===\n"
        + (lifetime_summary["text"] if lifetime_summary else "(none)")
    )
    short = "=== PREVIOUS SHORT-TERM MESSAGES ===\n" + format_short_term(short_term)
    episodic = "=== RETRIEVED EPISODIC FACTS ===\n" + format_episodes(episodes)
    current = "=== CURRENT USER MESSAGE ===\n" + current_message
    user = "\n\n".join((long_term, short, episodic, current))
    return {
        "system": system,
        "long_term": long_term,
        "short_term": short,
        "episodic": episodic,
        "current": current,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }


def append_usage_log(record: dict) -> None:
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, default=str) + "\n")


def command_response(request: ChatRequest, session_id: str) -> dict:
    recent = list(
        get_collection("messages")
        .find({"user_id": request.user_id, "session_id": session_id})
        .sort("created_at", DESCENDING)
        .limit(16)
    )
    recent.reverse()
    command = handle_file_command(request.message, [serialize_message(row) for row in recent])
    return {
        "reply": command["text"],
        "user_id": request.user_id,
        "session_id": session_id,
        "memory_used": {
            "short_term_count": len(recent),
            "short_term_messages": [serialize_message(row) for row in recent],
            "session_summary": None,
            "lifetime_summary": None,
            "episodic_facts": [],
            "file_command": command,
        },
        "usage": {"command": True, "prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0},
    }


def chat_turn(
    request: ChatRequest,
    runtime: RuntimeMemoryConfig | None = None,
    condition: str = "api-default",
) -> dict:
    """Execute one fully instrumented normal chat turn or one exact file command."""
    runtime = runtime or RuntimeMemoryConfig()
    session_id = request.session_id or str(uuid.uuid4())
    if request.message in COMMANDS:
        return command_response(request, session_id)

    messages_collection = get_collection("messages")
    current_document = {
        "user_id": request.user_id,
        "session_id": session_id,
        "role": "user",
        "content": request.message,
        "created_at": utc_now(),
    }
    current_id = messages_collection.insert_one(current_document).inserted_id

    query_embedding = embed_text(request.message)
    if runtime.policy == "relevance_aware":
        short_term = relevance_aware_short_term(
            request.user_id, session_id, current_id, query_embedding
        )
    else:
        short_term = standard_short_term(
            request.user_id, session_id, current_id, runtime.short_term_n
        )
    session_summary = latest_summary(request.user_id, "session", session_id)
    lifetime_summary = latest_summary(request.user_id, "user")
    episodes = retrieve_episodes(request.user_id, query_embedding, runtime.episodic_top_k)
    parts = build_prompt_parts(
        request.message,
        short_term,
        session_summary,
        lifetime_summary,
        episodes,
        runtime.include_file_memory,
    )
    model_result = complete(
        parts["messages"],
        temperature=0.0,
        model=settings.ollama_model,
        num_ctx=16384,
        num_predict=96,
    )
    reply = model_result["message"].strip()
    if not reply:
        raise RuntimeError("Local model returned an empty reply")
    messages_collection.insert_one({
        "user_id": request.user_id,
        "session_id": session_id,
        "role": "assistant",
        "content": reply,
        "created_at": utc_now(),
    })
    saved_facts = save_episodes(request.user_id, session_id, request.message)
    summary_refresh = refresh_summaries(
        request.user_id,
        session_id,
        runtime.summarize_every_user_msgs,
    )

    usage = {
        "prompt_tokens": int(model_result["input_tokens"]),
        "completion_tokens": int(model_result["output_tokens"]),
        "system_primer_tokens": estimated_tokens(parts["system"]),
        "long_term_summary_tokens": estimated_tokens(parts["long_term"]),
        "short_term_window_tokens": estimated_tokens(parts["short_term"]),
        "episodic_fact_tokens": estimated_tokens(parts["episodic"]),
        "component_counts_are_estimates": True,
        "component_tokenizer": COMPONENT_TOKENIZER,
        "latency_ms": float(model_result["latency_ms"]),
        "model": model_result["model"],
    }
    usage_record = {
        **usage,
        "user_id": request.user_id,
        "session_id": session_id,
        "timestamp": utc_now(),
        "configuration": asdict(runtime),
        "condition": condition,
    }
    get_collection("memory_usage").insert_one(usage_record.copy())
    append_usage_log(usage_record)

    return {
        "reply": reply,
        "user_id": request.user_id,
        "session_id": session_id,
        "memory_used": {
            "short_term_count": len(short_term),
            "short_term_messages": [serialize_message(row) for row in short_term],
            "session_summary": serialize_summary(session_summary),
            "lifetime_summary": serialize_summary(lifetime_summary),
            "episodic_facts": episodes,
            "facts_saved_after_retrieval": saved_facts,
            "summary_refresh": summary_refresh,
        },
        "usage": usage,
    }


def get_user_memory(user_id: str) -> dict:
    messages = list(
        get_collection("messages")
        .find({"user_id": user_id})
        .sort("created_at", DESCENDING)
        .limit(16)
    )
    messages.reverse()
    episodes = list(
        get_collection("episodes")
        .find({"user_id": user_id})
        .sort("created_at", DESCENDING)
        .limit(20)
    )
    return {
        "user_id": user_id,
        "messages": [serialize_message(row) for row in messages],
        "latest_session_summary": serialize_summary(latest_summary(user_id, "session")),
        "latest_lifetime_summary": serialize_summary(latest_summary(user_id, "user")),
        "episodes": [serialize_episode(row, include_embedding=True) for row in episodes],
    }


def aggregate_user_memory(user_id: str) -> dict:
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "message_count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    daily = [
        {"date": row["_id"], "message_count": row["message_count"]}
        for row in get_collection("messages").aggregate(pipeline)
    ]
    summaries = list(
        get_collection("summaries")
        .find({"user_id": user_id})
        .sort("created_at", DESCENDING)
        .limit(6)
    )
    return {
        "user_id": user_id,
        "daily_message_counts": daily,
        "recent_summaries": [serialize_summary(row) for row in summaries],
    }


def clean_owned_user(user_id: str) -> dict:
    """Delete only an explicitly namespaced experiment or verifier user."""
    if not (
        user_id.startswith("exp-260686-")
        or user_id.startswith("verify-260686-")
        or user_id.startswith("demo-260686-")
    ):
        raise ValueError("cleanup is limited to HW6 experiment/verifier users")
    deleted = {}
    for name in ("messages", "summaries", "episodes", "memory_usage"):
        deleted[name] = get_collection(name).delete_many({"user_id": user_id}).deleted_count
    return deleted
