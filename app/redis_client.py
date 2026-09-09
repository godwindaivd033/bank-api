import redis
from fastapi import HTTPException
from app.services.logger import logger


redis_client= redis.Redis(host= "localhost",
                          port= 6379,
                          decode_responses= True)



def check_rate_limit(key: str, max_attempts: int, window_seconds: int):
    current= redis_client.incr(key)

    if current == 1:
        redis_client.expire(key, window_seconds)

    if current > max_attempts:
        ttl= redis_client.ttl(key)
        logger.warning(f" Rate limit for {key} exceeded, retry in {ttl} seconds")
        raise HTTPException(status_code= 429, detail= f"Too many attempts,try again in {ttl} seconds")


