from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved relative to this file (backend/app/config.py -> backend/.env),
# not the process's current working directory — launchers (uvicorn, the
# bot, this repo's own preview tooling) don't all start from the same cwd.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str
    telegram_bot_token: str
    secret_key: str


settings = Settings()
