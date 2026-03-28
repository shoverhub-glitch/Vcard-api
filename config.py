from pydantic_settings import BaseSettings
from functools import lru_cache
import secrets
import os


def generate_secret() -> str:
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "wcard"
    
    max_pool_size: int = 10
    min_pool_size: int = 1
    
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    
    jwt_secret: str = os.environ.get("JWT_SECRET", generate_secret())
    jwt_refresh_secret: str = os.environ.get("JWT_REFRESH_SECRET", generate_secret())
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
