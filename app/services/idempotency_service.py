#---Writting the idempotency service function---
import json
from sqlmodel import select, Session
from app.models.idempotency_key import IdempotencyKey


#---Writting the service that checks if idempotency key has been used in a transaction---

def check_idempotency_key(session: Session, key: str, endpoint: str) -> IdempotencyKey:
    return session.exec(select(IdempotencyKey).where(IdempotencyKey.key == key, IdempotencyKey.endpoint == endpoint)).first()



#---Writting the service that saves the idempotency key data---
def save_idempotency_key(session: Session, key: str, endpoint: str, response_data: dict, status_code: int) -> IdempotencyKey:
    record= IdempotencyKey(Key= key,
                           endpoint= endpoint,
                           response_body= json.dumps(response_data),
                           status_code= status_code)
    session.add(record)
    return record
    