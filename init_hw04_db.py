from database import db_engine
from models import Base


Base.metadata.create_all(bind=db_engine)
print("HW4 tables initialized")
