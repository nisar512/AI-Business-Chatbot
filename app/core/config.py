from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_URL: str 
    ELASTICSEARCH_URL: str
    SELENIUM_REMOTE_URL: str
    JWT_SECRET: str 
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
