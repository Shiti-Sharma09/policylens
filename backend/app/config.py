from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "local"
    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen3:8b"
    OLLAMA_EMBEDDING_MODEL: str = "qwen3-embedding:0.6b"
    EMBEDDING_DIMENSION: int = 1024  # measured via /api/embed on Day 1 - see suggestions.md
    OLLAMA_THINK: bool = False  # Qwen3 thinking mode: 27+ min/answer if left on, ~20s if off
    QDRANT_LOCAL_PATH: str = "./qdrant_data"
    DATABASE_URL: str = "sqlite:///./policylens.db"

    class Config:
        env_file = ".env"


settings = Settings()
