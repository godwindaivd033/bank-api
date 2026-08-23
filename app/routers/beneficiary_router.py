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
from fastapi.concurrency import run_in_threadpool
import json
from app.redis_client import redis_client





router = APIRouter(prefix = "/ beneficiary", tags= ["beneficiary"])






#---Creating the endpoint that enables user to create a beneficiary---
@router.post("/", response_model= BeneficiaryRead, status_code= 201)
async def create_beneficiary(beneficiary_create: BeneficiaryCreate, session: Session= Depends(get_session),active_user: dict= Depends(get_user_with_role)):

    #---Getting the user---
    user = await run_in_threadpool(get_authenticated_user, session, active_user)
    logger.info(f"Beneficiary creation requested by user {user.id}")


   
    #---Getting the account---
    account= await run_in_threadpool(get_user_account, session, user)
    logger.info(f"Beneficiary creation requested by user account {account.id}")
    
    #---Getting the beneficiary account---
    beneficiary_account=await run_in_threadpool(get_account_by_number, session, account, user, beneficiary_create)

    #---Checking beneficiary to avoid duplication---
    await run_in_threadpool(validate_not_duplicate, session, account, user, beneficiary_account)

    #---Create beneficiary---
    beneficiary_created = Beneficiary(
        owner_account_id=account.id,
        beneficiary_account_id= beneficiary_account.id,
        nickname=beneficiary_create.nickname,
    )

    session.add(beneficiary_created)
    session.commit()
    session.refresh(beneficiary_created)

    #---Invalidating the redis cache since changes has been made---
    logger.info(f"invalidating the cache records for account{user.id}")
    await run_in_threadpool(redis_client.delete, f"account{user.id}")

    logger.info(f"Beneficiary added successfully for user {user.id}.")

    #---Get beneficiary owner's details---
    beneficiary_user = await run_in_threadpool(session.get, User, beneficiary_account.user_id)

    return BeneficiaryRead(id= beneficiary_created.id,
        account_number=beneficiary_account.account_number,
        account_name=f"{beneficiary_user.first_name} {beneficiary_user.last_name}",
        nickname=beneficiary_created.nickname,
        created_at=beneficiary_created.created_at,
    )




#---Creating the endpoint that enables user to get all beneficiaries---
@router.get("/all", response_model= list[BeneficiaryRead], status_code= 200)
async def get_all_beneficiaries(session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role), skip: int=0, limit: int = Query(default= 10, le= 100)):

    #---Authenticating the user---
    user= await run_in_threadpool(get_authenticated_user,session, active_user)
    logger.info(f"Fetching beneficiaries for user {user.id}.")

    #---Getting the account from the databse---
    account = await run_in_threadpool(get_account_or_404, session, user)

    #---Making the redis client cache key---
    cache_key= f"beneficiary:{account.id}:{skip}:{limit}"

    logger.info(f"Sending request to the redis cache for the data requested")
    cached = await run_in_threadpool(redis_client.get, cache_key)

    
    if cached:
        logger.info(f"User request hit the redis cache")
        return json.loads(cached)

    #---If the data was not found or missed the redis cache, query the data from the database---
    logger.info(f"Cache miss for {cache_key}, querying database.")
    owner_beneficiaries= await run_in_threadpool(lambda :session.exec(select(Beneficiary).where(Beneficiary.owner_account_id== account.id).offset(skip).limit(limit)).all())

    #---Getting the beneficiary account
    response = await run_in_threadpool(serialize_beneficiaries, session, owner_beneficiaries)

    logger.info(f"Retrieved {len(response)} beneficiary(ies) for user {user.id}.")
    response_data = [r.model_dump(mode="json") for r in response]

    await run_in_threadpool(redis_client.set, cache_key, json.dumps(response_data), ex=60)

    logger.info(f"Retrieved {len(response)} beneficiary(ies) for user {user.id}.")

    return response_data


#---Creating the endpoint that enables users to search through beneficiaries---
@router.get("/search", response_model=list[BeneficiaryRead], status_code=200)
async def search_beneficiaries(
    session: Session = Depends(get_session),
    search: BeneficiarySearch = Depends(),
    active_user: dict = Depends(get_user_with_role)
):

    #---Authenticating the user---
    user = await run_in_threadpool(get_authenticated_user, session, active_user)
    logger.info(f"Beneficiary search requested by user {user.id}.")

    #---Getting the owner's account---
    owner_account = await run_in_threadpool(get_account_or_404, session, user)

    #---Starting the query with only this user's beneficiaries to ensure the user beneficiaries belongs to the account---
    query = await run_in_threadpool(build_beneficiary_query, session, owner_account.id, search)

    #---Executing the query---
    beneficiaries = await run_in_threadpool(lambda: session.exec(query).all())

    #---Building the response---
    response = await run_in_threadpool(serialize_beneficiaries, session, beneficiaries)

    logger.info(f"Beneficiary search returned {len(response)} result(s) for user {user.id}.")

    return response



#---Creating the endpoint that enables user to update selected data in the database---
@router.patch("/{beneficiary_id}", response_model= BeneficiaryRead, status_code= 200)
async def update_beneficiary(update_data: BeneficiaryUpdate, beneficiary_id: int, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #--Authenticating user---
    user= await run_in_threadpool(get_authenticated_user, session, active_user)
    logger.info(f"Beneficiary update requested by user {user.id}.")

    account =await run_in_threadpool(get_account_or_404, session, user)

    
    #--If not, getting the requested beneficiary---
    beneficiary = await run_in_threadpool(get_owned_beneficiary_or_404, session, beneficiary_id, account)

    #---Updating the nickname
    if update_data.nickname is not None:
        beneficiary.nickname = update_data.nickname

    session.commit()
    session.refresh(beneficiary)

    logger.info(f"Beneficiary {beneficiary_id} updated successfully.")

    beneficiary_update = await run_in_threadpool(serialize_single_beneficiary, session, beneficiary)

    #---Invalidating cache for the updates made---
    await run_in_threadpool(redis_client.delete, f"beneficiary:{beneficiary_id}")

    return beneficiary_update
    


#---Creating the endpoint that enables useer to be able to get a particular beneficiary---
@router.get("/{beneficiary_id}", response_model= BeneficiaryRead, status_code= 200)
async def get_beneficiary(beneficiary_id: int, session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #---Get authenticated user---
    user= await run_in_threadpool(get_authenticated_user, session, active_user)
    logger.info(f"Fetching beneficiary {beneficiary_id} for user {user.id}.")

    #---Get the owner account---
    owner_account = await run_in_threadpool(get_account_or_404, session, user)
    
    #---Making the redis cache---
    cache_key= f"beneficiary:{beneficiary_id}"

    #---Attempting grabbing of the requested data from the redis cache---
    logger.info(f'Quering the redis cache to get the {cache_key}')
    cached= await run_in_threadpool(redis_client.get, cache_key)

    if cached:
        logger.info("Queried data hit the redis cache")
        return json.loads(cached)

    #---Getting the particular beneficiary using the beneficiary id
    beneficiary = await run_in_threadpool(get_owned_beneficiary_or_404, session, beneficiary_id, owner_account)

    #--Getting the beneficiary account---
    beneficiary_update = await run_in_threadpool(serialize_single_beneficiary, session, beneficiary)

    #---Updating the redis cache for any invalidations---
    beneficiary_data= [beneficiary_update.model_dump(mode= "json")]
    await run_in_threadpool(redis_client.set, cache_key, json.dumps(beneficiary_data), ex= 60)

    logger.info(f"Beneficiary {beneficiary_id} retrieved successfully.")

    return beneficiary_data