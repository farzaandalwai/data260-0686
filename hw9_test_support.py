import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

from database import SessionLocal
from models import User


@contextmanager
def reader_token():
    with SessionLocal() as db:
        suffix = uuid4().hex[:10]
        user = User(name="HW9 test reader", username="hw9_" + suffix, email="hw9_" + suffix + "@example.com",
                    role="reader", password_hash=bcrypt.hashpw(uuid4().hex.encode(), bcrypt.gensalt()).decode())
        db.add(user)
        db.commit()
        try:
            yield jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, os.environ["JWT_SECRET"], algorithm="HS256")
        finally:
            db.delete(user)
            db.commit()
