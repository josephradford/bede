from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bede_data_url: str = "http://bede-data:8001"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
