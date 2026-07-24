from decimal import Decimal
from sqlmodel import SQLModel
from app.models.transaction import TransactionRead

class DashboardRead(SQLModel, table=False):
    account_holder_name: str
    account_number: str
    account_type: str

    current_balance: Decimal

    beneficiary_count: int
    transaction_count: int

    recent_transactions: list[TransactionRead]