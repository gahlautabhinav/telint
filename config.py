from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_id: int
    api_hash: str
    phone: str
    session_name: str = "telint"
    db_path: str = "telint.db"
    monitor_interval_hours: int = 6
    reaction_posts_limit: int = 100
    message_scrape_limit: int = 200
    rate_limit_delay: float = 1.0

    class Config:
        env_file = ".env"

settings = Settings()
