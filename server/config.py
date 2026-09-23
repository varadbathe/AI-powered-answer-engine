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
    BM25_DIR: str = str(BASE_DIR / "bm25_index")
    RETRIEVAL_MODE: str = "hybrid"
    HYBRID_VECTOR_WEIGHT: float = 0.60
    HYBRID_BM25_WEIGHT: float = 0.40
    HYBRID_VECTOR_CANDIDATE_K: int = 10
    HYBRID_BM25_CANDIDATE_K: int = 10
    HYBRID_FINAL_TOP_K: int = 5
    RAG_RELEVANCE_THRESHOLD: float = 0.0
