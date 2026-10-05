from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ManagerRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=255)

    @field_validator("first_name", "last_name")
    @classmethod
    def required_text(cls, value):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class ManagerResponse(ManagerRequest):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ListingRequest(BaseModel):
    property_title: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)
    listing_code: str = Field(pattern=r"^RH-0686-[0-9]{5,}$", max_length=50)
    available_units: int = Field(default=1, ge=0, strict=True)
    property_manager_id: int = Field(gt=0, strict=True)

    @field_validator("property_title", "location")
    @classmethod
    def required_text(cls, value):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class ListingResponse(ListingRequest):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ListingsPage(BaseModel):
    items: list[ListingResponse]
    total: int
    page: int
    page_size: int


class ManagersPage(BaseModel):
    items: list[ManagerResponse]
    total: int
    page: int
    page_size: int
