from pydantic_settings import BaseSettings,SettingsConfigDict   

class Settings(BaseSettings):
    model_config =SettingsConfigDict(env_file=".env", extra="ignore")


    DB_connection: str
    SECRET_KEY: str
    ALGORITHM: str
    EXP_TIME:int
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

settings=Settings()