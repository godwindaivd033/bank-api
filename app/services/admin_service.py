
from fastapi import HTTPException
from sqlmodel import  Session, select
from app.models.account import Account
from app.models.user import User,  UserSearch
from app.models.transaction import Transaction, TransactionStatus, TransactionType,  TransactionSearch
from app.models.enums import AccountStatus, TransactionReferencePrefix
from app.utilies.ref_generator import generate_reference
from app.services.logger import logger





def search_the_user(session: Session, search : UserSearch, skip: int, limit: int):
    query = select(User)

    if search.first_name:
        query = query.where(User.first_name.contains(search.first_name))

    if search.last_name:
        query = query.where(User.last_name.contains(search.last_name))

    if search.email:
        query = query.where(User.email == search.email)

    if search.phone_number:
        query = query.where(User.phone_number == search.phone_number)
    
    if search.from_date:
        query= query.where(User.created_at >= search.from_date)
    
    if search.to_date:
        query= query.where(User.created_at <= search.to_date)

    user_search= session.exec((query).offset(skip).limit(limit)).all()

    return user_search


#---Helper: reverse a deposit transaction---
def apply_deposit_reversal(session, transaction, reversal_transaction):
    session.add(reversal_transaction)

    #---Marking that the data base has been updated---
    transaction.transaction_status = TransactionStatus.REVERSED

    #---Temporarily saving it to the database---
    session.flush()

    transaction.reversal_transaction_id =  reversal_transaction.id

    return transaction, reversal_transaction


#---Helper: reverse a withdrawal transaction---
def apply_withdrawal_reversal(session, transaction):
    transaction, transaction_receipt= make_withdrawal_reversal(session, transaction)

    session.add(transaction_receipt)

    #---Marking the transaction status---
    transaction.transaction_status = TransactionStatus.REVERSED

    session.flush()

    #---Indicating where it was reversed from---
    transaction.reversal_transaction_id = transaction_receipt.id

    return transaction, transaction_receipt


#---Helper: find and validate the sender/receiver transactions for a transfer---
def get_transfer_transactions_or_400(session, reference):
    sender_transaction = None
    receiver_transaction = None

    transactions= session.exec(select(Transaction).where(Transaction.reference == reference)).all()

    if not transactions:
        logger.warning(f"No transaction found with reference {reference}.")
        raise HTTPException(status_code= 404, detail= "Tracking transaction failed")

    for tx in transactions:
        if tx.transaction_type == TransactionType.TRANSFER_OUT:
            sender_transaction = tx

        elif tx.transaction_type == TransactionType.TRANSFER_IN:
            receiver_transaction = tx

    #---If the transactions does not exist---      
    if not sender_transaction or not receiver_transaction:
        logger.warning(f"Incomplete transfer transaction for reference {reference}.")
        raise HTTPException(status_code= 400, detail= "Transfer transaction is incomplete")

    #---Checking if the sender transaction was reversed---
    if sender_transaction.transaction_status == TransactionStatus.REVERSED:
        logger.warning(f"Sender transaction for {reference} has already been reversed.")
        raise HTTPException(status_code=400, detail="Sender transaction has already been reversed.")

    #---Checking if the reciever transaction was reversed---
    if receiver_transaction.transaction_status == TransactionStatus.REVERSED:
        logger.warning(f"Receiver transaction for {reference} has already been reversed.")
        raise HTTPException(status_code=400, detail="Receiver transaction has already been reversed.")

    #---Confirming the transaction was successful at both ends---
    if sender_transaction.transaction_status != TransactionStatus.SUCCESS or receiver_transaction.transaction_status != TransactionStatus.SUCCESS:
        logger.warning(f"Attempted reversal of unsuccessful transfer {reference}.")
        raise HTTPException(status_code= 400, detail= "Cannot reverse an unsucessful transaction")

    return sender_transaction, receiver_transaction


#---Helper: reverse a transfer transaction---
def apply_transfer_reversal(session, sender_transaction, receiver_transaction):
    sender_reversal_receipt, receiver_reversal_receipt = make_transfer_reversal(session, sender_transaction, receiver_transaction)

    session.add(sender_reversal_receipt)
    session.add(receiver_reversal_receipt)

    sender_transaction.transaction_status = TransactionStatus.REVERSED
    receiver_transaction.transaction_status = TransactionStatus.REVERSED

    session.flush()

    receiver_transaction.reversal_transaction_id = receiver_reversal_receipt.id
    sender_transaction.reversal_transaction_id = sender_reversal_receipt.id

    return sender_reversal_receipt, receiver_reversal_receipt



























def search_transaction(session: Session, search: TransactionSearch, skip: int, limit: int) -> list[Transaction]:
    logger.info("Transaction search requested.")

    query = select(Transaction)

    #---Verifyiing that the admin provided a reference--
    if search.reference:
        query = query.where(Transaction.reference == search.reference)

    #---Verifying that the admin provided a transaction type---
    if search.transaction_type:
        query = query.where(Transaction.transaction_type == search.transaction_type)

    #---Verifying that the admin provided a minimum amount---
    if search.min_amount:
        query = query.where(Transaction.amount >= search.min_amount)

    #---Verifying that the admin provided a maximum amount---
    if search.max_amount:
        query = query.where(Transaction.amount <= search.max_amount)

    #---Verifying if the from date time was provided---
    if search.from_date:
        query = query.where(Transaction.created_at >= search.from_date)

    #---Verifying that the to date time was provided---
    if search.to_date:
        query = query.where(Transaction.created_at <= search.to_date)
    
    #--Getting the user account that has the account number submitted---
    if search.account_number:
        account = session.exec(
            select(Account).where(Account.account_number == search.account_number)
        ).first()

        if not account:
            logger.warning(f"Account {search.account_number} not found.")
            raise HTTPException(status_code=404, detail="Account not found")
        
        query = query.where(Transaction.account_id == account.id)

    transactions = session.exec(
        query.order_by(Transaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    logger.info(f"Found {len(transactions)} transaction(s).")

    return transactions


def validate_admin(active_user: dict):
    logger.info("Admin access validation.")

    if active_user.get("role") != "Admin":
        logger.warning("Unauthorized admin access attempt.")
        raise HTTPException(status_code=403, detail="Forbidden request")

    logger.info("Admin access granted.")

def make_deposit_reversal(session: Session, reference: str) -> tuple[Transaction, Transaction | None]:

    logger.info(f"Deposit reversal requested for reference {reference}.")

    transaction = session.exec(
        select(Transaction).where(Transaction.reference == reference)
    ).first()

    if not transaction:
        logger.warning(f"Transaction {reference} not found.")
        raise HTTPException(status_code=404, detail="Tracking transaction failed")

    #---Checking if the transaction has been reversed---
    if transaction.transaction_status == TransactionStatus.REVERSED:
        logger.warning(f"Transaction {reference} has already been reversed.")
        raise HTTPException(status_code=400, detail="Transaction has been reversed")

    if transaction.transaction_status != TransactionStatus.SUCCESS:
        logger.warning(f"Transaction {reference} is not eligible for reversal.")
        raise HTTPException(
            status_code=400,
            detail="Only successful transactions can be reversed."
        )

    #---Confirming the transaction type
    if transaction.transaction_type == TransactionType.DEPOSIT:

        account = session.get(Account, transaction.account_id)

        if not account:
            logger.warning(f"Account {transaction.account_id} not found.")
            raise HTTPException(
                status_code=404,
                detail="Account not found"
            )

        #---Verifying that there is enough balance to remove the deposit---
        if account.balance < transaction.amount:
            logger.warning(f"Insufficient balance to reverse deposit for account {account.id}.")
            raise HTTPException(
                status_code=400,
                detail="Cannot reverse deposit because the account has insufficient funds."
            )

        balance_before = account.balance
        balance_after = balance_before - transaction.amount

        #---Updating the balance---
        account.balance = balance_after

        reference_prefix = generate_reference(TransactionReferencePrefix.REVERSAL.value)

        #---Creating a reversal transaction---
        reversal_transaction = Transaction(
            account_id=account.id,
            reference=reference_prefix,
            transaction_type=TransactionType.DEPOSIT_REVERSAL,
            transaction_status=TransactionStatus.SUCCESS,
            amount=transaction.amount,
            description=f"Reversal of transaction {transaction.reference}",
            balance_before=balance_before,
            balance_after=balance_after
        )

        logger.info(f"Deposit reversal {reference_prefix} created successfully.")

        return transaction, reversal_transaction

    # if it's not a deposit, this helper has nothing to build
    return transaction, None


def make_withdrawal_reversal(session: Session, transaction: Transaction) -> tuple[Transaction, Transaction]:

    logger.info(f"Withdrawal reversal requested for transaction {transaction.reference}.")

    #---Getting the account_id---
    account = session.get(Account, transaction.account_id)

    if not account:
        logger.warning(f"Account {transaction.account_id} not found.")
        raise HTTPException(status_code=404, detail="Account not found")

    balance_previously = account.balance

    new_balance = balance_previously + transaction.amount

    account.balance = new_balance

    #---Generating a reversal reference---
    transaction_reference = generate_reference(TransactionReferencePrefix.REVERSAL.value)

    #---Genarating a new transaction---
    transaction_receipt = Transaction(
        account_id=account.id,
        reference=transaction_reference,
        transaction_type=TransactionType.WITHDRAWAL_REVERSAL,
        transaction_status=TransactionStatus.SUCCESS,
        amount=transaction.amount,
        description=f"Reversal of transaction {transaction.reference}",
        balance_before=balance_previously,
        balance_after=new_balance,
    )

    logger.info(f"Withdrawal reversal {transaction_reference} created successfully.")

    return transaction, transaction_receipt



def make_transfer_reversal(session: Session, sender_transaction: Transaction, receiver_transaction: Transaction) -> tuple[Transaction, Transaction]:

    logger.info(f"Transfer reversal requested for reference {sender_transaction.reference}.")

    sender_account = session.get(Account, sender_transaction.account_id)
    if not sender_account:
        logger.warning(f"Sender account {sender_transaction.account_id} not found.")
        raise HTTPException(status_code=404, detail="Account not found")

    receiver_account = session.get(Account, receiver_transaction.account_id)
    if not receiver_account:
        logger.warning(f"Receiver account {receiver_transaction.account_id} not found.")
        raise HTTPException(status_code=404, detail="Account not found")

    if receiver_account.balance < sender_transaction.amount:
        logger.warning(f"Insufficient funds in receiver account {receiver_account.id} for reversal.")
        raise HTTPException(status_code=400, detail="Cannot reverse transaction due to insufficient funds")

    old_balance = receiver_account.balance
    new_acct_balance = old_balance - sender_transaction.amount
    receiver_account.balance = new_acct_balance

    balance_then = sender_account.balance
    balance_now = balance_then + receiver_transaction.amount
    sender_account.balance = balance_now

    reversal_reference = generate_reference(TransactionReferencePrefix.REVERSAL.value)

    sender_reversal_receipt = Transaction(
        account_id=sender_account.id,
        reference=reversal_reference,
        transaction_type=TransactionType.TRANSFER_OUT_REVERSAL,
        transaction_status=TransactionStatus.SUCCESS,
        amount=sender_transaction.amount,
        description=f"Reversal of transaction {sender_transaction.reference}",
        balance_before=balance_then,
        balance_after=balance_now,
    )

    receiver_reversal_receipt = Transaction(
        account_id=receiver_account.id,
        reference=reversal_reference,
        transaction_type=TransactionType.TRANSFER_IN_REVERSAL,
        transaction_status=TransactionStatus.SUCCESS,
        amount=receiver_transaction.amount,
        description=f"Reversal of transaction {receiver_transaction.reference}",
        balance_before=old_balance,
        balance_after=new_acct_balance,
    )

    logger.info(f"Transfer reversal {reversal_reference} completed successfully.")

    return sender_reversal_receipt, receiver_reversal_receipt


def freeze_the_account(session: Session, account_number: str) -> Account:

    logger.info(f"Freeze request for account {account_number}.")

    #---Querying the database to get the account---
    account = session.exec(
        select(Account).where(Account.account_number == account_number)
    ).first()

    if not account:
        logger.warning(f"Account {account_number} not found.")
        raise HTTPException(status_code=404, detail="Account not found")

    if account.status == AccountStatus.CLOSED:
        logger.warning(f"Attempt to freeze closed account {account_number}.")
        raise HTTPException(status_code=400, detail="Closed accounts cannot be frozen.")

    #---Checking the account status---
    if account.status == AccountStatus.SUSPENDED:
        logger.warning(f"Account {account_number} is already frozen.")
        raise HTTPException(status_code=400, detail="Account is currently frozen")

    account.status = AccountStatus.SUSPENDED

    logger.info(f"Account {account_number} frozen successfully.")

    return account


def unfreeze_the_account(session: Session, account_number: str) -> Account:

    logger.info(f"Unfreeze request for account {account_number}.")

    account = session.exec(
        select(Account).where(Account.account_number == account_number)
    ).first()

    if not account:
        logger.warning(f"Account {account_number} not found.")
        raise HTTPException(status_code=404, detail="Account not found")

    #---Checking the account status---
    if account.status == AccountStatus.CLOSED:
        logger.warning(f"Attempt to unfreeze closed account {account_number}.")
        raise HTTPException(status_code=400, detail="Closed accounts cannot be unfrozen.")

    #---Checking the account status---
    if account.status != AccountStatus.SUSPENDED:
        logger.warning(f"Account {account_number} is not suspended.")
        raise HTTPException(status_code=400, detail="Account is currently not suspended")

    account.status = AccountStatus.ACTIVE

    logger.info(f"Account {account_number} unfrozen successfully.")

    return account
   
  
    

  


    


    