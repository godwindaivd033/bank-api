#---Building the admin support endpoints---

from sqlmodel import Session, select
from fastapi import APIRouter, Query, HTTPException, Depends
from app.database import get_session
from app.auth import get_user_with_role
from app.models.transaction import TransactionRead, Transaction, TransactionSearch
from app.models.enums import   TransactionType
from app.models.account import AccountRead, Account
from app.models.user import  UserRead, UserSearch
from app.services.admin_service import validate_admin, search_transaction, make_deposit_reversal, get_transfer_transactions_or_400, freeze_the_account, apply_deposit_reversal, apply_transfer_reversal, apply_withdrawal_reversal, search_the_user, unfreeze_the_account
from app.services.logger import logger
from fastapi.concurrency import run_in_threadpool

#---Configuring the router---
router= APIRouter(prefix= "/admin", tags= ["admin"])




#---Creating the endpoint that enables the admin to get all the accounts---
@router.get("/accounts", response_model= list[AccountRead], status_code= 200)
async def get_all_accounts(skip: int= 0, limit: int= Query(default= 10, le= 100), session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    logger.info("Admin requested all accounts.")

    #---Confirming that the request is made by the admin---
    if active_user.get("role") != "Admin":
        logger.warning("Unauthorized attempt to retrieve all accounts.")
        raise HTTPException(status_code= 403, detail= "Forbidden request")
    
    #---Quering the database for all accounts---
    accounts= await run_in_threadpool(lambda :session.exec(select(Account).offset(skip).limit(limit)).all())

    logger.info(f"Retrieved {len(accounts)} account(s).")

    #---Returning the account  list---
    return accounts



#---Creating the endpoint that enables admin to get all transactions---
@router.get("/transactions", response_model= list[TransactionRead], status_code= 200)
async def get_all_transactions(skip: int= 0, limit: int= Query(default= 10, le= 100), session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    logger.info("Admin requested all transactions.")

    #---Verifying that the requester is an admin---
    validate_admin(active_user)

    #---Getting the transaction by querying the database---
    transactions= await run_in_threadpool(lambda :session.exec(select(Transaction).order_by(Transaction.created_at.desc()).offset(skip).limit(limit)).all())

    logger.info(f"Retrieved {len(transactions)} transaction(s).")

    return transactions





#---Creating the endpoint that enables the admin to search through the transaction---
@router.get("/transactions/search", response_model= list[TransactionRead], status_code= 200)
async def search_client_transaction_data(
    search: TransactionSearch = Depends(),
    skip: int = 0,
    limit: int = Query(default=10, le=100),
    session: Session = Depends(get_session),
    active_user: dict = Depends(get_user_with_role)):

    logger.info("Admin initiated transaction search.")

    #---Verifying that the user is been made by the admin---
    validate_admin(active_user)

    #---Querying through the database---
    transactions = await run_in_threadpool(search_transaction, session, search, skip, limit)

    logger.info(f"Transaction search returned {len(transactions)} result(s).")

    return transactions
    


#---Creating the endpoint that aids admins to reverse a transaction---
@router.post("/transactions/{reference}/reverse", response_model= TransactionRead, status_code= 200)
async def reverse_transaction(reference: str, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    logger.info(f"Transaction reversal requested for reference {reference}.")

    #---Verifying that the request is made by an admin---
    await run_in_threadpool(validate_admin, active_user)

    #---Finding the original transaction---
    transaction, reversal_transaction= await run_in_threadpool(make_deposit_reversal, session, reference)

    if reversal_transaction is not None:

        transaction, reversal_transaction =await run_in_threadpool(apply_deposit_reversal, session, transaction, reversal_transaction)

        session.commit()
        session.refresh(reversal_transaction)

        logger.info(f"Deposit transaction {reference} reversed successfully.")

        return reversal_transaction

    #---Checking if the transaction is a withdrawal---
    if transaction.transaction_type == TransactionType.WITHDRAWAL:

        transaction, transaction_receipt =await run_in_threadpool(apply_withdrawal_reversal, session, transaction)

        session.commit()
        session.refresh(transaction_receipt)

        logger.info(f"Withdrawal transaction {reference} reversed successfully.")

        return transaction_receipt

    #---Checking if transaction was a transfer---
    sender_transaction, receiver_transaction =await run_in_threadpool(get_transfer_transactions_or_400, session, reference)

    sender_reversal_receipt, receiver_reversal_receipt =await run_in_threadpool(apply_transfer_reversal, session, sender_transaction, receiver_transaction)

    session.commit()
    session.refresh(sender_reversal_receipt)
    session.refresh(receiver_reversal_receipt)

    logger.info(f"Transfer transaction {reference} reversed successfully.")

    return sender_reversal_receipt






#---Creating the endpoint that enables admin to freeze an account---
@router.patch("/accounts/{account_number}/freeze", response_model= AccountRead, status_code= 200)
async def freeze_accounts(account_number: str, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    logger.info(f"Freeze request received for account {account_number}.")

    #---Confirming ownership is from an admin---
    await run_in_threadpool(validate_admin, active_user)
    
    #---Querying the database to get the account---
    account = await run_in_threadpool(freeze_the_account, session, account_number)
   
    session.commit()
    session.refresh(account)

    logger.info(f"Account {account_number} frozen successfully.")

    return account




#---Creating the endpoint that enables admin to unfreeze an account---
@router.patch("/accounts/{account_number}/unfreeze", response_model= AccountRead, status_code= 200)
async def unfreeze_accounts(account_number: str, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    logger.info(f"Unfreeze request received for account {account_number}.")

    #---Confirming ownership is from an admin---
    await run_in_threadpool(validate_admin, active_user)
    
    account= await run_in_threadpool(unfreeze_the_account, session, account_number)
    
    session.commit()
    session.refresh(account)

    logger.info(f"Account {account_number} unfrozen successfully.")

    return account




#---Creating the endpoint that enables admin to search through Users---
@router.get("/users/search", response_model= list[UserRead], status_code= 200)
async def search_users(
    skip: int = 0,
    limit: int = Query(default=10, le=100),
    search: UserSearch = Depends(),
    session: Session = Depends(get_session),
    active_user: dict = Depends(get_user_with_role),
):
    logger.info("Admin initiated user search.")

    #---Ensuring that the request is made by admin---
    await run_in_threadpool(validate_admin, active_user)

    users = await run_in_threadpool(search_the_user, session, search, skip, limit)

    logger.info(f"User search returned {len(users)} result(s).")

    return users