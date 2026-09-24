#---Building the account endpoint---
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, Request
from app.auth import get_user_with_role
from app.models.account import Account, AccountCreate, AccountRead, AccountUpdate
from app.database import get_session
from app.models.enums import AccountStatus
from app.services.logger import logger
from app.services.account_service import get_account_by_id_or_404, apply_account_update, get_authenticated_user_or_404, validate_account_closure, validate_no_duplicate_account_type, generate_account_number
from fastapi.concurrency import run_in_threadpool
import json
from app.redis_client import redis_client
from app.limiter import limiter




#---Configuring the router---
router= APIRouter(prefix= "/account", tags= ["accounts"])




#---Creating the endpoint that enables users to create an account---
@router.post("/", response_model=AccountRead, status_code=201)
@limiter.limit("5/minute")
async def create_account(request: Request, user_create: AccountCreate, session: Session = Depends(get_session), active_user: dict = Depends(get_user_with_role)):

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
    try:
        await run_in_threadpool(redis_client.delete, f"accounts:{existing_user.id}")
    except Exception as e:
        logger.warning(f"Redis unavailable, could not invalidate cache: {e}")
    return account



#---Creating the endpoint that gets the authenticated user account---
@router.get("/", response_model=list[AccountRead], status_code=200)
@limiter.limit("10/minute")
async def get_user_account(request: Request, session: Session = Depends(get_session), active_user: dict = Depends(get_user_with_role)):

    #---Extracting user's email using the access token---
    email = active_user.get("sub")
    logger.info(f"Fetching accounts for {email}.")

    #---Quering the User table using the email to known if the user exist---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---Creating the cache key---
    cache_key = f"accounts:{user.id}"
    try:
        cached = await run_in_threadpool(redis_client.get, cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis unavailable, falling back to DB: {e}")
        cached = None

    #---If cache missed for cache_key, query the database---
    accounts = await run_in_threadpool(lambda: session.exec(select(Account).where(Account.user_id == user.id)).all())
    accounts_data = [AccountRead.model_validate(a).model_dump(mode="json") for a in accounts]
    await run_in_threadpool(redis_client.set, cache_key, json.dumps(accounts_data), ex=60)

    logger.info(f"Retrieved {len(accounts)} account(s) for user {user.id}.")

    return accounts_data


#---Creating the endpoint that gets one specific user account---
@router.get("/{account_id}", response_model= AccountRead, status_code= 200)
@limiter.limit("20/minute")
async def get_specific_account(request:Request, account_id: int, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):


#---Getting the logged-in user email using the access token---
    email= active_user.get("sub")
    logger.info(f"Fetching account {account_id} for {email}.")

    #---Querying the database to confirm the logged-in user still exist---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---Creating the cache_key---
    cache_key = f"account:{account_id}:user:{user.id}"
    try:
        cached = await run_in_threadpool(redis_client.get, cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis unavailable, falling back to DB: {e}")
        cached = None
    
    #---If request missed, query the database---
    logger.info(f'Cache miss for {cache_key}, querying the database')
    account = await run_in_threadpool(get_account_by_id_or_404, session, account_id, user, active_user)

    account_data= AccountRead.model_validate(account).model_dump(mode="json")
    await run_in_threadpool(redis_client.set, cache_key, json.dumps(account_data), ex= 60)

    #---If the conditions were met, returnng the account requested---
    logger.info(f"Account {account_id} retrieved successfully.")

    return account_data




#---Creating the endpoint that allows user to update account---
@router.patch("/{account_id}", response_model= AccountRead, status_code= 200)
@limiter.limit("7/minute")
async def update_user_account(request: Request, account_id: int, user_update: AccountUpdate, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #---Getting the logged in user by using the access token email---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---If the user exist, find the user account using the requested id---
    account = await run_in_threadpool(get_account_by_id_or_404, session, account_id, user, active_user)

    #---If confirmation was valid, ensure that the update was executed before proceeding---
    account = await run_in_threadpool(apply_account_update, session, account, user_update, account_id)
    try:
        await run_in_threadpool(redis_client.delete,f"account:{account_id}:user:{user.id}")
        await run_in_threadpool(redis_client.delete, f"account:{user.id}")
    except Exception as e:
        logger.warning(f"Redis unavailable, could not invalidate cache: {e}")
        
    
    return account



#---Creating the endpoint that aids in the closing of the user's account---
@router.patch("/{account_id}/close", response_model= AccountRead, status_code= 200)
@limiter.limit("7/minute")
async def close_user_account(request: Request, account_id: int, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

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
    try:
        await run_in_threadpool(redis_client.delete,f"account:{account_id}:user:{user.id}")
        await run_in_threadpool(redis_client.delete, f"account:{user.id}")
    except Exception as e:
        logger.warning(f"Redis is unavailable, could not invalidate cache: {e}")
    logger.info("redis client data has been cleaned up.")
    return account