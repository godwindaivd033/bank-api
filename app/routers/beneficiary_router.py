from fastapi import APIRouter, Depends, Query
from sqlmodel import  Session, select
from app.database import get_session
from app.auth import get_user_with_role
from app.models.account import Account
from app.models.beneficiary import Beneficiary, BeneficiarySearch, BeneficiaryCreate, BeneficiaryRead, BeneficiaryUpdate
from app.services.logger import logger
from app.services.beneficiary_service import get_authenticated_user
from app.models.user import User
from app.services.beneficiary_service import get_user_account, get_account_by_number, validate_not_duplicate, serialize_beneficiaries, build_beneficiary_query, get_owned_beneficiary_or_404, serialize_single_beneficiary
from app.services.dashboard_service import get_account_or_404








router = APIRouter(prefix = "/ beneficiary", tags= ["beneficiary"])






#---Creating the endpoint that enables user to create a beneficiary---
@router.post("/", response_model= BeneficiaryRead, status_code= 201)
def create_beneficiary(beneficiary_create: BeneficiaryCreate, session: Session= Depends(get_session),active_user: dict= Depends(get_user_with_role)):

    #---Getting the user---
    user = get_authenticated_user(session, active_user)
    logger.info(f"Beneficiary creation requested by user {user.id}")

    #---Getting the account---
    account= get_user_account(session, user)
    logger.info(f"Beneficiary creation requested by user account {account.id}")
    
    #---Getting the beneficiary account---
    beneficiary_account= get_account_by_number(session, account, user, beneficiary_create)

    #---Checking beneficiary to avoid duplication---
    validate_not_duplicate(session, account, user, beneficiary_account)

    #---Create beneficiary---
    beneficiary_created = Beneficiary(
        owner_account_id=account.id,
        beneficiary_account_id= beneficiary_account.id,
        nickname=beneficiary_create.nickname,
    )

    session.add(beneficiary_created)
    session.commit()
    session.refresh(beneficiary_created)

    logger.info(f"Beneficiary added successfully for user {user.id}.")

    #---Get beneficiary owner's details---
    beneficiary_user = session.get(User, beneficiary_account.user_id)

    return BeneficiaryRead(id= beneficiary_created.id,
        account_number=beneficiary_account.account_number,
        account_name=f"{beneficiary_user.first_name} {beneficiary_user.last_name}",
        nickname=beneficiary_created.nickname,
        created_at=beneficiary_created.created_at,
    )




#---Creating the endpoint that enables user to get all beneficiaries---
@router.get("/all", response_model= list[BeneficiaryRead], status_code= 200)
def get_all_beneficiaries(session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role), skip: int=0, limit: int = Query(default= 10, le= 100)):

    #---Authenticating the user---
    user= get_authenticated_user(session, active_user)
    logger.info(f"Fetching beneficiaries for user {user.id}.")

    #---getting the account---
  
    account = get_account_or_404(session, user)

    owner_beneficiaries= session.exec(select(Beneficiary).where(Beneficiary.owner_account_id== account.id).offset(skip).limit(limit)).all()

    #---Getting the beneficiary account
    response = serialize_beneficiaries(session, owner_beneficiaries)

    logger.info(f"Retrieved {len(response)} beneficiary(ies) for user {user.id}.")

    return response


#---Creating the endpoint that enables users to search through beneficiaries---
@router.get("/search", response_model=list[BeneficiaryRead], status_code=200)
def search_beneficiaries(
    session: Session = Depends(get_session),
    search: BeneficiarySearch = Depends(),
    active_user: dict = Depends(get_user_with_role)
):

    #---Authenticating the user---
    user = get_authenticated_user(session, active_user)
    logger.info(f"Beneficiary search requested by user {user.id}.")

  #---Getting the owner's account---
    owner_account = get_account_or_404(session, user)

    #---Starting the query with only this user's beneficiaries to ensure the user beneficiaries belongs to the account ---
    query = build_beneficiary_query(session, owner_account.id, search)

    #---Executing the query---
    beneficiaries = session.exec(query).all()

    #---Building the response---
    response = serialize_beneficiaries(session, beneficiaries)

    logger.info(f"Beneficiary search returned {len(response)} result(s) for user {user.id}.")

    return response





#---Creating the endpoint that enables user to update selected data in the database---
@router.patch("/{beneficiary_id}", response_model= BeneficiaryRead, status_code= 200)
def update_beneficiary(update_data: BeneficiaryUpdate, beneficiary_id: int, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #--Authenticating user---
    user= get_authenticated_user(session, active_user)
    logger.info(f"Beneficiary update requested by user {user.id}.")

    account = get_account_or_404(session, user)

    #--Getting the requested beneficiary---
    beneficiary = get_owned_beneficiary_or_404(session, beneficiary_id, account)

    #---Updating the nickname
    if update_data.nickname is not None:
        beneficiary.nickname = update_data.nickname

    session.commit()
    session.refresh(beneficiary)

    logger.info(f"Beneficiary {beneficiary_id} updated successfully.")

    beneficiary_update = serialize_single_beneficiary(session, beneficiary)

    return beneficiary_update
    


#---Creating the endpoint that enables useer to be able to get a particular beneficiary---
@router.get("/{beneficiary_id}", response_model= BeneficiaryRead, status_code= 200)
def get_beneficiary(beneficiary_id: int, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #---Get authenticated user---
    user= get_authenticated_user(session, active_user)
    logger.info(f"Fetching beneficiary {beneficiary_id} for user {user.id}.")

    #---Get the owner account---
    owner_account = get_account_or_404(session, user)

    #---Getting the particular beneficiary using the beneficiary id
    beneficiary = get_owned_beneficiary_or_404(session, beneficiary_id, owner_account)

    #--Getting the beneficiary account---
    beneficiary_update = serialize_single_beneficiary(session, beneficiary)

    logger.info(f"Beneficiary {beneficiary_id} retrieved successfully.")

    return beneficiary_update