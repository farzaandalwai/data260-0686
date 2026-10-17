"""FastAPI routes for MongoDB-backed conversational memory."""

from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from hw6_memory_service import aggregate_user_memory, chat_turn, get_user_memory
from hw6_schemas import ChatRequest, ChatResponse


router = APIRouter(tags=["HW6 memory"])


@router.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    try:
        return chat_turn(payload)
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail="Database error while processing chat") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Local model failed to produce a reply") from exc


@router.get("/api/memory/{user_id}")
def memory(user_id: str):
    try:
        return get_user_memory(user_id)
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail="Database error while fetching memory") from exc


@router.get("/api/aggregate/{user_id}")
def aggregate(user_id: str):
    try:
        return aggregate_user_memory(user_id)
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail="Database error while aggregating memory") from exc
