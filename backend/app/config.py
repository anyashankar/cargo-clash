"""Configuration settings for Cargo Clash."""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://cargo_user:cargo_pass@localhost:5432/cargo_clash"
    async_database_url: str = "postgresql+asyncpg://cargo_user:cargo_pass@localhost:5432/cargo_clash"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # AWS
    aws_region: str = "us-west-2"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    
    # AWS Cognito
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_client_secret: str = ""
    
    # AWS SQS
    sqs_queue_url: str = ""
    
    # Security
    secret_key: str = "your-super-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application
    debug: bool = True
    log_level: str = "INFO"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Game Configuration
    max_players_per_game: int = 100
    game_tick_rate: int = 10  # Updates per second
    world_size: int = 1000
    
    # Performance
    max_concurrent_requests: int = 1000
    request_timeout: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
