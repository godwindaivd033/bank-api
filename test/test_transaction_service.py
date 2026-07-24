from decimal import Decimal

from app.models.user import User
from app.models.account import Account
from app.models.transaction import TransactionCreate, TransactionType, TransactionStatus
from app.models.enums import AccountStatus

from app.services.transaction_service import validate_transaction_request, deposit_helper_function, withdrawal_helper_function, make_transfer
import pytest
from fastapi import HTTPException




def test_valid_request_returns_account(session, account, active_user, transaction):
    result = validate_transaction_request(session, active_user, transaction)   # - RUN
    assert result.id == account.id                                             # - CHECK


def test_user_not_found(session, account, active_user, transaction):
    active_user["sub"] = "daniel@gmail.com"

    with pytest.raises(HTTPException) as exc:
        validate_transaction_request(session, active_user, transaction)

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


def test_account_not_found(session, account, active_user, transaction):
    account.id= 22 #- Sabotage the account on purpose

    with pytest.raises(HTTPException) as exc:
        validate_transaction_request(session, active_user, transaction)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Account not found"



def test_not_account_user_id(session, account, active_user, transaction):
    account.user_id = 17

    with pytest.raises(HTTPException) as exc:
        validate_transaction_request(session, active_user, transaction)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Forbidden request."


def test_closed_account_rejected(session, account, active_user, transaction):
    account.status = AccountStatus.CLOSED
    

    with pytest.raises(HTTPException) as exc:
        validate_transaction_request(session, active_user, transaction)
    assert exc.value.status_code == 400
    assert exc.value.detail ==  "Cannot deposit into a closed account."

def test_transaction_amount(session, account, active_user, transaction):
    transaction.amount = Decimal("-100")

    with pytest.raises(HTTPException) as exc:
        validate_transaction_request(session, active_user, transaction)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Amount has to be greater than zero"




def test_deposit_increases_balance(session, account, active_user, transaction):
    balance_before = account.balance

    result = deposit_helper_function(session, transaction, active_user)

    assert result.balance_before == balance_before
    assert result.balance_after == balance_before + transaction.amount
    assert account.balance == balance_before + transaction.amount


def test_deposit_sets_correct_transaction_fields(session, account, active_user, transaction):
    result = deposit_helper_function(session, transaction, active_user)

    assert result.account_id == account.id
    assert result.transaction_type == TransactionType.DEPOSIT
    assert result.transaction_status == TransactionStatus.SUCCESS
    assert result.amount == transaction.amount
    assert result.description == transaction.description


def test_deposit_generates_unique_reference(session, account, active_user, transaction):
    result = deposit_helper_function(session, transaction, active_user)

    assert result.reference is not None
    assert result.reference != ""


def test_deposit_fails_on_closed_account(session, account, active_user, transaction):
    account.status = AccountStatus.CLOSED
    session.commit()

    with pytest.raises(HTTPException) as exc:
        deposit_helper_function(session, transaction, active_user)

    assert exc.value.status_code == 400


def test_deposit_fails_on_negative_amount(session, account, active_user):
    bad_transaction = TransactionCreate(account_id=account.id, amount=Decimal("-500"))

    with pytest.raises(HTTPException) as exc:
        deposit_helper_function(session, bad_transaction, active_user)

    assert exc.value.status_code == 400

def test_withdrawal_reduces_balance(session, account, active_user, transaction):
    balance_before= account.balance
    result= withdrawal_helper_function(session, active_user, transaction)
    assert result.balance_after == balance_before - transaction.amount
    assert account.balance == balance_before - transaction.amount




def test_unique_reference_generates(session, account, active_user, transaction):
    result= withdrawal_helper_function(session, active_user, transaction)

    assert result.reference != ""
    assert result.reference is not None

def test_withdrawal_field_is_correct(session, account, active_user, transaction):
    result= withdrawal_helper_function(session, active_user, transaction)

    assert result.transaction_type == TransactionType.WITHDRAWAL
    assert result.transaction_status == TransactionStatus.SUCCESS
    assert result.account_id == account.id
    assert result.amount == transaction.amount
    assert result.description == transaction.description

def test_withdrawal_fails_on_negative_balance(session, account, active_user, transaction):
    transaction.amount = Decimal("-2000")

    with pytest.raises(HTTPException) as exc:
        withdrawal_helper_function(session, active_user, transaction)
    assert exc.value.status_code== 400



def test_valid_make_transfer_returns_two_transactions(session, active_user, transfer):
                                                                  
  sender_tx, receiver_tx= make_transfer(session, active_user, transfer)
  
  assert sender_tx.transaction_type == TransactionType.TRANSFER_OUT
  assert receiver_tx.transaction_type == TransactionType.TRANSFER_IN



def test_user_not_found(session, active_user, transfer):
    active_user["sub"]= "avindazin@gmail.com"
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


def test_account_not_found(session, active_user, transfer):
    transfer.from_account_id = 89
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)
    assert exc.value.status_code == 404
    assert exc.value.detail ==  "Account not found"

def test_account_belongs_to_user(session, active_user, account, transfer):
    account.user_id = 14
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Forbidden request"

def test_account_current_status(session, active_user, account, transfer):
    account.status = AccountStatus.CLOSED
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Cannot transfer from a closed account"
    

def test_account_belongs_to_receiver(session, active_user, another_account, transfer):
    another_account.account_number = "22200033344" #--Sabotaging the account number--
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Reciever account not found"


def test_owner_not_receiver_account(session, active_user, another_account, account, transfer):
    account.id = 7
    account.account_number = "00022345555" 
    
    session.add(account)
    session.commit()
    another_account.account_number = account.account_number

    # 2. Force the transfer to point to the EXACT SAME account
    transfer.from_account_id = 7
    transfer.to_account_number = "00022345555"  #
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)
    assert exc.value.status_code == 400
    assert exc.value.detail == "You cannot transfer money to the same account."

def test_receiver_acccount_current_status(session, active_user, another_account, transfer):
    another_account.status = AccountStatus.CLOSED
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Cannot transfer money to a closed account"

def  test_amount_is_not_negative(session, active_user, transfer):
    transfer.amount = Decimal("-5000")
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Amount must be greater than zero"


def  test_amount_is_greater_than_zero(session, active_user, transfer):
    transfer.amount = Decimal("0")
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Amount must be greater than zero"


def test_owner_balance_greater_than_transfer_amount(session, active_user, account, transfer):
    account.balance = Decimal("300")
    with pytest.raises(HTTPException) as exc:
        make_transfer(session, active_user, transfer)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Insufficient funds"



def test_balance_saved_properly(session, active_user, another_account, account, transfer):
    sender_account_balance_before = account.balance
    receiver_account_balance_before = another_account.balance

    sender_tx, receiver_tx = make_transfer(session, active_user, transfer)
    assert sender_tx.balance_before == sender_account_balance_before
    assert receiver_tx.balance_before == receiver_account_balance_before
    assert sender_tx.balance_after == sender_account_balance_before - transfer.amount
    assert receiver_tx.balance_after == receiver_account_balance_before + transfer.amount



def test_reference_was_well_saved(session, active_user, transfer):
    sender_tx, receiver_tx= make_transfer(session, active_user, transfer)

    assert sender_tx.reference != ""
    assert sender_tx.reference is not None
    assert receiver_tx.reference != ""
    assert receiver_tx.reference is not None
    assert sender_tx.reference == receiver_tx.reference
