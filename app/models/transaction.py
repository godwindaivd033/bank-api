#---Building the main model and schema models for the transactions---
from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, UTC
from app.models.enums import TransactionType, TransactionStatus


#---Creating the main transaction model---
class Transaction(SQLModel, table= True):
    id: Optional[int]= Field(default= None, primary_key= True)
    account_id: int= Field(foreign_key= "account.id")
    reference: str
    amount: Decimal
    transaction_type: TransactionType
    transaction_status: TransactionStatus
    reversal_transaction_id: int | None = Field( default=None, foreign_key="transaction.id")
    description: str
    balance_before: Decimal
    balance_after: Decimal
    created_at: datetime= Field(default_factory= lambda: datetime.now(UTC))



#---Creating the schema model that aids user to read the data in the database---
class TransactionRead(SQLModel, table= False):
    id: int
    account_id: int
    reference: str
    amount: Decimal
    transaction_type: TransactionType
    transaction_status: TransactionStatus
    description: str
    balance_before: Decimal
    balance_after: Decimal
    created_at: datetime


#---Creating the schema model that aids in creating transaction---
class TransactionCreate(SQLModel, table= False):
    account_id: int
    amount: Decimal
    description: Optional[str]= None


#---Schema that aids in transferring money---
class TransferCreate(SQLModel, table=False):
    from_account_id: int
    to_account_number: str
    amount: Decimal
    description: Optional[str] = None
    
class TransactionSearch(SQLModel, table=False):
    reference: str | None = None
    account_number: str | None = None
    transaction_type: TransactionType | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
   



#---Creating the schema for statement of account---
class StatementSummary(SQLModel, table=False):
    account_holder_name: str
    account_number: str
    account_type: str

    from_date: datetime
    to_date: datetime

    opening_balance: Decimal
    closing_balance: Decimal

    total_deposits: Decimal
    total_withdrawals: Decimal
    total_transfer_in: Decimal
    total_transfer_out: Decimal

    transactions: list[TransactionRead]

class StatementSearch(SQLModel, table= False):
    from_date: datetime | None = None
    to_date: datetime | None = None



