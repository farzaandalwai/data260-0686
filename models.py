from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    notes = relationship("ListingNote", back_populates="listing")


class ListingNote(Base):
    __tablename__ = "listing_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("rental_listings.id"), nullable=False)
    note = Column(String(255), nullable=False)
    listing = relationship("RentalListing", back_populates="notes")
