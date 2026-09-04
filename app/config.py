import os
import shutil

class Settings:
    PROJECT_NAME: str = "JMB PERFORMANCE"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "jmb_performance_secret_key_2026_super_secure")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    @property
    def DATABASE_URL(self) -> str:
        # Check if running in Vercel or read-only Lambda environment
        if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("VERCEL_ENV"):
            tmp_db = "/tmp/jmb_performance.db"
            if not os.path.exists(tmp_db):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                local_db = os.path.join(base_dir, "jmb_performance.db")
                if not os.path.exists(local_db):
                    local_db = os.path.join(base_dir, "database.sqlite")
                if os.path.exists(local_db):
                    try:
                        shutil.copy(local_db, tmp_db)
                    except Exception as e:
                        print(f"Error copying DB to /tmp: {e}")
            return f"sqlite:///{tmp_db}"
        return os.getenv("DATABASE_URL", "sqlite:///./jmb_performance.db")

settings = Settings()
