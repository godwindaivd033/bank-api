import pytest

from sqlmodel import SQLModel, Session, create_engine

from app.models.user import User
from app.models.account import Account, AccountCreate, AccountUpdate
from app.models.transaction import Transaction, TransactionCreate, TransferCreate
from decimal import Decimal

TEST_DATABASE_URL = "sqlite:///test.db"

test_engine = create_engine(TEST_DATABASE_URL)




#---Creating the function that test can use automatically---

@pytest.fixture
def session():
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session


def get_test_session():
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def user(session):
    user = User(
        first_name="Godwin",
        last_name="David",
        email="godwin@test.com",
        password="fake_hashed_password",
        phone_number="08012345678"
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user

@pytest.fixture
 # Create a test account for that user
def account(session, user):
    account = Account(
        user_id=user.id,
        account_number="00012345555",
        account_type="Savings",
        balance= Decimal("50000")
    )

    session.add(account)
    session.commit()
    session.refresh(account)

    return account

  # Create the transaction request
@pytest.fixture
def transaction(account):
    transaction = TransactionCreate(
        account_id=account.id,
        amount=Decimal("20000"),
        description="Payment of loan"
    )

    return transaction

   # Fake authenticated user
@pytest.fixture
def active_user(user):
    active_user = {
        "sub": user.email,
        "role": "Customer"
    }

    return active_user

@pytest.fixture
def another_user(session):
    another_user = User(
        first_name="Godon",
        last_name="Davila",
        email="godwyn@test.com",
        password="fake_hashed_password",
        phone_number="07012345678"
    )

    session.add(another_user)
    session.commit()
    session.refresh(another_user)

    return another_user

@pytest.fixture
 # Create a test account for that user
def another_account(session, another_user):
    another_user_account = Account(
        user_id=another_user.id,
        account_number="00022345555",
        account_type="Savings",
        balance= Decimal("50000")
    )

    session.add(another_user_account)
    session.commit()
    session.refresh(another_user_account)

    return another_user_account


@pytest.fixture
def transfer(account, another_account):
    return TransferCreate(
        from_account_id=account.id,
        to_account_number=another_account.account_number,
        amount=Decimal("1000"),
        description="Test transfer",
    )


