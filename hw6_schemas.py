"""Pydantic request and response schemas for HW6."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RentalStatus(str, Enum):
    available = "available"
    pending = "pending"
    rented = "rented"


class PropertyType(str, Enum):
    apartment = "apartment"
    condo = "condo"
    house = "house"
    studio = "studio"
    townhouse = "townhouse"


class RentalDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    status: RentalStatus = RentalStatus.available
    property_type: PropertyType
    available_from: datetime

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class RentalDocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    status: RentalStatus | None = None
    property_type: PropertyType | None = None
    available_from: datetime | None = None

    @field_validator("title", "status", "property_type", "available_from", mode="before")
    @classmethod
    def reject_null_required_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("field cannot be null")
        return value

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class RentalDocumentOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    status: RentalStatus
    property_type: PropertyType
    available_from: datetime
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    session_id: str | None = Field(default=None, min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("user_id", "session_id", "message")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str
    memory_used: dict
    usage: dict
