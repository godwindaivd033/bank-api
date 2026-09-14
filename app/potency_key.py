import secrets
import requests
from decimal import Decimal


from_account_id = 20
to_account_number = "6612345678"
amount = Decimal("50000")
description = "Test transfer"

# Generate a new idempotency key for this new transfer
idempotency_key = secrets.token_urlsafe(32)

response = requests.post(
    "http://127.0.0.1:8000/transfer",
    headers={
        "Idempotency-Key": idempotency_key
    },
    json={
        "from_account_id": from_account_id,
        "to_account_number": to_account_number,
        "amount": amount,
        "description": description
    }
)

print(response.json())