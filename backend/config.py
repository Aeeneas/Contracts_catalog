import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DADATA_API_KEY: str = os.getenv("DADATA_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    HTTP_PROXY: str = os.getenv("HTTP_PROXY", "")
    HTTPS_PROXY: str = os.getenv("HTTPS_PROXY", "")

settings = Settings()
