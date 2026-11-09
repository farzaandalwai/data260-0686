from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from hw9_cache import ListingNotFoundError, RentalCache, SemanticCache, listing_facts, shipped_threshold
from routers.hw7_auth import current_user


router = APIRouter(prefix="/api/hw9", tags=["HW9 rental cache"])


class Question(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    listing_id: int = Field(gt=0)
    field: Literal["listing_code", "location", "available_units", "property_title"]
    threshold: float | None = Field(default=None, ge=0, le=1)


@router.post("/ask")
def ask(question: Question, user=Depends(current_user)):
    try:
        listing_facts(question.listing_id, question.field)
        return SemanticCache(threshold=question.threshold if question.threshold is not None else shipped_threshold()).answer(question.query, question.listing_id, question.field)
    except ListingNotFoundError:
        raise HTTPException(status_code=404, detail="Listing not found") from None
    except (RedisError, RuntimeError, TimeoutError):
        raise HTTPException(status_code=503, detail="Local cache or agent service unavailable") from None


@router.get("/listings/{listing_id}")
def view_listing(listing_id: int = Path(gt=0), user=Depends(current_user)):
    try:
        result = listing_facts(listing_id, "property_title")
        result["views"] = RentalCache().increment_listing_views(listing_id)
        return result
    except ListingNotFoundError:
        raise HTTPException(status_code=404, detail="Listing not found") from None
