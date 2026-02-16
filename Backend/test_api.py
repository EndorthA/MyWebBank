# Backend/test_api.py
"""
Comprehensive API tests for all routers.
Run with: pytest test_api.py -v (from Backend directory)
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import Backend as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.main import app
from Backend.database import Base, get_db


# ============================================================
# Test Database Setup
# ============================================================

# Use PostgreSQL for testing (same as production)
SQLALCHEMY_TEST_DATABASE_URL = "postgresql+psycopg2://webbank:webbank@localhost:5432/webbank_test"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    pool_pre_ping=True
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True, scope="function")
def clear_database():
    """Clear all tables before each test for isolation."""
    # Drop all tables before test
    Base.metadata.drop_all(bind=engine)
    # Create all tables fresh
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_customer():
    """Create a test customer."""
    response = client.post("/customers", json={
        "identity_card_num": "AB1234567",
        "afm": "123456789",
        "address": "123 Main St",
        "zip_code": "10001",
        "city": "Athens",
        "citizenship": "Greece"
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def test_user(test_customer):
    """Create a test user and return with token."""
    # Register user
    response = client.post("/auth/register", params={"customer_id": test_customer["customer_id"]}, json={
        "customer_id": test_customer["customer_id"],
        "email": "testuser@example.com",
        "phone": "1234567890",
        "password": "SecurePassword123"
    })
    assert response.status_code == 201
    user_data = response.json()
    
    # Login and get token
    login_response = client.post("/auth/login", json={
        "email": "testuser@example.com",
        "password": "SecurePassword123"
    })
    assert login_response.status_code == 200
    token_data = login_response.json()
    
    return {
        "user": user_data,
        "token": token_data["access_token"]
    }


@pytest.fixture
def test_admin():
    """Create a test admin and return with token."""
    # Create admin
    response = client.post("/admins", json={
        "username": "testadmin",
        "email": "admin@example.com",
        "phone": "9876543210",
        "password": "AdminPass123",
        "role": "super_admin"
    })
    assert response.status_code == 201
    admin_data = response.json()
    
    # Login and get token
    login_response = client.post("/auth/admin/login", json={
        "username": "testadmin",
        "password": "AdminPass123"
    })
    assert login_response.status_code == 200
    token_data = login_response.json()
    
    return {
        "admin": admin_data,
        "token": token_data["access_token"]
    }


@pytest.fixture
def test_account(test_customer):
    """Create a test account."""
    response = client.post("/accounts", json={
        "customer_id": test_customer["customer_id"],
        "currency": "EUR",
        "card_nr": "1234567890123456"
    })
    assert response.status_code == 201
    return response.json()


# ============================================================
# Customer Tests
# ============================================================

class TestCustomers:
    
    def test_create_customer(self):
        response = client.post("/customers", json={
            "identity_card_num": "AB1234567",
            "afm": "123456789",
            "city": "Athens"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["identity_card_num"] == "AB1234567"
        assert data["afm"] == "123456789"
        assert data["is_deleted"] is False

    def test_get_customer(self, test_customer):
        response = client.get(f"/customers/{test_customer['customer_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == test_customer["customer_id"]

    def test_get_nonexistent_customer(self):
        response = client.get("/customers/9999")
        assert response.status_code == 404

    def test_list_customers(self, test_customer):
        response = client.get("/customers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_update_customer(self, test_customer):
        response = client.put(f"/customers/{test_customer['customer_id']}", json={
            "identity_card_num": "CD9876543",
            "afm": "987654321",
            "city": "Thessaloniki"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Thessaloniki"

    def test_delete_customer(self, test_customer):
        response = client.delete(f"/customers/{test_customer['customer_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_deleted"] is True


# ============================================================
# User Tests
# ============================================================

class TestUsers:
    
    def test_create_user(self, test_customer):
        response = client.post("/auth/register", params={"customer_id": test_customer["customer_id"]}, json={
            "customer_id": test_customer["customer_id"],
            "email": "newuser@example.com",
            "phone": "1111111111",
            "password": "MyPassword123"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"

    def test_get_user(self, test_user):
        response = client.get(f"/users/{test_user['user']['user_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user["user"]["user_id"]

    def test_deactivate_user(self, test_user):
        response = client.delete(f"/users/{test_user['user']['user_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_deleted"] is True


# ============================================================
# Admin Tests
# ============================================================

class TestAdmins:
    
    def test_create_admin(self):
        response = client.post("/admins", json={
            "username": "newadmin",
            "email": "newadmin@example.com",
            "phone": "5555555555",
            "password": "AdminPassword123",
            "role": "admin"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newadmin"

    def test_get_admin(self, test_admin):
        response = client.get(f"/admins/{test_admin['admin']['admin_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["admin_id"] == test_admin["admin"]["admin_id"]

    def test_list_admins(self, test_admin):
        response = client.get("/admins")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_deactivate_admin(self, test_admin):
        response = client.delete(f"/admins/{test_admin['admin']['admin_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_deleted"] is True


# ============================================================
# Auth Tests
# ============================================================

class TestAuth:
    
    def test_user_login_success(self, test_customer):
        # Register user
        client.post("/auth/register", params={"customer_id": test_customer["customer_id"]}, json={
            "customer_id": test_customer["customer_id"],
            "email": "auth@example.com",
            "password": "password123"
        })
        
        # Login
        response = client.post("/auth/login", json={
            "email": "auth@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_user_login_wrong_password(self, test_customer):
        # Register user
        client.post("/auth/register", params={"customer_id": test_customer["customer_id"]}, json={
            "customer_id": test_customer["customer_id"],
            "email": "auth2@example.com",
            "password": "password123"
        })
        
        # Try login with wrong password
        response = client.post("/auth/login", json={
            "email": "auth2@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_admin_login_success(self):
        # Create admin
        client.post("/admins", json={
            "username": "authtest",
            "email": "authtest@example.com",
            "password": "adminpass123",
            "role": "super_admin"
        })
        
        # Login
        response = client.post("/auth/admin/login", json={
            "username": "authtest",
            "password": "adminpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_admin_login_wrong_password(self):
        # Create admin
        client.post("/admins", json={
            "username": "authtest2",
            "email": "authtest2@example.com",
            "password": "adminpass123",
            "role": "admin"
        })
        
        # Try login with wrong password
        response = client.post("/auth/admin/login", json={
            "username": "authtest2",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_get_user_profile(self, test_user):
        """Test getting user profile with token."""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["role"] == "customer"

    def test_get_user_profile_without_token(self):
        """Test that profile endpoint requires token."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_admin_profile(self, test_admin):
        """Test getting admin profile with token."""
        headers = {"Authorization": f"Bearer {test_admin['token']}"}
        response = client.get("/auth/admin/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testadmin"
        assert data["role"] == "super_admin"

    def test_get_admin_profile_without_token(self):
        """Test that admin profile endpoint requires token."""
        response = client.get("/auth/admin/me")
        assert response.status_code == 401


# ============================================================
# Account Tests
# ============================================================

class TestAccounts:
    
    def test_create_account(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/accounts", json={
            "customer_id": test_customer["customer_id"],
            "currency": "EUR",
            "card_nr": "1111111111111111"
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["currency"] == "EUR"
        assert float(data["balance"]) == 0

    def test_get_account(self, test_user, test_account):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.get(f"/accounts/{test_account['account_id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == test_account["account_id"]

    def test_list_accounts_for_customer(self, test_user, test_account, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.get(f"/accounts/customer/{test_customer['customer_id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_deposit(self, test_user, test_account):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post(f"/accounts/{test_account['account_id']}/deposit", json={
            "amount": 1000.50,
            "currency": "EUR"
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert float(data["balance"]) == 1000.50

    def test_withdraw_success(self, test_user, test_account):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        # First deposit
        client.post(f"/accounts/{test_account['account_id']}/deposit", json={
            "amount": 500,
            "currency": "EUR"
        }, headers=headers)
        # Then withdraw
        response = client.post(f"/accounts/{test_account['account_id']}/withdraw", json={
            "amount": 200,
            "currency": "EUR"
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert float(data["balance"]) == 300

    def test_withdraw_insufficient_funds(self, test_user, test_account):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post(f"/accounts/{test_account['account_id']}/withdraw", json={
            "amount": 1000,
            "currency": "EUR"
        }, headers=headers)
        assert response.status_code == 400

    def test_update_account_status(self, test_user, test_account):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.put(f"/accounts/{test_account['account_id']}/status", json={
            "status_value": "frozen"
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "frozen"


# ============================================================
# Transaction Tests
# ============================================================

class TestTransactions:
    
    def test_create_transaction(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        # Create two accounts
        acc1 = client.post("/accounts", json={
            "customer_id": test_customer["customer_id"],
            "currency": "EUR"
        }, headers=headers).json()
        acc2 = client.post("/accounts", json={
            "customer_id": test_customer["customer_id"],
            "currency": "EUR"
        }, headers=headers).json()
        
        # Deposit money in first account
        client.post(f"/accounts/{acc1['account_id']}/deposit", json={
            "amount": 1000,
            "currency": "EUR"
        }, headers=headers)
        
        # Create transaction
        response = client.post("/transactions", json={
            "sender_account_id": acc1["account_id"],
            "receiver_account_id": acc2["account_id"],
            "amount": 500,
            "currency": "EUR",
            "comment": "Test transfer"
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert float(data["amount"]) == 500
        assert data["status"] == "completed"


    def test_get_transaction(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        # Setup accounts
        acc1 = client.post("/accounts", json={
            "customer_id": test_customer["customer_id"],
            "currency": "EUR"
        }, headers=headers).json()
        acc2 = client.post("/accounts", json={
            "customer_id": test_customer["customer_id"],
            "currency": "EUR"
        }, headers=headers).json()
        
        client.post(f"/accounts/{acc1['account_id']}/deposit", json={
            "amount": 1000,
            "currency": "EUR"
        }, headers=headers)
        
        # Create transaction
        tx = client.post("/transactions", json={
            "sender_account_id": acc1["account_id"],
            "receiver_account_id": acc2["account_id"],
            "amount": 500,
            "currency": "EUR"
        }, headers=headers).json()
        
        # Get transaction
        response = client.get(f"/transactions/{tx['transaction_id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["transaction_id"] == tx["transaction_id"]

    def test_list_transactions_for_account(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        # Setup accounts
        acc1 = client.post("/accounts", json={
            "customer_id": test_customer["customer_id"],
            "currency": "EUR"
        }, headers=headers).json()
        acc2 = client.post("/accounts", json={
            "customer_id": test_customer["customer_id"],
            "currency": "EUR"
        }, headers=headers).json()
        
        client.post(f"/accounts/{acc1['account_id']}/deposit", json={
            "amount": 1000,
            "currency": "EUR"
        }, headers=headers)
        
        client.post("/transactions", json={
            "sender_account_id": acc1["account_id"],
            "receiver_account_id": acc2["account_id"],
            "amount": 500,
            "currency": "EUR"
        }, headers=headers)
        
        # List transactions for account
        response = client.get(f"/transactions/account/{acc1['account_id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0


# ============================================================
# Loan Tests
# ============================================================

class TestLoans:
    
    def test_create_loan(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post("/loans", json={
            "customer_id": test_customer["customer_id"],
            "principal": 10000,
            "remaining_debt": 10000,
            "currency": "EUR",
            "rate_percentage": 5.5
        }, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert float(data["principal"]) == 10000
        assert data["status"] == "active"

    def test_create_loan_without_token(self, test_customer):
        """Test that creating loan without token returns 401."""
        response = client.post("/loans", json={
            "customer_id": test_customer["customer_id"],
            "principal": 10000,
            "remaining_debt": 10000,
            "currency": "EUR",
            "rate_percentage": 5.5
        })
        assert response.status_code == 401

    def test_get_loan(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        # Create loan
        loan = client.post("/loans", json={
            "customer_id": test_customer["customer_id"],
            "principal": 10000,
            "remaining_debt": 10000,
            "currency": "EUR",
            "rate_percentage": 5.5
        }, headers=headers).json()
        
        # Get loan
        response = client.get(f"/loans/{loan['loan_id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["loan_id"] == loan["loan_id"]

    def test_list_loans_for_customer(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        client.post("/loans", json={
            "customer_id": test_customer["customer_id"],
            "principal": 10000,
            "remaining_debt": 10000,
            "currency": "EUR",
            "rate_percentage": 5.5
        }, headers=headers)
        
        response = client.get(f"/loans/customer/{test_customer['customer_id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_make_loan_payment(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        # Create loan
        loan = client.post("/loans", json={
            "customer_id": test_customer["customer_id"],
            "principal": 10000,
            "remaining_debt": 10000,
            "currency": "EUR",
            "rate_percentage": 5.5
        }, headers=headers).json()
        
        # Make payment
        response = client.post(f"/loans/{loan['loan_id']}/payment", json={
            "amount": 2000
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert float(data["remaining_debt"]) == 8000

    def test_make_loan_payment_full(self, test_user, test_customer):
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        # Create loan
        loan = client.post("/loans", json={
            "customer_id": test_customer["customer_id"],
            "principal": 10000,
            "remaining_debt": 10000,
            "currency": "EUR",
            "rate_percentage": 5.5
        }, headers=headers).json()
        
        # Pay off full debt
        response = client.post(f"/loans/{loan['loan_id']}/payment", json={
            "amount": 10000
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert float(data["remaining_debt"]) == 0
        assert data["status"] == "closed"
