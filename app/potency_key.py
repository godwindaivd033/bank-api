import secrets
import requests
from decimal import Decimal


BASE_URL = "http://127.0.0.1:8000"


login_response = requests.post(
    f"{BASE_URL}/login",  
    data={
        "username": "your_test_user@example.com",
        "password": "your_test_password"
    }
)


print(login_response.status_code)
print(login_response.json())   

token = login_response.json()["access_token"]   

from_account_id = 20
to_account_number = "6612345678"
amount = Decimal("50000")
description = "Test transfer"

# Generate a new idempotency key for this new transfer
idempotency_key = secrets.token_urlsafe(32)

response = requests.post(
    "http://127.0.0.1:8000/transaction/transfer",
    headers={
        "Idempotency-Key": idempotency_key
    },
    json={
        "from_account_id": from_account_id,
        "to_account_number": to_account_number,
        "amount": str(amount),
        "description": description
    }
)

print(response.json())