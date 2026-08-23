from sqlmodel import Session
from fastapi import  APIRouter, Depends, Request
from app.auth import get_user_with_role,  hash_password
from app.database import get_session
from app.models.profile import UserProfileRead, UserProfileUpdate, ChangePassword
from app.services.beneficiary_service import get_authenticated_user
from app.services.logger import logger
from app.services.profile_services import apply_profile_update, serialize_user_profile, validate_password_update
from  fastapi.concurrency import run_in_threadpool
from app.main import limiter





#---Configuring the router---
router= APIRouter(prefix= "/profile", tags= ["profile"])

#---Creating the endpoint that enables user to get their profile---
@router.get("/", response_model= UserProfileRead, status_code= 200)
@limiter.limit("20/minute")
async def get_profile(session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #---Authenticating the user---
    user= await run_in_threadpool(get_authenticated_user,session, active_user)
    logger.info(f"Profile requested by user {user.id}.")
   
    #---Getting and returning the user's profile---

    profile= UserProfileRead(id= user.id,
    first_name= user.first_name,
    last_name= user.last_name,
    email= user.email,
    phone_number= user.phone_number,
    created_at= user.created_at)

    logger.info(f"Profile retrieved for user {user.id}.")

    return profile


#---Creating the endpoint that enables user to update their profile---
@router.patch("/update", response_model= UserProfileRead, status_code= 200)
@limiter.limit("7/minute")
async def update_profile(profile_update: UserProfileUpdate, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):
 
    #---Authenticating the user---
    user= await run_in_threadpool(get_authenticated_user,session, active_user)
    logger.info(f"Profile update requested by user {user.id}.")
    
    #---Validating changes were made and commiting changes---
 

    #---Validating changes were made and commiting changes---
    user = apply_profile_update(user, profile_update)

    session.commit()
    session.refresh(user)

    logger.info(f"Profile updated successfully for user {user.id}.")

    #---Getting and returning the latest update on the profile---
    profile = serialize_user_profile(user)

    return profile


#---Creating the endpoint that enables a user to update password---
@router.patch("/update_password", status_code=200)
@limiter.limit("3/minute")
async def change_password(
    password_update: ChangePassword,
    session: Session = Depends(get_session),
    active_user: dict = Depends(get_user_with_role),
):

    #---Authenticating the user---
    user = await run_in_threadpool(get_authenticated_user, session, active_user)
    logger.info(f"Password change requested by user {user.id}.")

    validate_password_update(password_update, user)

    #---Hashing the new password---
    hashed_password = hash_password(password_update.new_password)

    #---Updating the user's password---
    user.password = hashed_password

    #---Saving the changes---
    session.commit()

    #---Refreshing the user object---
    session.refresh(user)

    logger.info(f"Password updated successfully for user {user.id}.")

    return {
        "message": "Password updated successfully"
    }