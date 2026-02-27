from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 3038

    # Environment
    env_name: str = "LOCAL"
    log_level: str = "INFO"

    # Own database (read/write) — all analytics data
    stats_mongodb_url: str = "mongodb://localhost:27017"
    stats_mongodb_database: str = "stats-db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
