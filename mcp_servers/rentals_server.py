import logging
from pathlib import Path
import sys

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal
from mcp_servers.common import response
from models import ListingNote, PropertyManager, RentalListing


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)
mcp = FastMCP("rentals", dependencies=["mcp<2", "sqlalchemy", "pymysql", "python-dotenv"])


def listing_summary(listing: RentalListing) -> dict:
    return {
        "id": listing.id,
        "property_title": listing.property_title,
        "location": listing.location,
        "listing_code": listing.listing_code,
        "available_units": listing.available_units,
        "property_manager_id": listing.property_manager_id,
    }


@mcp.tool(description="Search rental titles or locations using existing MySQL data.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
def search_listings(query: str, limit: int = 10) -> dict:
    if not query.strip():
        return response(error="query must not be blank.")
    if not 1 <= limit <= 25:
        return response(error="limit must be between 1 and 25.")
    try:
        with SessionLocal() as db:
            rows = db.scalars(
                select(RentalListing)
                .where(or_(
                    RentalListing.property_title.icontains(query.strip(), autoescape=True),
                    RentalListing.location.icontains(query.strip(), autoescape=True),
                ))
                .order_by(RentalListing.id).limit(limit)
            ).all()
            return response(data=[listing_summary(row) for row in rows])
    except SQLAlchemyError:
        logger.warning("Rental search failed")
        return response(error="Unable to read rental listings.")


@mcp.tool(description="Look up a rental listing with its manager and notes.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
def detail_lookup(listing_id: int) -> dict:
    if listing_id <= 0:
        return response(error="listing_id must be positive.")
    try:
        with SessionLocal() as db:
            listing = db.get(RentalListing, listing_id)
            if listing is None:
                return response(error="Rental listing not found.")
            data = listing_summary(listing)
            manager = listing.property_manager
            data["manager"] = {
                "id": manager.id,
                "first_name": manager.first_name,
                "last_name": manager.last_name,
                "email": manager.email,
            }
            notes = db.scalars(
                select(ListingNote).where(ListingNote.listing_id == listing_id).order_by(ListingNote.id)
            ).all()
            data["notes"] = [{"id": note.id, "note": note.note} for note in notes]
            return response(data=data)
    except SQLAlchemyError:
        logger.warning("Rental detail lookup failed")
        return response(error="Unable to read rental listing details.")


@mcp.tool(description="Count a manager's listings and sum their available units.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
def aggregate_by_manager(manager_id: int) -> dict:
    if manager_id <= 0:
        return response(error="manager_id must be positive.")
    try:
        with SessionLocal() as db:
            manager = db.get(PropertyManager, manager_id)
            if manager is None:
                return response(error="Property manager not found.")
            counts = db.execute(
                select(func.count(RentalListing.id), func.coalesce(func.sum(RentalListing.available_units), 0))
                .where(RentalListing.property_manager_id == manager_id)
            ).one()
            return response(data={
                "manager_id": manager.id,
                "first_name": manager.first_name,
                "last_name": manager.last_name,
                "email": manager.email,
                "listing_count": counts[0],
                "total_available_units": int(counts[1]),
            })
    except SQLAlchemyError:
        logger.warning("Manager aggregate failed")
        return response(error="Unable to read manager aggregates.")


if __name__ == "__main__":
    mcp.run(transport="stdio")
