import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

class Config:
    # Database Config
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "hanoi_osm")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # LLM Config
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://171.232.252.238:8080/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.5-122B-A10B")
    LLM_EMBEDDING_MODEL = os.getenv("LLM_EMBEDDING_MODEL", "Qwen3-Embedding-4B")
