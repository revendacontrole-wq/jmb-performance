import os

class Settings:
    PROJECT_NAME: str = "JMB PERFORMANCE"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "jmb_performance_secret_key_2026_super_secure")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    DATABASE_URL: str = "sqlite:///./jmb_performance.db"

settings = Settings()
