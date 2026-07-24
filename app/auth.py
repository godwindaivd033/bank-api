#---Building the authentication workflow---
from fastapi import Depends, HTTPException
from jose import jwt
from jose.exceptions import JWTError
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from datetime import datetime, UTC, timedelta
import app.settings as settings


#---Creating the token reader---
OAuth2scheme= OAuth2PasswordBearer(tokenUrl= "login")


#---Creating the method that hashes the password---
def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


#---Creating the method that verifies the password---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())



#---Creating the access token---
def create_access_token(sub: str, role: str) -> str:
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured")
    expire= datetime.now(UTC) + timedelta(minutes= int(settings.ACCESS_TOKEN_LIMIT))
    payload= {"sub": sub,
              "role": role,
              "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm= settings.ALGORITHM)



#---Creating the method for decoding the access token---
def decode_access_token(token: str) -> dict| None:
    if not settings.SECRET_KEY:
        return None
    try:
        payload= jwt.decode(token, settings.SECRET_KEY, algorithms= [settings.ALGORITHM])
    except JWTError:
        return None
        
    return payload



def get_user_with_role(token: str = Depends(OAuth2scheme)) -> dict:
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    return payload