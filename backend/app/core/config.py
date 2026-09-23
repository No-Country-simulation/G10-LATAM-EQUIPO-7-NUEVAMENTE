"""Configuración central de BackendAPI.

Las variables se obtienen del entorno y, durante el desarrollo local,
del archivo `.env`.
"""

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración tipada de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicación ---
    PROJECT_NAME: str = "NuevaMente API"
    DESCRIPTION: str = (
        "Backend API de NuevaMente para gestión de documentos "
        "y adaptación educativa asistida por IA."
    )
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal[
        "local",
        "development",
        "staging",
        "production",
    ] = "local"
    DEBUG: bool = True

    # --- API ---
    API_V1_PREFIX: str = "/api/v1"

    # --- Servidor ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- CORS ---
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # --- Documentos / almacenamiento temporal ---
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "storage/uploads"

    # --- Base de datos ---
    DATABASE_URL: str = "sqlite:///storage/nuevamente.db"

    # --- OCI Object Storage ---
    OCI_NAMESPACE: str = ""
    OCI_BUCKET_NAME: str = ""
    OCI_REGION: str = ""
    OCI_CONFIG_FILE: str = "~/.oci/config"
    OCI_CONFIG_PROFILE: str = "DEFAULT"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, value: object) -> object:
        """Acepta una lista JSON o una cadena separada por comas."""
        if not isinstance(value, str):
            return value

        raw = value.strip()

        if raw.startswith("["):
            return json.loads(raw)

        return [
            origin.strip()
            for origin in raw.split(",")
            if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        """Indica si la aplicación se ejecuta en producción."""
        return self.ENVIRONMENT == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        """Convierte el límite de carga configurado de MB a bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def docs_url(self) -> str | None:
        """Deshabilita Swagger en producción."""
        return None if self.is_production else "/docs"


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de configuración por proceso."""
    return Settings()


settings = get_settings()