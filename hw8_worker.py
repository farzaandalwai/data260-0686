import json
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, field_validator
from typing import Literal

from hw8_kafka import REQUESTS, RESPONSES, consumer, log, producer, send


class ListingData(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    propertyTitle: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)
    submitterEmail: EmailStr
    description: str = Field(min_length=26, max_length=2000)
    propertyType: Literal["Apartment", "House", "Condominium", "Townhouse"]
    termsAccepted: Literal[True]

    @field_validator("termsAccepted", mode="before")
    @classmethod
    def accepted(cls, value):
        if value is not True:
            raise ValueError("termsAccepted must be true")
        return value


def handle_request(message: dict, listings: dict) -> dict:
    cid = message.get("correlation_id")
    response = {"correlation_id": cid, "success": False}
    data = message.get("data")
    if not isinstance(cid, str) or not cid.strip() or message.get("reply_to") != RESPONSES:
        return {**response, "error": "Valid correlation_id and reply_to are required"}
    if not isinstance(data, dict):
        return {**response, "error": "data must be an object"}
    if message.get("operation") == "CREATE_LISTING":
        try:
            fields = ListingData.model_validate(data).model_dump(mode="json")
        except ValidationError as error:
            fields = [".".join(map(str, item["loc"])) for item in error.errors()]
            return {**response, "error": "Invalid listing fields: " + ", ".join(fields)}
        listing_id = str(uuid4())
        listings[listing_id] = {"listing_id": listing_id, **fields}
        return {**response, "success": True, "listing_id": listing_id, "message": "Listing created"}
    if message.get("operation") == "GET_LISTING":
        try:
            UUID(data.get("listing_id", ""))
        except (ValueError, TypeError, AttributeError):
            return {**response, "error": "A valid listing_id UUID is required"}
        listing = listings.get(data["listing_id"])
        return {**response, "success": True, "listing": listing} if listing else {**response, "error": "Listing not found"}
    return {**response, "error": "Unknown operation"}


def main():
    listings, completed = {}, {}
    client, output = consumer("s0686_entity_worker", REQUESTS), producer()
    print("Consumer is ready and listening...", flush=True)
    try:
        while True:
            record = client.poll(0.5)
            if record is None:
                continue
            if record.error():
                log("consumer_error", stage="worker", error=str(record.error()))
                continue
            try:
                message = json.loads(record.value())
                if not isinstance(message, dict):
                    raise ValueError("Request must be an object")
            except (ValueError, TypeError):
                log("worker_invalid_json", offset=record.offset())
                client.commit(record, asynchronous=False)
                continue
            cid = message.get("correlation_id")
            log("worker_receive", correlation_id=cid, message=message, partition=record.partition(), offset=record.offset())
            if isinstance(cid, str) and cid in completed:
                response = completed[cid]
                log("worker_duplicate", correlation_id=cid, listing_count=len(listings))
            else:
                response = handle_request(message, listings)
                if isinstance(cid, str) and cid.strip():
                    completed[cid] = response
                log("worker_process", correlation_id=cid, message=response, listing_count=len(listings))
            metadata = send(output, RESPONSES, response, key=cid if isinstance(cid, str) else None)
            log("worker_reply", correlation_id=cid, message=response, **metadata)
            client.commit(record, asynchronous=False)
    finally:
        client.close()


if __name__ == "__main__":
    main()
