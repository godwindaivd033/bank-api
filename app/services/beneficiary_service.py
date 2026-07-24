from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.user import User
from app.models.account import Account
from app.services.logger import logger
from app.models.beneficiary import Beneficiary, BeneficiaryRead, BeneficiaryCreate


def get_authenticated_user(session: Session, active_user: dict):
    email= active_user.get("sub")

    user= session.exec(select(User).where(User.email == email)).first()

    if not user:
        raise HTTPException(status_code= 404, detail= "User not found")
    return user



def get_user_account(session: Session, user: User) -> Account:
    """Fetch the logged-in user's account, or 404 if missing."""
    account = session.exec(select(Account).where(Account.user_id == user.id)).first()
    if not account:
        logger.warning(f"Account not found for user {user.id}.")
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def get_account_by_number(session: Session, beneficiary_create: BeneficiaryCreate, account: Account, user: User)-> Account:
    #finding the beneficiary account using the account number
    beneficiary_account= session.exec(select(Account).where(Account.account_number == beneficiary_create.beneficiary_account_number)).first()

    if not beneficiary_account:
        logger.warning(f"Beneficiary account {beneficiary_create.beneficiary_account_number} not found.")
        raise HTTPException(status_code= 404, detail= "Account not found")
    

    #--Preventing adding account owner as beneficiary--
    if account.id == beneficiary_account.id:
        logger.warning(f"User {user.id} attempted to add their own account as beneficiary.")
        raise HTTPException(status_code= 400, detail= "Cannot add your account as a beneficiary")
    
    return beneficiary_account

 #---Validating duplicate---
def validate_not_duplicate(session: Session, account: Account, user: User, beneficiary_account: Account):
    existing_beneficiary= session.exec(select(Beneficiary).where(Beneficiary.owner_account_id == account.id, Beneficiary.beneficiary_account_id == beneficiary_account.id)).first()

    if existing_beneficiary:
        logger.warning(f"Duplicate beneficiary attempt for user {user.id}.")
        raise HTTPException(
            status_code=400,
            detail="Beneficiary already exists"
        )



#---Helper: build the beneficiary search query---
def build_beneficiary_query(session, owner_account_id, search):
    query = select(Beneficiary).where(Beneficiary.owner_account_id == owner_account_id)

    #---Searching by beneficiary account number---
    if search.account_number:
        beneficiary_account = session.exec(select(Account).where(Account.account_number == search.account_number)).first()

        if not beneficiary_account:
            logger.warning(f"Beneficiary account {search.account_number} not found.")
            raise HTTPException(status_code=404, detail="Account not found")

        query = query.where(Beneficiary.beneficiary_account_id == beneficiary_account.id)

    #---Searching by nickname---
    if search.nickname:
        query = query.where(Beneficiary.nickname.contains(search.nickname))

    return query


#---Helper: convert beneficiaries into BeneficiaryRead objects---
def serialize_beneficiaries(session, beneficiaries):
    response = []

    for b in beneficiaries:

        beneficiary_account = session.get(Account, b.beneficiary_account_id)

        if not beneficiary_account:
            logger.warning(f"Beneficiary account ID {b.beneficiary_account_id} not found.")
            continue

        beneficiary_user = session.get(User, beneficiary_account.user_id)

        if not beneficiary_user:
            logger.warning(f"Beneficiary user {beneficiary_account.user_id} not found.")
            continue

        response.append(
            BeneficiaryRead(id= b.id,
                account_number=beneficiary_account.account_number,
                account_name=f"{beneficiary_user.first_name} {beneficiary_user.last_name}",
                nickname=b.nickname,
                created_at=b.created_at
            )
        )

    return response


#---Helper: get the account belonging to the authenticated user---
def get_account_or_404(session, user):
    account = session.exec(select(Account).where(Account.user_id == user.id)).first()
    if not account:
        logger.warning(f"Account not found for user {user.id}.")
        raise HTTPException(status_code= 404, detail= "Account not found")
    return account


#---Helper: get a beneficiary owned by this account, or raise---
def get_owned_beneficiary_or_404(session, beneficiary_id, account):
    beneficiary= session.get(Beneficiary, beneficiary_id)

    if not beneficiary:
        logger.warning(f"Beneficiary {beneficiary_id} not found.")
        raise HTTPException(status_code= 404, detail= "Beneficiary not found")

    #---Ensuring the beneficiary account belongs to the owner---
    if beneficiary.owner_account_id != account.id:
        logger.warning(f"Unauthorized update attempt on beneficiary {beneficiary_id} by user {account.user_id}.")
        raise HTTPException(status_code= 403, detail= "Bad request")

    return beneficiary


#---Helper: build a single BeneficiaryRead, raising if related records are missing---
def serialize_single_beneficiary(session, beneficiary):
    beneficiary_account= session.get(Account, beneficiary.beneficiary_account_id)
    if not beneficiary_account:
        logger.warning(f"Beneficiary account for beneficiary {beneficiary.id} not found.")
        raise HTTPException(status_code= 404, detail= "Beneficiary account not found")

    beneficiary_user= session.get(User,  beneficiary_account.user_id)
    if not beneficiary_user:
        logger.warning(f"Beneficiary user {beneficiary_account.user_id} not found.")
        raise HTTPException(status_code= 404, detail= "Beneficiary user not found")

    return BeneficiaryRead(id= beneficiary.id,
    account_number= beneficiary_account.account_number,
    account_name=f"{beneficiary_user.first_name} {beneficiary_user.last_name}",
    nickname= beneficiary.nickname,
    created_at= beneficiary.created_at)