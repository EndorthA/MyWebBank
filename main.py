from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "API running"}

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users