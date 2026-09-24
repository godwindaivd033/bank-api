from sqlmodel import Session
from app.models.transaction import StatementSearch, StatementSummary, TransferCreate, TransactionCreate, TransactionRead
from app.auth import get_user_with_role
from app.database import get_session
from fastapi import APIRouter, Query, Depends, HTTPException
from app.services.transaction_service import deposit_helper_function, withdrawal_helper_function, make_transfer, get_transactions_for_statement,fetch_transaction_history, get_account_or_404, fetch_reference, validate_date_range, calculate_statement_totals,get_authenticated_user_or_404
from app.services.logger import logger
from app.routers.websocket import manager
from fastapi.concurrency import run_in_threadpool
import json
from app.redis_client import redis_client
from fastapi import Header
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Annotated
from app.services.idempotency_service import check_idempotency_key, save_idempotency_key


#---Configuring the router---
router= APIRouter(prefix= "/transaction", tags= ["transactions"])




#---Creating the endpoint that helps to create a transaction request---
@router.post("/deposit", response_model= TransactionRead, status_code= 201)
async def create_deposit_transactions(transaction_create: TransactionCreate, idempotency_key: Annotated[str, Header(description= "Unique key to prevent duplicate deposit")], session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):


    #---Confirming that transaction isn't a duplicate---
    existing=await run_in_threadpool(check_idempotency_key, session, idempotency_key, "/deposit")

    if existing:
        logger.info(f"Idempotency key {idempotency_key} has already been used, returning saved result")
        return JSONResponse(content= json.load(existing.response_body), status_code= existing.status_code)

    logger.info("Deposit transaction requested.")
    #---Getting the user---
    user= await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    transaction_receipt= await run_in_threadpool (deposit_helper_function, session, transaction_create, active_user)

    response_data= jsonable_encoder(TransactionRead.model_validate(transaction_receipt))

    #---Adding the idempotency data---
    logger.info("Saving idempotency data")
    save_idempotency_key(session, idempotency_key, "/deposit", response_data, 201)

    session.add(transaction_receipt)
    session.commit()
    session.refresh(transaction_receipt)

    logger.info(f"Deposit transaction {transaction_receipt.reference} created successfully.")

    #---Notifying the user through websocket---
    await manager.send_to_user(user.id,
                               f"Deposit of {transaction_receipt.amount} was made"
                               f" New balance: {transaction_receipt.balance_after}")
    return transaction_receipt    


@router.post("/withdraw", response_model=TransactionRead, status_code=201)
async def create_withdrawal_transaction(
    transaction: TransactionCreate,
    idempotency_key: Annotated[str, Header(description= "Unique key to prevent duplicate deposit")],
    session: Session = Depends(get_session),
    active_user: dict = Depends(get_user_with_role)
):


    #---Confirming that such transaction isn't occuring twice--
    existing= await run_in_threadpool(check_idempotency_key, session, idempotency_key, "/withdraw")

    #---If existing, return result---
    if existing:

        logger.info(f"Idempotency key{idempotency_key} has been used, returning saved result")
        return JSONResponse(content= json.load(existing.response_body), status_code= existing.status_code)
    
    logger.info("Withdrawal transaction requested.")
    #---Getting the authenticated user (need user.id for WebSocket notification)---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    transaction_receipt = await run_in_threadpool(
        withdrawal_helper_function,
        session,
        active_user,
        transaction
    )

    #---Configuring the response data---
    response_data= jsonable_encoder(TransactionRead.model_validate(transaction_receipt))

    #---Add idempotency detail---
    logger.info("Saving the idempotency data")
    save_idempotency_key(session, idempotency_key, "/withdraw", response_data, 201)

    # Add transaction to database
    session.add(transaction_receipt)
    session.commit()
    session.refresh(transaction_receipt)

    logger.info(
        f"Withdrawal transaction "
        f"{transaction_receipt.reference} created successfully."
    )

    #---Notify the user through WebSocket---
    await manager.send_to_user(
        user.id,
        f"Withdrawal of {transaction_receipt.amount} successful. "
        f"New balance: {transaction_receipt.balance_after}"
    )

    return transaction_receipt


#---Creating the endpoint that aids user in carrying out transfer---
@router.post("/transfer", response_model= TransactionRead, status_code= 201)
async def create_transfer(transfer_create: TransferCreate, idempotency_key: Annotated[str, Header(description="Unique key to prevent duplicate transfers")], session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    logger.info("Transfer transaction requested.")

    #---Confirming that specific transaction isnt occuring twice---
    existing= await run_in_threadpool(check_idempotency_key, session, idempotency_key, "/transfer", )


    #---If existing, terminate outgoing duplicated request and return response---
    if existing:
        logger.info(f"Idempotency key {idempotency_key} has already been used, returning saved result")

        return JSONResponse(content= json.load(existing.response_body), status_code= existing.status_code)

       # Getting the authenticated user (need user.id for WebSocket notification)
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)
    
    sender_receipt, receiver_receipt = await run_in_threadpool(make_transfer, transfer_create, session, active_user)
    
    #---Adding both transaction records---
    session.add(sender_receipt)
    session.add(receiver_receipt)

    #---Add the detail to the idempontency model for over time referencing---
    response_data= jsonable_encoder(TransactionRead.model_validate(sender_receipt))

    #---Save the idempotency details---
    save_idempotency_key(session, idempotency_key, "/transfer", response_data, 201)
    
    #---Saving everything together---
    session.commit()

    #---Refreshing newly created transactions---
    session.refresh(sender_receipt)
    session.refresh(receiver_receipt)

    logger.info(f"Transfer transaction {sender_receipt.reference} completed successfully.")

    #---Notify the user through websocket---
    await manager.send_to_user(user.id, 
                               f'Transfer of {sender_receipt.amount} sucessful. '
                               f'New balance: {sender_receipt.balance_after}')

    return sender_receipt




#---Creating the endpoint that aids users in getting statement of account---
@router.get("/statement", response_model= list[StatementSummary], status_code= 200)
async def get_statement_of_account(search: StatementSearch= Depends(), session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):
    
    logger.info("Statement of account requested.")

  #---Getting the authenticated user---
    user = await run_in_threadpool(get_authenticated_user_or_404, session, active_user)

    #---Getting the user account---
    account = await run_in_threadpool(get_account_or_404, session, user)

    starting_date= search.from_date
    ending_date= search.to_date

    #--Using the helper service to validate date range---
    validate_date_range(user, starting_date, ending_date)

   #---making the redis cache key---
    cache_key= f"statement: {account.id}" 

    #---Try grabbing data from the redis cache---
    logger.info(f"Querying the redis cache for {cache_key}") 

    try:
        cached= await run_in_threadpool(redis_client.get, cache_key)

        if cached:
            logger.info(f"Query for {cache_key} hit the redis cache")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis unavailable, falling back to database: {e}")
        cached= None

    #---If not, getting the transactions for the statement---
    logger.info(f"Query for {cache_key} miss redis, querying the database for request")
    transactions = await run_in_threadpool(
        get_transactions_for_statement, session, account.id, starting_date, ending_date
    )


    if not transactions:
        logger.warning(f"No transactions found for user {user.id} within the selected period.")
        raise HTTPException(status_code= 404, detail= " No transactions found for the selected period") 

    #---Preparing the calculations---
    total_deposit, total_withdrawal, total_transfer_in, total_transfer_out, transaction_read = calculate_statement_totals(transactions)

    #---Getting balances directly from transactions---
    opening_balance = transactions[0].balance_before

    closing_balance = transactions[-1].balance_after

    #---Building the statement---
    statement = StatementSummary(
        account_holder_name=f"{user.first_name} {user.last_name}",
        account_number=account.account_number,
        account_type=account.account_type,
        from_date=starting_date,
        to_date=ending_date,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        total_deposits=total_deposit,
        total_withdrawals=total_withdrawal,
        total_transfer_in=total_transfer_in,
        total_transfer_out=total_transfer_out,
        transactions=transaction_read
    )

    logger.info(f"Statement generated successfully for user {user.id}.")
    #---Invalidating the redis cache---
    statement_data= [statement.model_dump(mode= "json")]
    await run_in_threadpool(redis_client.set, cache_key, json.dumps(statement_data), ex=60)

    #---Notifying user through the websocket---
    await manager.send_to_user(user.id ,
                               "Your statement of account is ready, log in to your app to view it")
    return statement_data


#---Creating the endpoint that aids users in accessing their transaction history---
@router.get("/{account_id}/transactions", response_model= list[TransactionRead], status_code= 200)
async def get_transaction_history(account_id: int, skip: int= 0, limit: int= Query(default= 10, le= 100), session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    logger.info(f"Transaction history requested for account {account_id}.")

    
    return  await run_in_threadpool(fetch_transaction_history, account_id, skip, limit, session, active_user )




#---Creating the endpoint that gets one specific transaction---
@router.get("/{ref_id}", response_model= TransactionRead, status_code= 200)
async def get_transaction_references(ref_id: str, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    logger.info(f"Transaction lookup requested for reference {ref_id}.")

    return await run_in_threadpool(fetch_reference, ref_id, session, active_user)