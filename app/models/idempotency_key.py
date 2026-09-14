from sqlmodel import SQLModel, Field
from typing import Optional
from  datetime import datetime, UTC

class Idempotency_key(SQLModel, table= True):
    id: Optional[int]= Field(default= None, primary_key= True)
    key: str= Field(unique= True, index= True)
    status: str
    response_data: Optional[str] = None
    created_at: datetime= Field(default_factory= lambda: datetime.now(UTC))