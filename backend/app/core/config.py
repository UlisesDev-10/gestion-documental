from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Plataforma de Gestión Documental"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Base de Datos PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gestion_documental_db"

    # Seguridad y Criptografía
    SECRET_KEY: str = "cambiar_esta_clave_secreta_super_segura_en_produccion_1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Concurrencia y Almacenamiento
    DEFAULT_LOCK_TTL_MINUTES: int = 30
    MAX_FILE_SIZE_BYTES: int = 524288000  # 500 MB
    STORAGE_PATH: str = "./storage"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
