#---Building the account endpoint---
from sqlmodel import Session, select
from fastapi import Depends, HTTPException
from fastapi import APIRouter
from app.auth import get_user_with_role
from app.models.account import Account, AccountCreate, AccountRead, AccountUpdate
from app.models.user import User
from app.database import get_session
from app.models.enums import AccountStatus
from app.services.logger import logger
from app.services.account_service import get_account_by_id_or_404, apply_account_update, get_authenticated_user_or_404, validate_account_closure, validate_no_duplicate_account_type, generate_account_number
from fastapi.concurrency import run_in_threadpool



#---Configuring the router---
router= APIRouter(prefix= "/account", tags= ["accounts"])




#---Creating the endpoint that enables users to create an account---
@router.post("/", response_model=AccountRead, status_code=201)
async def create_account(user_create: AccountCreate, session: Session = Depends(get_session), active_user: dict = Depends(get_user_with_role)):

    #---Getting the authenticated user's email---
    email = active_user.get("sub")
    logger.info(f"Account creation requested by {email}.")

    #---Finding the logged in user---
    existing_user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---Checking if the user already has this account type---
    await run_in_threadpool(validate_no_duplicate_account_type, session, existing_user, user_create.account_type)


    #---Generating a unique account number---
    account_number = await run_in_threadpool(generate_account_number, session)

    #---Creating the account---
    account = Account(
        user_id=existing_user.id,
        account_number=account_number,
        account_type=user_create.account_type
    )

    session.add(account)
    session.commit()
    session.refresh(account)

    logger.info(f"Account {account.account_number} created for user {existing_user.id}.")

    return account




#---Creating the endpoint that gets the authenticated user account---
@router.get("/", response_model= list[AccountRead], status_code= 200)
async def get_user_account(session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):
    

   #---Extracting user's email using the access token---
    email= active_user.get("sub")
    logger.info(f"Fetching accounts for {email}.")

    #---Quering the User table using the email to known if the user exist---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---If the user exist then return the list of the accounts---
    accounts= await run_in_threadpool(lambda :session.exec(select(Account).where(Account.user_id == user.id)).all())

    logger.info(f"Retrieved {len(accounts)} account(s) for user {user.id}.")

    return accounts






#---Creating the endpoint that gets one specific user account---
@router.get("/{account_id}", response_model= AccountRead, status_code= 200)
async def get_specific_account(account_id: int, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):


#---Getting the logged-in user email using the access token---
    email= active_user.get("sub")
    logger.info(f"Fetching account {account_id} for {email}.")

    #---Querying the database to confirm the logged-in user still exist---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---Verifying that there is an account in the database that belongs to this user---
    account = await run_in_threadpool(get_account_by_id_or_404, session, account_id, user, active_user)

    #---If the conditions were met, returnng the account requested---
    logger.info(f"Account {account_id} retrieved successfully.")

    return account




#---Creating the endpoint that allows user to update account---
@router.patch("/{account_id}", response_model= AccountRead, status_code= 200)
async def update_user_account(account_id: int, user_update: AccountUpdate, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #---Getting the logged in user by using the access token email---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---If the user exist, find the user account using the requested id---
    account = await run_in_threadpool(get_account_by_id_or_404, session, account_id, user, active_user)

    #---If confirmation was valid, ensure that the update was executed before proceeding---
    account = await run_in_threadpool(apply_account_update, session, account, user_update, account_id)

    return account





#---Creating the endpoint that allows user to update account---
@router.patch("/{account_id}", response_model= AccountRead, status_code= 200)
async def update_user_account(account_id: int, user_update: AccountUpdate, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

   #---Getting the logged in user by using the access token email---
    email= active_user.get("sub")
    logger.info(f"Account update requested by {email}.")

    #---Querying the database to confirm the user still exist in the database---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---If the user exist, find the user account using the requested id---
    account = await run_in_threadpool(get_account_by_id_or_404, session, account_id, user, active_user)

    #---If confirmation was valid, ensure that the update was executed before proceeding---
    account = await run_in_threadpool(apply_account_update, session, account, user_update, account_id)

    return account




#---Creating the endpoint that aids in the closing of the user's account(s)---
@router.patch("/{account_id}/close", response_model= AccountRead, status_code= 200)
async def close_user_account(account_id: int, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #---Getting the user email by using the access token---
    email= active_user.get("sub")
    logger.info(f"Account closure requested by {email}.")

    #---Quering the database to ensure that the user exist in the database---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---If the user exist, get the  user account using the requested id---
    account = await run_in_threadpool(get_account_by_id_or_404, session, account_id, user, active_user)

    #---Verifying the account can be closed---
    await run_in_threadpool(validate_account_closure, account, account_id)

    #---ELSE---
    account.status= AccountStatus.CLOSED

    session.commit()
    session.refresh(account)

    logger.info(f"Account {account_id} closed successfully.")

    return account