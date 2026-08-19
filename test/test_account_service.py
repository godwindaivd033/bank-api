from app.models.account import AccountCreate
import pytest
from app.models.enums import AccountStatus
from fastapi import HTTPException
from app.services.account_service import generate_account_number, get_account_by_id_or_404, get_authenticated_user_or_404, apply_account_update, validate_account_closure, validate_no_duplicate_account_type


#---Writting the test---
def test_generate_account_number(session, account):
    
    account_num= generate_account_number(session)

    assert account_num != account.account_number



def test_get_authenticated_user_or_404(user, session, active_user):
    user.email= "Danilo@gmail.com"
    active_user["sub"]= "daniella@gmail.com"
    with pytest.raises(HTTPException) as error:
        get_authenticated_user_or_404(session, active_user)
   
    assert error.value.status_code == 404
    assert error.value.detail == "User not found"


def test_get_account_by_id_or_404(user, account, session, active_user)