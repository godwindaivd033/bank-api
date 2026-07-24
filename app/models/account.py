#---Creating the main and schema model for the account---
from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, UTC
from app.models.enums import AccountStatus


#---Creating the main model---
class Account(SQLModel, table= True):
    id: Optional[int]= Field(default= None, primary_key= True)
    user_id: int= Field(foreign_key= "user.id")
    account_number: str= Field(index= True, unique= True)
    account_type: str
    balance: Decimal = Field(default=Decimal("0.00"))
    status: AccountStatus= Field(default= AccountStatus.ACTIVE)
    created_at: datetime= Field(default_factory= lambda: datetime.now(UTC))



#---Creating the schema that aids in getting the data in the database---
class AccountRead(SQLModel, table= False):
    id:int
    user_id: int
    account_number: str
    account_type: str
    balance: Decimal
    status: str
    created_at: datetime



#---Creating the schema that aids in creating an account---
class AccountCreate(SQLModel, table= False):
    account_type: str






#---Creating the schema that aids in updating the data in the database---
class AccountUpdate(SQLModel, table= False):
    account_type: Optional[str]= None
    





