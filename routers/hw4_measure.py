from contextvars import ContextVar

from fastapi import APIRouter, Depends, Query
from sqlalchemy import event, select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from database import db_engine, get_db
from models import ListingNote, RentalListing, User
from routers.hw4_auth import get_current_user


router = APIRouter(prefix="/api/measure")
sql_statement_count = ContextVar("sql_statement_count", default=None)


def count_sql_statement(conn, cursor, statement, parameters, context, executemany):
    current = sql_statement_count.get()
    if current is None:
        return
    sql_statement_count.set(current + 1)


event.listen(db_engine, "before_cursor_execute", count_sql_statement)


def note_json(note):
    return {"id": note.id, "note": note.note}


def listing_json(listing, notes):
    ordered = sorted(notes, key=lambda note: note.id)
    return {
        "id": listing.id,
        "property_title": listing.property_title,
        "location": listing.location,
        "notes": [note_json(note) for note in ordered],
    }


def response_json(page_size, listings, statement_count):
    return {
        "page_size": page_size,
        "returned": len(listings),
        "sql_statements": statement_count,
        "listings": listings,
    }


@router.get("/listings/naive")
def naive_listings(
    page_size: int = Query(ge=1, le=200),
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = sql_statement_count.set(0)
    try:
        rows = db.scalars(
            select(RentalListing).order_by(RentalListing.id).limit(page_size)
        ).all()
        listings = []
        for listing in rows:
            notes = db.scalars(
                select(ListingNote)
                .where(ListingNote.listing_id == listing.id)
                .order_by(ListingNote.id)
            ).all()
            listings.append(listing_json(listing, notes))
        statement_count = sql_statement_count.get()
    finally:
        sql_statement_count.reset(token)
    return response_json(page_size, listings, statement_count)


@router.get("/listings/fixed")
def fixed_listings(
    page_size: int = Query(ge=1, le=200),
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = sql_statement_count.set(0)
    try:
        rows = db.scalars(
            select(RentalListing)
            .options(selectinload(RentalListing.notes))
            .order_by(RentalListing.id)
            .limit(page_size)
        ).all()
        listings = [listing_json(listing, listing.notes) for listing in rows]
        statement_count = sql_statement_count.get()
    finally:
        sql_statement_count.reset(token)
    return response_json(page_size, listings, statement_count)
