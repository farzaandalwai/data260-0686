from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(128), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    user = relationship("User", back_populates="sessions")


class RentalListing(Base):
    __tablename__ = "rental_listings"
    __table_args__ = (CheckConstraint("available_units >= 0", name="ck_available_units"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    listing_code = Column(String(50), nullable=False, unique=True)
    available_units = Column(Integer, nullable=False, default=1, server_default="1")
    property_manager_id = Column(Integer, ForeignKey("property_managers.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    property_manager = relationship("PropertyManager", back_populates="listings")
    notes = relationship("ListingNote", back_populates="listing")


class PropertyManager(Base):
    __tablename__ = "property_managers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    listings = relationship("RentalListing", back_populates="property_manager", passive_deletes="all")


class ListingNote(Base):
    __tablename__ = "listing_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("rental_listings.id"), nullable=False)
    note = Column(String(255), nullable=False)
    listing = relationship("RentalListing", back_populates="notes")
