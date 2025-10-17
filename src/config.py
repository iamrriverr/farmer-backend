# src/config.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    """系統配置類"""
    
    # ============================================================
    # 系統設定
    # ============================================================
    TITLE = os.getenv("TITLE", "Farmer RAG System")
    VERSION = os.getenv("VERSION", "2.0.0")
    
    # ============================================================
    # JWT 認證設定
    # ============================================================
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # ============================================================
    # OpenAI API 設定（GPT + Embeddings）
    # ============================================================
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # GPT 模型設定
    GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")
    GPT_TEMPERATURE = float(os.getenv("GPT_TEMPERATURE", "0.7"))
    GPT_MAX_TOKENS = int(os.getenv("GPT_MAX_TOKENS", "2000"))
    
    # ============================================================
    # Google Gemini API 設定（備用）
    # ============================================================
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    
    # ============================================================
    # AI 模型選擇
    # ============================================================
    PRIMARY_LLM = os.getenv("PRIMARY_LLM", "gpt")  # 'gpt' 或 'gemini'
    
    # ============================================================
    # PostgreSQL 資料庫設定
    # ============================================================
    PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
    PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    PG_USER = os.getenv("POSTGRES_USER")
    PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    PG_DATABASE = os.getenv("POSTGRES_DB")
    
    # ============================================================
    # Chroma 向量資料庫設定
    # ============================================================
    CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./.chromadb"))
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "farmer_documents")
    
    # ============================================================
    # 🔥 混合搜尋設定（新增）
    # ============================================================
    ENABLE_HYBRID_SEARCH = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
    BM25_WEIGHT = float(os.getenv("BM25_WEIGHT", "0.5"))  # BM25 權重
    VECTOR_WEIGHT = float(os.getenv("VECTOR_WEIGHT", "0.5"))  # 向量權重
    HYBRID_SEARCH_LIMIT = int(os.getenv("HYBRID_SEARCH_LIMIT", "100"))  # 初始載入文件數量
    
    # ============================================================
    # 文件處理設定
    # ============================================================
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
    
    # ============================================================
    # 路徑設定
    # ============================================================
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    UPLOAD_DIR = DATA_DIR / "uploads"
    
    @classmethod
    def validate(cls):
        """驗證必要的配置項"""
        required = {
            "SECRET_KEY": cls.SECRET_KEY,
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
            "PG_USER": cls.PG_USER,
            "PG_PASSWORD": cls.PG_PASSWORD,
            "PG_DATABASE": cls.PG_DATABASE,
        }
        
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"缺少必要的配置: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_model_name(cls):
        """獲取當前使用的模型名稱"""
        if cls.PRIMARY_LLM == "gpt":
            return f"{cls.GPT_MODEL} (OpenAI)"
        else:
            return f"{cls.GEMINI_MODEL} (Google)"
