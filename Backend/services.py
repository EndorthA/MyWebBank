# Backend/services.py
"""
Service layer - higher-level business logic that may coordinate multiple CRUD operations.
This demonstrates the business logic layer that sits between routers and CRUD operations.
"""

from decimal import Decimal
from sqlalchemy.orm import Session

from . import models, crud, schemas
from .crud import NotFoundError, BadRequestError, AuthError


class CustomerService:
    """Service for customer-related business logic."""
    
    @staticmethod
    def create_customer_with_user(
        db: Session,
        customer_data: schemas.CustomerCreate,
        user_data: schemas.UserCreate,
    ) -> tuple:
        """
        Create a customer and associated user in a single transaction.
        
        Args:
            db: Database session
            customer_data: Customer information
            user_data: User authentication information
        
        Returns:
            Tuple of (customer, user)
        
        Raises:
            BadRequestError: If email already exists or customer creation fails
        """
        try:
            # Create customer first
            customer = crud.create_customer(db, customer_data)
            
            # Set customer ID in user data
            user_data.customer_id = customer.customer_id
            
            # Create user
            user = crud.create_user(db, user_data)
            
            return (customer, user)
        except Exception as e:
            db.rollback()
            raise BadRequestError(f"Failed to create customer and user: {str(e)}")


class AccountService:
    """Service for account-related business logic."""
    
    @staticmethod
    def transfer_money(
        db: Session,
        sender_account_id: int,
        receiver_account_id: int,
        amount: Decimal,
        currency: str,
        comment: str = None,
    ) -> models.Transaction:
        """
        Execute a money transfer with validation.
        
        Args:
            db: Database session
            sender_account_id: ID of sending account
            receiver_account_id: ID of receiving account
            amount: Amount to transfer
            currency: Currency code (e.g., "EUR")
            comment: Optional transaction comment
        
        Returns:
            Created Transaction object
        
        Raises:
            BadRequestError: If validation fails
            NotFoundError: If accounts don't exist
        """
        # Create transaction (which handles balance updates)
        tx_data = schemas.TransactionCreate(
            sender_account_id=sender_account_id,
            receiver_account_id=receiver_account_id,
            amount=amount,
            currency=currency,
            comment=comment,
            is_recurring=False,
        )
        
        return crud.create_transaction(db, tx_data)
    
    @staticmethod
    def get_account_balance(db: Session, account_id: int) -> Decimal:
        """Get current account balance."""
        account = crud.get_account(db, account_id)
        if not account:
            raise NotFoundError("Account not found")
        return account.balance
    
    @staticmethod
    def get_account_summary(db: Session, account_id: int) -> dict:
        """
        Get comprehensive account summary including balance, transactions, and status.
        
        Returns:
            Dictionary with account details and related data
        """
        account = crud.get_account(db, account_id)
        if not account:
            raise NotFoundError("Account not found")
        
        transactions = crud.list_transactions_for_account(db, account_id)
        
        return {
            "account_id": account.account_id,
            "customer_id": account.customer_id,
            "currency": account.currency,
            "balance": account.balance,
            "status": account.status,
            "card_nr": account.card_nr,
            "created_at": account.created_at,
            "transaction_count": len(transactions),
            "recent_transactions": sorted(
                transactions,
                key=lambda t: t.created_at,
                reverse=True
            )[:10],  # Last 10 transactions
        }


class LoanService:
    """Service for loan-related business logic."""
    
    @staticmethod
    def create_loan_with_validation(
        db: Session,
        customer_id: int,
        principal: Decimal,
        currency: str,
        rate_percentage: Decimal,
    ) -> models.Loan:
        """
        Create a loan with business logic validation.
        
        Args:
            db: Database session
            customer_id: ID of borrowing customer
            principal: Loan amount
            currency: Currency (e.g., "EUR")
            rate_percentage: Annual interest rate
        
        Returns:
            Created Loan object
        
        Raises:
            BadRequestError: If validation fails
            NotFoundError: If customer doesn't exist
        """
        # Validate customer exists
        customer = crud.get_customer(db, customer_id)
        if not customer:
            raise NotFoundError("Customer not found")
        
        # Validate loan amount
        if principal <= 0:
            raise BadRequestError("Loan amount must be positive")
        
        # Validate interest rate
        if rate_percentage < 0 or rate_percentage > 100:
            raise BadRequestError("Interest rate must be between 0 and 100")
        
        # Create loan
        loan_data = schemas.LoanCreate(
            customer_id=customer_id,
            principal=principal,
            remaining_debt=principal,
            currency=currency,
            rate_percentage=rate_percentage,
        )
        
        return crud.create_loan(db, loan_data)
    
    @staticmethod
    def get_loan_details(db: Session, loan_id: int) -> dict:
        """
        Get comprehensive loan details including remaining balance and payment info.
        
        Returns:
            Dictionary with loan information
        """
        loan = crud.get_loan(db, loan_id)
        if not loan:
            raise NotFoundError("Loan not found")
        
        # Calculate months remaining (assuming fixed rate, monthly payments)
        remaining_months = 60  # Example: 5-year loan
        
        return {
            "loan_id": loan.loan_id,
            "customer_id": loan.customer_id,
            "principal": loan.principal,
            "remaining_debt": loan.remaining_debt,
            "currency": loan.currency,
            "rate_percentage": loan.rate_percentage,
            "status": loan.status,
            "created_at": loan.created_at,
            "paid_amount": loan.principal - loan.remaining_debt,
            "percentage_paid": (
                ((loan.principal - loan.remaining_debt) / loan.principal * 100)
                if loan.principal > 0 else 0
            ),
            "estimated_remaining_months": remaining_months,
        }
    
    @staticmethod
    def make_payment(
        db: Session,
        loan_id: int,
        amount: Decimal,
    ) -> models.Loan:
        """Make a loan payment."""
        if amount <= 0:
            raise BadRequestError("Payment amount must be positive")
        
        loan = crud.get_loan(db, loan_id)
        if not loan:
            raise NotFoundError("Loan not found")
        
        if loan.status != models.LoanStatus.active.value:
            raise BadRequestError("Can only make payments on active loans")
        
        return crud.make_loan_payment(db, loan_id, amount)


class AdminService:
    """Service for admin-related business logic."""
    
    @staticmethod
    def get_system_statistics(db: Session) -> dict:
        """
        Get system-wide statistics (requires admin access).
        
        Returns:
            Dictionary with system statistics
        """
        from sqlalchemy import func
        
        # Count active customers
        active_customers = db.query(func.count(models.Customer.customer_id)).filter(
            models.Customer.is_deleted == False
        ).scalar()
        
        # Count total accounts
        total_accounts = db.query(func.count(models.Account.account_id)).scalar()
        
        # Total account balance
        total_balance = db.query(func.sum(models.Account.balance)).scalar() or Decimal(0)
        
        # Count transactions
        total_transactions = db.query(func.count(models.Transaction.transaction_id)).scalar()
        
        # Count active loans
        active_loans = db.query(func.count(models.Loan.loan_id)).filter(
            models.Loan.status == models.LoanStatus.active.value
        ).scalar()
        
        # Total outstanding debt
        total_debt = db.query(func.sum(models.Loan.remaining_debt)).scalar() or Decimal(0)
        
        return {
            "active_customers": active_customers,
            "total_accounts": total_accounts,
            "total_balance": float(total_balance),
            "total_transactions": total_transactions,
            "active_loans": active_loans,
            "outstanding_debt": float(total_debt),
        }
    
    @staticmethod
    def suspend_customer_accounts(db: Session, customer_id: int) -> int:
        """
        Suspend all accounts for a customer (for compliance/fraud reasons).
        
        Returns:
            Number of accounts suspended
        """
        accounts = crud.list_accounts_for_customer(db, customer_id)
        
        count = 0
        for account in accounts:
            if account.status != models.AccountStatus.closed.value:
                crud.update_account_status(
                    db,
                    account.account_id,
                    models.AccountStatus.frozen.value,
                )
                count += 1
        
        return count
