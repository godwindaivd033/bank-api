from fastapi import APIRouter, Depends, Query, Request
from app.models.beneficiary import Beneficiary
from app.models.transaction import Transaction
from app.auth import get_user_with_role
from app.database import get_session
from sqlmodel import Session, select
from app.services.beneficiary_service import get_authenticated_user
from app.models.dashboard import DashboardRead
from app.services.logger import logger
from app.services.dashboard_service import get_account_or_404, serialize_transactions
from fastapi.concurrency import run_in_threadpool
from app.limiter import limiter


router= APIRouter(prefix= "/dashboard", tags= ["beneficiary"])






#---Creating the endpoint that enables user to get dashboard data---
@router.get("/", response_model= DashboardRead, status_code= 200)
@limiter.limit("15/minute")
async def get_dashboard(request: Request, skip: int= 0, limit: int= Query(default= 5, le= 100), session: Session= Depends(get_session), active_user: dict= Depends(get_user_with_role)):

    #--Authenticating the user---
    user= await run_in_threadpool(get_authenticated_user,session, active_user)
    logger.info(f"Dashboard requested by user {user.id}.")

    account = get_account_or_404(session, user)

    #--Getting the beneficiaries for the account--
    beneficiaries = session.exec(select(Beneficiary).where(Beneficiary.owner_account_id == account.id)).all()

    #---counting the beneficiaries---
    beneficiary_count= len(beneficiaries)

    transactions= await run_in_threadpool (lambda :session.exec(select(Transaction).where(Transaction.account_id == account.id)).all())

    #---Counting the transactions---
    transaction_count= len(transactions)

    #---Getting the latest transactions---
    recent_transaction= await run_in_threadpool(lambda: session.exec(select(Transaction).where(Transaction.account_id == account.id).order_by(Transaction.created_at.desc()).offset(skip).limit(limit)).all())
    receipt= serialize_transactions(recent_transaction)

    #---Building the dashboardRead---
    dashboard_read= DashboardRead(account_holder_name= f"{user.first_name} {user.last_name}",                                
    account_number= account.account_number,
    account_type= account.account_type,
    current_balance= account.balance,
    beneficiary_count= beneficiary_count,
    transaction_count= transaction_count,

    recent_transactions= receipt)

    logger.info(
        f"Dashboard generated for user {user.id}: "
        f"{beneficiary_count} beneficiary(ies), "
        f"{transaction_count} transaction(s), "
        f"{len(receipt)} recent transaction(s)."
    )

    return dashboard_read