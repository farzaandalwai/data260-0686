"""MongoDB CRUD routes for rental listing documents."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from pymongo.errors import PyMongoError

from hw6_mongo import get_collection
from hw6_schemas import RentalDocumentCreate, RentalDocumentOut, RentalDocumentUpdate


router = APIRouter(prefix="/api/document-listings", tags=["HW6 document listings"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail="Invalid document listing ID")
    return ObjectId(value)


def serialize_document(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "title": document["title"],
        "description": document.get("description"),
        "status": document["status"],
        "property_type": document["property_type"],
        "available_from": document["available_from"],
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }


@router.post("", response_model=RentalDocumentOut, status_code=status.HTTP_201_CREATED)
def create_document_listing(payload: RentalDocumentCreate):
    collection = get_collection("rental_documents")
    now = utc_now()
    document = payload.model_dump(mode="python")
    document["status"] = payload.status.value
    document["property_type"] = payload.property_type.value
    document["created_at"] = now
    document["updated_at"] = now
    try:
        result = collection.insert_one(document)
        created = collection.find_one({"_id": result.inserted_id})
        return serialize_document(created)
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail="Database error while creating listing") from exc


@router.get("", response_model=list[RentalDocumentOut])
def list_document_listings():
    collection = get_collection("rental_documents")
    try:
        documents = collection.find().sort("created_at", -1)
        return [serialize_document(document) for document in documents]
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail="Database error while fetching listings") from exc


@router.get("/{listing_id}", response_model=RentalDocumentOut)
def get_document_listing(listing_id: str):
    object_id = parse_object_id(listing_id)
    collection = get_collection("rental_documents")
    try:
        document = collection.find_one({"_id": object_id})
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail="Database error while fetching listing") from exc
    if document is None:
        raise HTTPException(status_code=404, detail="Document listing not found")
    return serialize_document(document)


@router.put("/{listing_id}", response_model=RentalDocumentOut)
def update_document_listing(listing_id: str, payload: RentalDocumentUpdate):
    object_id = parse_object_id(listing_id)
    updates = payload.model_dump(exclude_unset=True, mode="python")
    if not updates:
        raise HTTPException(status_code=400, detail="At least one update field is required")
    for field in ("status", "property_type"):
        if field in updates:
            updates[field] = updates[field].value
    updates["updated_at"] = utc_now()
    collection = get_collection("rental_documents")
    try:
        result = collection.update_one({"_id": object_id}, {"$set": updates})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Document listing not found")
        document = collection.find_one({"_id": object_id})
        return serialize_document(document)
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail="Database error while updating listing") from exc


@router.delete("/{listing_id}")
def delete_document_listing(listing_id: str):
    object_id = parse_object_id(listing_id)
    collection = get_collection("rental_documents")
    try:
        result = collection.delete_one({"_id": object_id})
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail="Database error while deleting listing") from exc
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document listing not found")
    return {"message": "Document listing deleted", "id": listing_id}
