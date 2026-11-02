from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hw8_kafka import log, request


router = APIRouter(prefix="/api/hw8", tags=["HW8 Kafka listings"])


class KafkaRequest(BaseModel):
    correlation_id: str | None = Field(default=None, min_length=1, max_length=100)
    operation: str
    data: dict


@router.post("/listings")
def listing_request(payload: KafkaRequest):
    try:
        response = request(payload.operation, payload.data, payload.correlation_id)
    except (TimeoutError, RuntimeError):
        raise HTTPException(status_code=503, detail="Kafka request could not complete") from None
    log("api_return", correlation_id=response["correlation_id"], success=response["success"])
    return response
