#---Building the user main model and schema models---
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, UTC
from pydantic import EmailStr

#---Creating the main user model---
class User(SQLModel, table= True):
    id: Optional[int]= Field(default= None, primary_key= True)
    first_name: str
    last_name: str
    email: EmailStr= Field(index= True, unique= True)
    password: str
    phone_number: str
    role: str= Field(default= "customer")
    is_active: bool= Field(default= True)
    created_at: datetime= Field(default_factory=lambda: datetime.now(UTC))




#---Creating the schema model that allows user to update their data in the database
class UserUpdate(SQLModel, table= False):
    first_name: Optional[str]= None
    last_name: Optional[str]= None
    email: Optional[str]= None
    phone_number: Optional[str]= None




#---Creating the schema model that allows user to read the response data in the database---
class UserRead(SQLModel, table= False):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    role: str
    is_active: bool
    created_at: datetime



class UserCreate(SQLModel):
    first_name: str
    last_name: str
    email: str
    password: str
    phone_number: str


        
        
class UserSearch(SQLModel, table = False):       
    first_name: str | None = None,
    last_name: str | None = None,
    email: str| None = None,
    phone_number: str| None = None,
    from_date: datetime| None = None,
    to_date: datetime| None = None,
   