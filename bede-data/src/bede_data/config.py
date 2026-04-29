from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlite_db_path: str = "/data/sqlite/bede.db"
    ingest_write_token: str = ""
    timezone: str = "Australia/Sydney"
    owntracks_url: str = "http://owntracks-recorder:8083"
    owntracks_user: str = ""
    owntracks_device: str = ""
    homepage_api_url: str = "http://homepage-api:5000"
    nominatim_url: str = "https://nominatim.openstreetmap.org/reverse"
    bom_location: str = ""
    claude_sessions_dir: str = "/data/bede/claude-sessions"
    host: str = "0.0.0.0"
    port: int = 8001

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
