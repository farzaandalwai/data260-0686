from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from database import get_db
from hw5_schemas import ListingRequest, ListingResponse, ListingsPage
from models import ListingNote, PropertyManager, RentalListing, User
from routers.hw4_auth import get_current_user


router = APIRouter(prefix="/api/listings")


def find_listing(db, listing_id):
    listing = db.get(RentalListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


def check_manager(db, manager_id):
    if db.get(PropertyManager, manager_id) is None:
        raise HTTPException(status_code=404, detail="Property manager not found")


def save_listing(db, listing):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Listing code already exists or related record changed")
    db.refresh(listing)
    return listing


@router.post("", response_model=ListingResponse, status_code=201)
def create_listing(
    data: ListingRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_manager(db, data.property_manager_id)
    listing = RentalListing(**data.model_dump())
    db.add(listing)
    return save_listing(db, listing)


@router.get("", response_model=ListingsPage)
def get_listings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.scalar(select(func.count()).select_from(RentalListing))
    rows = db.scalars(
        select(RentalListing).order_by(RentalListing.id)
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(
    listing_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return find_listing(db, listing_id)


@router.put("/{listing_id}", response_model=ListingResponse)
def update_listing(
    listing_id: int,
    data: ListingRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = find_listing(db, listing_id)
    check_manager(db, data.property_manager_id)
    for field, value in data.model_dump().items():
        setattr(listing, field, value)
    return save_listing(db, listing)


@router.delete("/{listing_id}")
def delete_listing(
    listing_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = find_listing(db, listing_id)
    if db.scalar(select(ListingNote.id).where(ListingNote.listing_id == listing_id).limit(1)):
        raise HTTPException(status_code=409, detail="Listing has notes and cannot be deleted")
    db.delete(listing)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Listing has related records and cannot be deleted")
    return {"message": "Listing deleted"}
