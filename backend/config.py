from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = f'sqlite:///{ROOT / "traceback.db"}'
    upload_dir: Path = ROOT / 'backend' / 'uploads'
    demo_data_dir: Path = ROOT / 'demo_data'
    jwt_secret: str = ''
    openai_api_key: str = ''
    ai_model: str = 'gpt-4.1-mini'
    ai_provider: str = 'openai'
    ai_base_url: str | None = None
    ai_mode: Literal['demo', 'live'] = 'demo'
    environment: Literal['development', 'test', 'production'] = 'development'
    auth_rate_limit: int = 30
    frontend_dist: Path = ROOT / 'frontend' / 'dist'
    serve_frontend: bool = False
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    model_config = SettingsConfigDict(env_file=str(ROOT / '.env'), extra='ignore')

    @model_validator(mode='after')
    def production_safety(self):
        if self.jwt_secret and len(self.jwt_secret) < 32:
            raise ValueError('JWT_SECRET must contain at least 32 characters')
        if self.environment == 'production' and not self.jwt_secret:
            raise ValueError(
                'Production requires a persistent JWT_SECRET of at least 32 characters'
            )
        if self.environment == 'production' and '*' in self.cors_origins:
            raise ValueError('Production requires explicit CORS origins')
        return self


settings = Settings()
