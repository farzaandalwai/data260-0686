from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from routers.auth import router as auth_router


app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key="s0686-rental-housing-dev",
    max_age=3600,
    same_site="lax",
    https_only=True,
)
app.include_router(auth_router)
base_path = Path(__file__).parent
listings = []
next_id = 1


class ListingInput(BaseModel):
    propertyTitle: str = Field(min_length=1)
    location: str = Field(min_length=1)
    submitterEmail: str = Field(min_length=3)
    description: str = Field(min_length=26)
    propertyType: Literal["Apartment", "House", "Condominium", "Townhouse"]
    termsAccepted: bool
    submissionDate: str | None = None


class RentalListing(BaseModel):
    id: int
    propertyTitle: str
    location: str
    submitterEmail: str
    description: str
    propertyType: str
    termsAccepted: bool
    submissionDate: str


@app.get("/listings-ui", response_class=FileResponse)
def read_listings_ui():
    return FileResponse(base_path / "index.html")


@app.get("/script.js", response_class=FileResponse)
def read_script():
    return FileResponse(base_path / "script.js")


@app.get("/listings", response_model=list[RentalListing])
def get_listings(search: str | None = None):
    if not search:
        return listings

    search_text = search.lower()
    return [
        listing
        for listing in listings
        if search_text in listing.propertyTitle.lower()
        or search_text in listing.location.lower()
    ]


@app.post("/listings", response_model=RentalListing, status_code=201)
def create_listing(data: ListingInput):
    global next_id

    listing = RentalListing(
        id=next_id,
        propertyTitle=data.propertyTitle,
        location=data.location,
        submitterEmail=data.submitterEmail,
        description=data.description,
        propertyType=data.propertyType,
        termsAccepted=data.termsAccepted,
        submissionDate=data.submissionDate
        or datetime.now(timezone.utc).isoformat(),
    )

    listings.append(listing)
    next_id += 1
    return listing


@app.put("/listings/{listing_id}", response_model=RentalListing)
def update_listing(listing_id: int, data: ListingInput):
    for index, listing in enumerate(listings):
        if listing.id == listing_id:
            updated_listing = RentalListing(
                id=listing_id,
                propertyTitle=data.propertyTitle,
                location=data.location,
                submitterEmail=data.submitterEmail,
                description=data.description,
                propertyType=data.propertyType,
                termsAccepted=data.termsAccepted,
                submissionDate=data.submissionDate or listing.submissionDate,
            )
            listings[index] = updated_listing
            return updated_listing

    raise HTTPException(status_code=404, detail="Listing not found")


@app.delete("/listings/{listing_id}")
def delete_listing(listing_id: int):
    for index, listing in enumerate(listings):
        if listing.id == listing_id:
            listings.pop(index)
            return {"message": "Listing deleted", "id": listing_id}

    raise HTTPException(status_code=404, detail="Listing not found")
