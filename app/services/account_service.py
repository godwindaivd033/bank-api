from fastapi import HTTPException
from app.services.logger import logger
from app.models.account import Account, AccountStatus
from app.models.user import User
from sqlmodel import Session, select
import secrets





#---Creating the helper method that generates a unique account number---
def generate_account_number(session: Session) -> str:
    while True:
        account_numbers = "66" + "".join(str(secrets.randbelow(10)) 
                                for _ in range(8)
                                ) 
    
        existing= session.exec(select(Account).where(Account.account_number == account_numbers)).first()
        if not existing:
            return account_numbers





#---Helper: get the authenticated user from the access token, or raise---
def get_authenticated_user_or_404(session, active_user):
    email= active_user.get("sub")

    user= session.exec(select(User).where(User.email == email)).first()

    if not user:
        logger.warning(f"User not found: {email}.")
        raise HTTPException(status_code= 404, detail= "User not found")

    return user




#---Helper: get an account by id, verifying ownership (or admin)---
def get_account_by_id_or_404(session, account_id, user, active_user):
    account= session.get(Account, account_id)

    #---If the account is not found, raise an alarm---
    if not account:
        logger.warning(f"Account {account_id} not found.")
        raise HTTPException(status_code= 404, detail= "User account not found")

    #---If the account was found, confirming the ownnership first before proceeding with the request---
    if account.user_id != user.id and active_user.get("role") != "Admin":
        logger.warning(f"Unauthorized update attempt on account {account_id} by user {user.id}.")
        raise HTTPException(status_code= 403, detail= "Forbidden request")

    return account


#---Helper: apply an update to an account if any fields were provided---
def apply_account_update(session, account, user_update, account_id):
    updating_user= user_update.model_dump(exclude_unset= True)

    if updating_user:
        account.sqlmodel_update(updating_user)

        session.commit()
        session.refresh(account)

        logger.info(f"Account {account_id} updated successfully.")

    return account


#---Helper: raise if the user already has an account of this type---
def validate_no_duplicate_account_type(session, user, account_type):
    existing_account = session.exec(select(Account).where(Account.user_id == user.id, Account.account_type == account_type)).first()

    if existing_account:
        logger.warning(f"User {user.id} already has a {account_type} account.")
        raise HTTPException(status_code=400, detail=f"You already have a {account_type} account.")



#---Helper: validate that an account is eligible to be closed---
def validate_account_closure(account, account_id):
    #---Verifying that the balance in the account is empty---
    if account.balance > 0:
        logger.warning(f"Account {account_id} has a non-zero balance.")
        raise HTTPException(status_code= 400, detail= "Account balance must be zero before closing")

    if account.status == AccountStatus.CLOSED:
        logger.warning(f"Account {account_id} is already closed.")
        raise HTTPException(
            status_code=400,
            detail="Account is already closed."
        )