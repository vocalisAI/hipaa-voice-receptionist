import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ACS_CONNECTION_STRING: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_KEY: str
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str
    
    # Callback URI - To be determined by deployment, but good to have a placeholder or env var
    # ACS requires a public callback URI. In App Service, this is usually https://<app-name>.azurewebsites.net/api/callbacks
    CALLBACK_URI_HOST: str = "" # Optional, can be derived or set manually

    class Config:
        case_sensitive = True
        # If .env file is present (local dev), load it.
        env_file = ".env"

try:
    settings = Settings()
except Exception as e:
    print(f"CRITICAL: Missing required environment variables. {e}")
    # We might want to just let it crash, or handle it gracefully in main.py
    # Re-raising ensures fail-fast behavior on startup.
    raise
