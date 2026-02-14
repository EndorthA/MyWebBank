# Backend/main.py
from fastapi import FastAPI

from .Routers import users, accounts, transactions
from .Routers import test_db  

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])

app.include_router(test_db.router) 