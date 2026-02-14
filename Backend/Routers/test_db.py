# Backend/Routers/test_db.py
from fastapi import APIRouter, Depends
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models  # ensures models are imported/registered

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/ping")
def ping(db: Session = Depends(get_db)):
    # Simple DB roundtrip
    db.execute(text("SELECT 1"))
    return {"db": "ok"}

@router.get("/tables")
def tables(db: Session = Depends(get_db)):
    # Shows tables that exist in the DB
    inspector = inspect(db.get_bind())
    return {"tables": inspector.get_table_names()}

@router.post("/seed-one-customer")
def seed_customer(db: Session = Depends(get_db)):
    # Works if you have models.Customer defined
    c = models.Customer(identity_card_num="AB1234567", afm="123456789", city="Athens")
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"customer_id": c.customer_id}