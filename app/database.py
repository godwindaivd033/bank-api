#---Building the database---
from sqlmodel import SQLModel, Session, create_engine, select
from app.models.user import User
from app.auth import hash_password
import os




#---Getting the database link---
db_link= os.getenv("db_link")


#---Creating the engine---
engine= create_engine(db_link, echo= True)

#---Creating the database and the table---
def create_db_and_table():
    SQLModel.metadata.create_all(engine)

#---Creating the session---
def get_session():
    with Session(engine) as session:
        yield session



ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_ROLE = os.getenv("ADMIN_ROLE")


#---seeding the admin into the database---
def create_admin():
    with Session(engine) as session:
        existing_admin= session.exec(select(User).where(User.email== ADMIN_EMAIL)).first()
        if existing_admin:
            return
        admin= User(
        first_name= "Administrator",
        last_name= "one",
        email= ADMIN_EMAIL,
        password= hash_password(ADMIN_PASSWORD),
        phone_number= "+23470669865",
        role= ADMIN_ROLE,
        is_active= True)
        
        #--Handing it over to the database--
        session.add(admin)
        session.commit()
        session.refresh(admin)
                                     




        