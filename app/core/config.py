from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_URL: str = "postgresql+asyncpg://user:password@db:5432/dbname"
    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"
    SELENIUM_REMOTE_URL: str = "http://localhost:4444/wd/hub"
    JWT_SECRET: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()