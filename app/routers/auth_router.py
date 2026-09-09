from sqlmodel import Session, select
from app.auth import  hash_password, verify_password, create_access_token
from app.database import get_session
from fastapi import  Depends, HTTPException, APIRouter, Request
from app.main import limiter
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import User, UserRead, UserCreate
from fastapi.concurrency import run_in_threadpool
from app.redis_client import check_rate_limit



router = APIRouter(tags= ["authentication"])




#---Creating the endpoint that aids users to register---
@router.post("/register", response_model= UserRead, status_code= 201)
@limiter.limit("4/minute")
async def reg_user(request: Request, create_data: UserCreate, session: Session= Depends(get_session)):

        #---SlowAPI already checked IP-based limit before this function body even runs---

    #---Additional manual check: limit by the email being registered, not just IP---
    rate_limit_key = f"register_attempts:{create_data.email}"
    await run_in_threadpool(check_rate_limit, rate_limit_key, max_attempts=3, window_seconds=600)

    #---Confirming the user hasn't registered previously to prevent duplication---
    existing_user= await run_in_threadpool(lambda :session.exec(select(User).where(User.email== create_data.email)).first())

    #---Checking if the user data is still recorded in the database---
    if existing_user:
        raise HTTPException(status_code= 400, detail= "Email already exist")
    
    #---If not registered, hashing the password before commiting the data to the database---
    hashed_password= hash_password(create_data.password)

    #--Configuring the data and commit--
    user= User(first_name= create_data.first_name,
    last_name= create_data.last_name,
    email= create_data.email,
    password= hashed_password,
    phone_number= create_data.phone_number)


    session.add(user)
    session.commit()
    session.refresh(user)

    return user



#----Creating the endpoint that allows user to login---
@router.post("/login", status_code= 200)
async def login_user(user_data: OAuth2PasswordRequestForm= Depends(), session: Session= Depends(get_session)):

   
    #---Confirming the user exist in the database---
    user= await run_in_threadpool(lambda :session.exec(select(User).where(User.email == user_data.username)).first())
    if not user:
        raise HTTPException(status_code= 401, detail= "Invalid login credentials")
    
    #---If user, then verifying the user password--
    verify_pwd= verify_password(user_data.password, user.password)

    if not verify_pwd:
        raise HTTPException(status_code= 401, detail= "Invalid login credentials")
    
    
    #---Verifying that the user is active---
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    #---If verify_pwd, create access token--
    access_token = create_access_token(user.email, user.role)

    return {
        "access_token": access_token,
        "token_type": "bearer"}