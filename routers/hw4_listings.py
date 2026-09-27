from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from database import get_db
from models import RentalListing
from models import User
from routers.hw4_auth import get_current_user


router = APIRouter(prefix="/api/listings")


class ListingRequest(BaseModel):
    property_title: str
    location: str

    @field_validator("property_title", "location")
    @classmethod
    def required_text(cls, value):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


def listing_json(listing):
    return {
        "id": listing.id,
        "property_title": listing.property_title,
        "location": listing.location,
    }


def find_listing(db, listing_id):
    listing = db.get(RentalListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("", status_code=201)
def create_listing(
    data: ListingRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = RentalListing(property_title=data.property_title, location=data.location)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing_json(listing)


@router.get("")
def get_listings(
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.scalars(select(RentalListing).order_by(RentalListing.id)).all()
    return [listing_json(listing) for listing in rows]


@router.get("/{listing_id}")
def get_listing(
    listing_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listing_json(find_listing(db, listing_id))


@router.put("/{listing_id}")
def update_listing(
    listing_id: int,
    data: ListingRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = find_listing(db, listing_id)
    listing.property_title = data.property_title
    listing.location = data.location
    db.commit()
    db.refresh(listing)
    return listing_json(listing)


@router.delete("/{listing_id}")
def delete_listing(
    listing_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = find_listing(db, listing_id)
    db.delete(listing)
    db.commit()
    return {"message": "Listing deleted"}
