from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'mealtrack.db'}"

    secret_key: str = "change-me-to-a-random-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 30  # 30 days

    # Default user seeded on first startup
    default_user_name: str = "Wajahat Ahmed"
    default_user_email: str = "wajahatahmad056@gmail.com"
    default_user_password: str = "change-me"

    # Redis Streams — event bus for cross-app integration
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
