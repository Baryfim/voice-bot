from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    
    OPENAI_API_TOKEN: str
    OPENAI_MODEL: str
    
    ASSISTANT_INSTRUCTIONS: str
    ASSISTANT_NAME: str
    
    WHISPER_MODEL: str

    OPENAI_TTS_MODEL: str
    OPENAI_TTS_VOICE: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()