# Backend/main.py
from fastapi import FastAPI

from .Routers import customers, users, admins, accounts, transactions, loans, auth
from .Routers import test_db  

app = FastAPI()

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(users.router)
app.include_router(admins.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(loans.router)

app.include_router(test_db.router) 