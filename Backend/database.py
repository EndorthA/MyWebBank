from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# IMPORTANT: # Needs to be %23
# Tdakw2GFHV506#u3B_MY  →  Tdakw2GFHV506%23u3B_MY
DATABASE_URL = "mysql://root:Tdakw2GFHV506%23u3B_MY@localhost:3307/web_banking"

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

