import bcrypt
from sqlalchemy import select

from database import SessionLocal
from models import User


EMAIL = "farzaan@s0686.local"
NAME = "Farzaan"
PASSWORD = "rental260"


def main():
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == EMAIL))
        if existing is not None:
            print("User already exists")
            return
        password_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
        db.add(User(name=NAME, email=EMAIL, password_hash=password_hash))
        db.commit()
        print("Demo user created")
    finally:
        db.close()


if __name__ == "__main__":
    main()
