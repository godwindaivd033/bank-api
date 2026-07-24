from sqlmodel import  select
from fastapi import HTTPException
from app.models.account import Account
from app.services.logger import logger
from app.models.transaction import  TransactionRead




#---Helper: get the account belonging to the authenticated user---
def get_account_or_404(session, user):
    account = session.exec(select(Account).where(Account.user_id == user.id)).first()
    if not account:
        logger.warning(f"Account not found for user {user.id}.")
        raise HTTPException(status_code= 404, detail= "Account not found")
    return account


#---Helper: convert transactions into TransactionRead objects---
def serialize_transactions(transactions):
    receipt= []
    for tx in transactions:
        receipt.append(TransactionRead(id= tx.id,
    account_id= tx.account_id,
    reference= tx.reference,
    amount= tx.amount,
    transaction_type= tx.transaction_type,
    transaction_status= tx.transaction_status,
    description= tx.description,
    balance_before= tx.balance_before,
    balance_after= tx.balance_after,
    created_at= tx.created_at
))
    return receipt