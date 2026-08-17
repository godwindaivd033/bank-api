from fastapi import APIRouter
from app.redis_client import redis_client



router = APIRouter()






@router.get("/test-redis")
def test_resdis():
    redis_client.set("message", "Hello from fastapi")

    redis_client.set("message", "Hello Redis")

    value= redis_client.get("message")
    return {"message": value}