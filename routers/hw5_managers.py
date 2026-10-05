from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from database import get_db
from hw5_schemas import ManagerRequest, ManagerResponse, ManagersPage, ListingsPage
from models import PropertyManager, RentalListing, User
from routers.hw4_auth import get_current_user


router = APIRouter(prefix="/api/property-managers")


def find_manager(db, manager_id):
    manager = db.get(PropertyManager, manager_id)
    if manager is None:
        raise HTTPException(status_code=404, detail="Property manager not found")
    return manager


def save_manager(db, manager):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Property manager email already exists")
    db.refresh(manager)
    return manager


@router.post("", response_model=ManagerResponse, status_code=201)
def create_manager(
    data: ManagerRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    manager = PropertyManager(**data.model_dump())
    db.add(manager)
    return save_manager(db, manager)


@router.get("", response_model=ManagersPage)
def get_managers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.scalar(select(func.count()).select_from(PropertyManager))
    rows = db.scalars(
        select(PropertyManager).order_by(PropertyManager.id)
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/{manager_id}/listings", response_model=ListingsPage)
def manager_listings(
    manager_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    find_manager(db, manager_id)
    total = db.scalar(
        select(func.count()).select_from(RentalListing)
        .where(RentalListing.property_manager_id == manager_id)
    )
    rows = db.scalars(
        select(RentalListing).where(RentalListing.property_manager_id == manager_id)
        .order_by(RentalListing.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/{manager_id}", response_model=ManagerResponse)
def get_manager(
    manager_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return find_manager(db, manager_id)


@router.put("/{manager_id}", response_model=ManagerResponse)
def update_manager(
    manager_id: int,
    data: ManagerRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    manager = find_manager(db, manager_id)
    for field, value in data.model_dump().items():
        setattr(manager, field, value)
    return save_manager(db, manager)


@router.delete("/{manager_id}")
def delete_manager(
    manager_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    manager = find_manager(db, manager_id)
    if db.scalar(select(RentalListing.id).where(RentalListing.property_manager_id == manager_id).limit(1)):
        raise HTTPException(status_code=409, detail="Property manager still has listings")
    db.delete(manager)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Property manager still has listings")
    return {"message": "Property manager deleted"}
