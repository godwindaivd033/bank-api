#---Creating the helper function for my transaction endpoint----
from fastapi import HTTPException
from sqlmodel import  Session, select
from app.models.account import Account
from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus, TransactionType, TransactionCreate, TransferCreate, TransactionRead
from app.models.enums import AccountStatus, TransactionReferencePrefix
from app.utilies.ref_generator import generate_reference
from app.services.logger import logger
from decimal import Decimal
import json
from app.redis_client import redis_client

def get_transactions_for_statement(session: Session, account_id: int, starting_date, ending_date) -> list[Transaction]:
    return session.exec(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.created_at >= starting_date,
            Transaction.created_at <= ending_date
        ).order_by(Transaction.created_at.desc())
    ).all()






def validate_transaction_request(session: Session, active_user: dict, transaction_create: TransactionCreate) -> Account:
    email= active_user.get("sub")
    logger.info(f"Validating transaction request for {email}.")

    #---Querying the database to ensure that the user data exist in the database---
    user= session.exec(select(User).where(User.email == email)).first()

    if not user:
        logger.warning(f"User not found: {email}.")
        raise HTTPException(status_code= 404, detail= "User not found")
    
    #---Confirming that the user created an account that is stored in the database---
    account = session.get(Account, transaction_create.account_id)

    if not account:
        logger.warning(f"Account {transaction_create.account_id} not found.")
        raise HTTPException(status_code= 404, detail= "Account not found")
    
    #---Confirming that the request was made by the owner of the account or an admin---
    if account.user_id != user.id and active_user.get("role") != "Admin":
        logger.warning(f"Unauthorized transaction attempt on account {account.id} by user {user.id}.")
        raise HTTPException(status_code= 403, detail= "Forbidden request.")
    
    #---Checking the account status to see if it is closed---
    if account.status == AccountStatus.CLOSED:
        logger.warning(f"Transaction attempted on closed account {account.id}.")
        raise HTTPException(status_code= 400, detail= "Cannot deposit into a closed account.")
    
    #---Validating the amount that will to be transacted---
    if transaction_create.amount <= 0:
        logger.warning(f"Invalid transaction amount: {transaction_create.amount}.")
        raise HTTPException(status_code= 400, detail= "Amount has to be greater than zero")

    logger.info(f"Transaction validation successful for account {account.id}.")
    
    return account
    






#---Creating the helper function for deposit---
def deposit_helper_function(session: Session, transaction_create: TransactionCreate, active_user: dict) -> Transaction:
   
    account = validate_transaction_request(session, active_user, transaction_create)

    logger.info(f"Processing deposit into account {account.id}.")

    #---Getting the previous balance--
    balance_before= account.balance

    #---Getting the new balance---
    balance_after= balance_before + transaction_create.amount
     
    # Update the account balance (tracked automatically by the session)
    account.balance= balance_after

    #---Generating the transaction reference---
    transaction_ref= generate_reference(TransactionReferencePrefix.DEPOSIT.value)

    #---Creating the transaction reciept---
    transaction_receipt= Transaction(
        account_id= transaction_create.account_id,
        reference= transaction_ref,
        transaction_type=TransactionType.DEPOSIT,
        transaction_status = TransactionStatus.SUCCESS,
        amount= transaction_create.amount,
        description= transaction_create.description,
        balance_before= balance_before,
        balance_after= balance_after)

    logger.info(f"Deposit transaction {transaction_ref} created.")

    return transaction_receipt




#---Creating the helper function for withdrawal---

def withdrawal_helper_function(session: Session, active_user: dict, transaction: TransactionCreate) -> Transaction:

    account = validate_transaction_request(session, active_user, transaction)

    logger.info(f"Processing withdrawal from account {account.id}.")

    #---Verifying sufficient funds---
    if account.balance < transaction.amount:
        logger.warning(f"Insufficient funds in account {account.id}.")
        raise HTTPException(status_code= 400, detail= "Cannot proceed with transaction due to insufficient funds")
    
    #---Saving current balance---
    balance_before= account.balance

    balance_after= balance_before - transaction.amount

    #---Updating the account---
    account.balance= balance_after

    #---Generating the transaction references using the helper method---
    transaction_reference= generate_reference(TransactionReferencePrefix.WITHDRAWAL.value)

    #---Creating the transaction---
    transaction_receipt= Transaction(
        account_id= transaction.account_id,
        reference= transaction_reference,
        transaction_type=TransactionType.WITHDRAWAL,
        transaction_status = TransactionStatus.SUCCESS,
        amount= transaction.amount,
        description= transaction.description,
        balance_before= balance_before,
        balance_after= balance_after)

    logger.info(f"Withdrawal transaction {transaction_reference} created.")

    return transaction_receipt



def make_transfer(session: Session, active_user: dict, transfer_create: TransferCreate) -> tuple[Transaction, Transaction]:

    #---Extracting the logged-in user email from the access token---
    email= active_user.get("sub")
    logger.info(f"Transfer request initiated by {email}.")

    #---Querying the database to be sure the user data still exist in the database---
    user= session.exec(select(User).where(User.email == email)).first()

    if not user:
        logger.warning(f"User not found: {email}.")
        raise HTTPException(status_code= 404, detail= "User not found")
    
    #---Getting the user account---
    account= session.get(Account, transfer_create.from_account_id)

    if not account:
        logger.warning(f"Sender account {transfer_create.from_account_id} not found.")
        raise HTTPException(status_code= 404, detail= "Account not found")
    
    #---Verifying the ownership of the account---
    if account.user_id != user.id and active_user.get("role") != "Admin":
        logger.warning(f"Unauthorized transfer attempt on account {account.id} by user {user.id}.")
        raise HTTPException(status_code= 400, detail= "Forbidden request")
    

    #---Verifying the status of the account---
    if account.status == AccountStatus.CLOSED:
        logger.warning(f"Transfer attempted from closed account {account.id}.")
        raise HTTPException(status_code= 400, detail= "Cannot transfer from a closed account")
    

    #---Finding the receiver account using account number---
    receiver_account = session.exec(select(Account).where(Account.account_number == transfer_create.to_account_number)).first()

    if not receiver_account:
        logger.warning(f"Receiver account {transfer_create.to_account_number} not found.")
        raise HTTPException(status_code= 404, detail= "Reciever account not found")
    

     #---Prevent self transfer---
    if account.id == receiver_account.id:
        logger.warning(f"User {user.id} attempted a self-transfer.")
        raise HTTPException(status_code=400, detail="You cannot transfer money to the same account.")

    #---Checking receiver account status---
    if receiver_account.status == AccountStatus.CLOSED:
        logger.warning(f"Transfer attempted to closed account {receiver_account.id}.")
        raise HTTPException(status_code=400, detail="Cannot transfer money to a closed account")

    #---Validating amount---
    if transfer_create.amount <= 0:
        logger.warning(f"Invalid transfer amount: {transfer_create.amount}.")
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    #---Checking sufficient funds---
    if account.balance < transfer_create.amount:
        logger.warning(f"Insufficient funds in account {account.id}.")
        raise HTTPException(status_code=400, detail="Insufficient funds")

    #---Saving balances before transfer---
    sender_balance_before = account.balance
    receiver_balance_before = receiver_account.balance

    #---Calculating new balances---
    sender_new_balance = sender_balance_before - transfer_create.amount
    receiver_new_balance = receiver_balance_before + transfer_create.amount

    #---Updating both accounts---
    account.balance = sender_new_balance
    receiver_account.balance = receiver_new_balance

    #---Generating one transfer reference---
    reference = generate_reference(TransactionReferencePrefix.TRANSFER.value)

    #---Creating sender transaction---
    sender_receipt = Transaction(
        account_id = account.id,
        reference = reference,
        transaction_type = TransactionType.TRANSFER_OUT,
        transaction_status = TransactionStatus.SUCCESS,
        amount = transfer_create.amount,
        description = transfer_create.description,
        balance_before = sender_balance_before,
        balance_after = sender_new_balance,
    )

    #---Creating receiver transaction---
    receiver_receipt = Transaction(
        account_id = receiver_account.id,
        reference = reference,
        transaction_type = TransactionType.TRANSFER_IN,
        transaction_status = TransactionStatus.SUCCESS,
        amount = transfer_create.amount,
        description = transfer_create.description,
        balance_before = receiver_balance_before,
        balance_after = receiver_new_balance,
    )

    logger.info(f"Transfer {reference} completed successfully.")

    return sender_receipt, receiver_receipt




def get_authenticated_user(session: Session, active_user: dict):
    email= active_user.get("sub")

    logger.info(f"Authenticating user {email}.")

    user= session.exec(select(User).where(User.email == email)).first()

    if not user:
        logger.warning(f"User not found: {email}.")
        raise HTTPException(status_code= 404, detail= "User not found")

    logger.info(f"User {user.id} authenticated successfully.")

    return user



def fetch_transaction_history(session: Session, account_id: int, active_user: dict, skip: int, limit: int ) -> list[dict]:

    user = get_authenticated_user(session, active_user)

    logger.info(f"Fetching transaction history for account {account_id}.")
    
    #---Getting the user account---
    account= session.get(Account, account_id )
    
    if not account:
        logger.warning(f"Account {account_id} not found.")
        raise HTTPException(status_code=404, detail="Account not found")
    

    #---Verifying the account ownership, making sure the request was made by the right owner or admin---
    if account.user_id != user.id and active_user.get("role") != "Admin":
        logger.warning(f"Unauthorized access to transaction history for account {account_id} by user {user.id}.")
        raise HTTPException(status_code= 403, detail= "Forbidden request")

    #---Making the redis cache_key---
    cache_key= f"transactions:{account_id}:{skip}:{limit}"



    #---Getting the requested data from the redis_cache---
    cached= redis_client.get(cache_key)
    if cached:
      
        transaction_data= json.loads(cached)
      
        logger.info(f"Request{cache_key} HIT redis cache")
        return transaction_data

    logger.info(f"Request for {cache_key} miss, now querying the database")
    #---Getting the transaction---
    transactions= session.exec(
        select(Transaction)
        .where(Transaction.account_id == account.id)
        .order_by(Transaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    #---Converting the database objects to dictionaries--
    transaction_data= [r.model_dump(mode= "json") for r in transactions]

    #---Store in redis for 60 seconds---
    redis_client.set(cache_key, json.dumps(transaction_data), ex= 60)


    logger.info(f"Retrieved {len(transactions)} transaction(s) for account {account_id}.")

    return transaction_data


def fetch_reference(session: Session, active_user: dict, ref_id: str) -> dict:

    user = get_authenticated_user(session, active_user)
    logger.info(f"Fetching transaction reference {ref_id}.")

    cache_key = f"transaction:{ref_id}"
    cached = redis_client.get(cache_key)

    if cached:
        transaction_data = json.loads(cached)         
        if transaction_data["user_id"] != user.id and active_user.get("role") != "Admin":
            logger.warning(f"Unauthorized access to transaction {ref_id} by user {user.id}.")
            raise HTTPException(status_code= 403, detail= "Forbidden request")
        logger.info(f"Requested data for {cache_key} hit the redis cache")
        return transaction_data

    #---Cache MISS go to the database---
    transaction = session.exec(select(Transaction).where(Transaction.reference == ref_id)).first()

    if not transaction:
        logger.warning(f"Transaction {ref_id} not found.")
        raise HTTPException(status_code=404, detail="Transaction not found")

    account = session.get(Account, transaction.account_id)

    if not account:
        logger.warning(f"Account for transaction {ref_id} not found.")
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != user.id and active_user.get("role") != "Admin":
        logger.warning(f"Unauthorized access to transaction {ref_id} by user {user.id}.")
        raise HTTPException(status_code=403, detail="Forbidden request")

    transaction_data = TransactionRead.model_validate(transaction).model_dump(mode="json")   # <-- defined HERE, line 2
    transaction_data["user_id"] = account.user_id
    redis_client.set(cache_key, json.dumps(transaction_data), ex=3600)

    logger.info(f"Transaction {ref_id} retrieved successfully.")
    return transaction_data




#---Helper: get the authenticated user, or raise---
def get_authenticated_user_or_404(session, active_user):
    email= active_user.get("sub")

    user = session.exec(select(User).where(User.email == email)).first()

    if not user:
        logger.warning(f"User not found: {email}.")
        raise HTTPException(status_code= 404, detail= "User not found")

    return user


#---Helper: validate that the date range is not reversed---
def validate_date_range(user, starting_date, ending_date):
    if starting_date > ending_date:
        logger.warning(f"Invalid statement date range requested by user {user.id}.")
        raise HTTPException(status_code= 400, detail= "Wrong date request")


#---Helper: calculate totals by transaction type and build the TransactionRead list---
def calculate_statement_totals(transactions):
    total_deposit = Decimal("0")
    total_withdrawal=  Decimal("0")
    total_transfer_in= Decimal("0")
    total_transfer_out= Decimal("0")

    transaction_read = []

    for tx in transactions:

        if tx.transaction_type == TransactionType.DEPOSIT:
            total_deposit += tx.amount

        elif tx.transaction_type == TransactionType.WITHDRAWAL:
            total_withdrawal += tx.amount

        elif tx.transaction_type == TransactionType.TRANSFER_IN:
            total_transfer_in += tx.amount

        elif tx.transaction_type == TransactionType.TRANSFER_OUT:
            total_transfer_out += tx.amount

        transaction_read.append(
            TransactionRead(
                id=tx.id,
                account_id=tx.account_id,
                reference=tx.reference,
                amount=tx.amount,
                transaction_type=tx.transaction_type,
                transaction_status=tx.transaction_status,
                description=tx.description,
                balance_before=tx.balance_before,
                balance_after=tx.balance_after,
                created_at=tx.created_at
            )
        )

    return total_deposit, total_withdrawal, total_transfer_in, total_transfer_out, transaction_read



#---Helper: get the account belonging to the authenticated user, or raise---
def get_account_or_404(session, user):
    account = session.exec(select(Account).where(Account.user_id == user.id)).first()

    if not account:
        logger.warning(f"Account not found for user {user.id}.")
        raise HTTPException(status_code= 404, detail= "Account not found")

    return account