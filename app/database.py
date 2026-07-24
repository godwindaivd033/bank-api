#---Building the database---
from sqlmodel import SQLModel, Session, create_engine, select
from app.models.user import User
from app.auth import hash_password




#---Creating the database link---
db_link= "sqlite:///data.db"

#---Creating the engine---
engine= create_engine(db_link, echo= True)

#---Creating the database and the table---
def create_db_and_table():
    SQLModel.metadata.create_all(engine)

#---Creating the session---
def get_session():
    with Session(engine) as session:
        yield session



ADMIN_EMAIL = "admindave331@gmail.com"
ADMIN_PASSWORD = "strongdave1235"
ADMIN_ROLE = "Admin"


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
        role= "Admin",
        is_active= True)
        
        #--Handing it over to the database--
        session.add(admin)
        session.commit()
        session.refresh(admin)
                                     




        