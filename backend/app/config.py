from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Anthropic LLM
    anthropic_auth_token: str = ""
    anthropic_base_url: str = "https://ai-api-gateway.app.baizhi.cloud/api/anthropic"
    anthropic_model: str = "deepseek-v4-pro"

    # Embedding
    embedding_model: str = "BAAI/bge-large-zh-v1.5"

    # JWT
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # Upload
    upload_dir: str = "./data/uploads"

    # Tesseract OCR executable (empty = auto-detect)
    tesseract_cmd: str = ""

    def normalized_upload_dir(self) -> str:
        return os.path.abspath(self.upload_dir)

    def normalized_chroma_dir(self) -> str:
        return os.path.abspath(self.chroma_persist_dir)

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
