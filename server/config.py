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
   