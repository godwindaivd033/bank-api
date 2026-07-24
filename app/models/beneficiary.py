from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, UTC



class Beneficiary(SQLModel, table=True):
  

    id:Optional[int] = Field(default=None, primary_key=True)

    # The account that owns this beneficiary
    owner_account_id: int = Field(foreign_key="account.id")

    # The saved beneficiary account
    beneficiary_account_id: int = Field(foreign_key="account.id")

    # Optional custom name
    nickname: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))



class BeneficiaryCreate(SQLModel, table= False):
    beneficiary_account_number: str

    nickname: Optional[str] = None


class BeneficiaryRead(SQLModel, table= False):
    id: int
    account_number: str

    account_name: str

    nickname: Optional[str] = None
    
    created_at: datetime


class BeneficiaryUpdate(SQLModel, table= False):
    nickname: Optional[str] = None




class BeneficiarySearch(SQLModel, table= False):
    account_number: Optional[str] = None

    nickname: Optional[str]= None

  