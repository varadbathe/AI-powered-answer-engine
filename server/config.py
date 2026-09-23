from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings): 
    # Settings class used to access configuration from environment or defaults
    TAVILY_API_KEY: str = "your_tavily_api_key"
    GEMINI_API_KEY: str = "your_gemini_api_key"
    DATABASE_PATH: str = str(BASE_DIR / "conversations.db")
    CHROMA_DIR: str = str(BASE_DIR / "chroma_db")
    UPLOADS_DIR: str = str(BASE_DIR / "uploads")
    DEFAULT_CHUNK_SIZE: int = 600
    DEFAULT_CHUNK_OVERLAP: int = 120
    MAX_FILE_SIZE_MB: int = 50
    RAG_DEBUG: bool = False