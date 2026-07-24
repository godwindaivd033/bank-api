from sqlmodel import SQLModel
from datetime import datetime
from pydantic import EmailStr


#---Creating the schema that reads the user profile---

class UserProfileRead(SQLModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    created_at: datetime


#---Creating the schema that enables user to update the profile---
class UserProfileUpdate(SQLModel):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


#---Creating the schema that enables the user to change password---
class ChangePassword(SQLModel):
    current_password: str
    new_password: str
    confirm_password: str