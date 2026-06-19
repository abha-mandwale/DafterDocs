from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'DafterDocs'
    app_env: str = 'development'
    debug: bool = True

    api_prefix: str = '/api'
    cors_origins: list[str] = Field(default_factory=lambda: ['*'])

    jwt_secret_key: str = 'change-this-in-production'
    jwt_algorithm: str = 'HS256'
    jwt_exp_minutes: int = 60 * 24

    database_url: str = 'postgresql+psycopg://postgres:postgres@localhost:5432/dafterdocs'

    storage_dir: str = 'storage'
    upload_dir_name: str = 'uploads'
    export_dir_name: str = 'exports'

    processing_step_delay_seconds: float = 0.8
    ocr_languages: str = 'hin+eng'
    ocr_render_scale: float = 2.0
    ocr_max_pages: int = 25
    ocr_tesseract_config: str = '--oem 1 --psm 6'
    tesseract_cmd: Optional[str] = None
    pdf_font_path: Optional[str] = None

    openai_api_key: Optional[str] = None
    openai_model: str = 'gpt-4o-mini'

    @property
    def upload_dir(self) -> Path:
        return Path(self.storage_dir) / self.upload_dir_name

    @property
    def export_dir(self) -> Path:
        return Path(self.storage_dir) / self.export_dir_name


@lru_cache
def get_settings() -> Settings:
    return Settings()
