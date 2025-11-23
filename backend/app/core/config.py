from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings and configuration"""

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./ai_proctor.db"
    DATABASE_POOL_SIZE: int = 5

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ML Model Configuration (based on Proctoring-AI standards)
    MODEL_CONFIDENCE_THRESHOLD: float = 0.6  # Proctoring-AI uses 0.6 for object detection
    EYE_GAZE_THRESHOLD: float = 2.0  # seconds before alert
    ALERT_COOLDOWN_SECONDS: int = 3  # Cooldown between alerts
    MAX_FACES_ALLOWED: int = 1  # Only one person allowed during exam

    # Gemini AI for Violation Verification
    GEMINI_API_KEY: str = ""  # Set in .env file
    GEMINI_MODEL: str = "gemini-1.5-flash"  # Fast and cost-effective
    ENABLE_AI_VERIFICATION: bool = False  # Set to True and add GEMINI_API_KEY to enable AI verification
    AI_VERIFICATION_CONFIDENCE_THRESHOLD: float = 0.7  # Only verify if AI is 70%+ confident it's genuine

    # Recording
    ENABLE_RECORDING: bool = False
    RECORDING_PATH: str = "./recordings"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
