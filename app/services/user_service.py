
from sqlmodel import select
from app.models.user import User
from app.database import get_session

def get_user_by_email(email: str):
    session = next(get_session())

    try:
        user = session.exec(
            select(User).where(User.email == email)
        ).first()

        return user

    finally:
        session.close()