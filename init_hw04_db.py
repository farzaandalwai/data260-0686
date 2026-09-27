from database import db_session_basede26
from models import Base


Base.metadata.create_all(bind=db_session_basede26)
print("HW4 tables initialized")
