from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Telegram
    bot_token: str

    # PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "meetbro"
    db_pass: str = "meetbro"
    db_name: str = "meetbro"

    # Redis (None = MemoryStorage fallback)
    redis_url: str | None = None

    # WebApp URL (for Telegram Mini App)
    webapp_url: str | None = None

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
