from fastapi import HTTPException
from app.services.logger import logger
from app.models.profile import UserProfileRead
from app.auth import verify_password













#---Helper: validate and apply profile update fields---
def apply_profile_update(user, profile_update):
    if (
        profile_update.first_name is None
        and profile_update.last_name is None
        and profile_update.phone_number is None
    ):
        logger.warning(f"No profile update data provided by user {user.id}.")
        raise HTTPException(
            status_code=400,
            detail="No update data provided"
        )

    if profile_update.first_name:
        user.first_name = profile_update.first_name

    if profile_update.last_name:
        user.last_name= profile_update.last_name 
                
    if profile_update.phone_number:
        user.phone_number= profile_update.phone_number

    return user


#---Helper: convert a User into a UserProfileRead---
def serialize_user_profile(user):
    return UserProfileRead(id= user.id,
    first_name= user.first_name,
    last_name= user.last_name,
    email= user.email,
    phone_number= user.phone_number,
    created_at= user.created_at)



#---Helper: validate a password update request---
def validate_password_update(password_update, user):
    #---Ensuring the current password was provided---
    if not password_update.current_password:
        logger.warning(f"Current password not provided by user {user.id}.")
        raise HTTPException(
            status_code=400,
            detail="Current password is required"
        )

    #---Verifying that the current password is correct---
    if not verify_password(password_update.current_password, user.password):
        logger.warning(f"Incorrect current password provided by user {user.id}.")
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    #---Ensuring the new password was provided---
    if not password_update.new_password:
        logger.warning(f"New password not provided by user {user.id}.")
        raise HTTPException(
            status_code=400,
            detail="New password is required"
        )

    #---Ensuring confirm password was provided---
    if not password_update.confirm_password:
        logger.warning(f"Confirm password not provided by user {user.id}.")
        raise HTTPException(
            status_code=400,
            detail="Confirm password is required"
        )

    #---Ensuring both passwords match---
    if password_update.new_password != password_update.confirm_password:
        logger.warning(f"Password confirmation mismatch for user {user.id}.")
        raise HTTPException(
            status_code=400,
            detail="New password and confirm password do not match"
        )

    #---Ensuring the new password is different from the current password---
    if verify_password(password_update.new_password, user.password):
        logger.warning(f"User {user.id} attempted to reuse the current password.")
        raise HTTPException(
            status_code=400,
            detail="New password must be different from the current password"
        )