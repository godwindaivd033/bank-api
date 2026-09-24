from sqlmodel import SQLModel, Field
from typing import Optional
from  datetime import datetime, UTC

class IdempotencyKey(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    endpoint: str
    response_body: str  # store the JSON result as text
    status_code: int
    created_at: datetime = Field(default_factory= lambda: datetime.now(UTC))