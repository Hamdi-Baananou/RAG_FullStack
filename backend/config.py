from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any, List
from pathlib import Path

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Document Processing API"
    
    # API Keys
    GROQ_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    HF_TOKEN: Optional[str] = None
    
    # LLM Configuration
    LLM_MODEL_NAME: str = "qwen-qwq-32b"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_OUTPUT_TOKENS: int = 31550
    
    # Vision Model Configuration
    VISION_MODEL_NAME: str = "mistral-small-latest"
    
    # Embedding Configuration
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"
    NORMALIZE_EMBEDDINGS: bool = True
    EMBEDDING_CACHE_DIR: Optional[str] = None
    
    # Vector Store Configuration
    CHROMA_PERSIST_DIRECTORY: Optional[str] = "./chroma_db_prod"
    COLLECTION_NAME: str = "pdf_qa_prod_collection"
    
    # Text Processing Configuration
    CHUNK_SIZE: int = 5000
    CHUNK_OVERLAP: int = 75
    RETRIEVER_K: int = 4
    
    # Health Check Configuration
    HEALTH_CHECK_TIMEOUT: int = 300  # 5 minutes
    HEALTH_CHECK_INTERVAL: int = 30  # 30 seconds
    HEALTH_CHECK_GRACE_PERIOD: int = 60  # 1 minute
    
    # Processing Configuration
    MAX_PARALLEL_ATTRIBUTES: int = 4
    ATTRIBUTE_CHUNK_SIZE: int = 1000
    
    # PDF Processing Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {"pdf"}
    
    # Web Scraping Configuration
    SUPPLIER_URLS: List[str] = [
        "https://www.te.com/usa-en/product-{part_number}.html",
        "https://www.molex.com/molex/products/part-detail/{part_number}",
        # Add more supplier URLs as needed
    ]
    SCRAPING_TIMEOUT: int = 5000  # 5 seconds
    SCRAPING_RETRIES: int = 3
    SCRAPING_DELAY: float = 1.0  # 1 second between retries
    
    # Extraction Configuration
    EXTRACTION_TIMEOUT: int = 30  # 30 seconds per extraction
    EXTRACTION_RETRIES: int = 2
    EXTRACTION_DELAY: float = 0.5  # 0.5 seconds between retries
    
    # Metrics Configuration
    METRICS_PRECISION: int = 2  # Decimal places for metrics
    METRICS_THRESHOLD: float = 0.8  # Success threshold (80%)
    
    @property
    def is_persistent(self) -> bool:
        """Check if vector store is persistent."""
        return bool(self.CHROMA_PERSIST_DIRECTORY)
    
    @property
    def chroma_settings(self) -> Dict[str, Any]:
        """Get Chroma settings dictionary."""
        return {
            "is_persistent": self.is_persistent,
            "persist_directory": self.CHROMA_PERSIST_DIRECTORY,
            "collection_name": self.COLLECTION_NAME
        }
    
    def validate_settings(self) -> None:
        """Validate critical settings."""
        if not self.GROQ_API_KEY:
            print("Warning: GROQ_API_KEY not found in environment variables.")
        if not self.MISTRAL_API_KEY:
            print("Warning: MISTRAL_API_KEY not found in environment variables.")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.validate_settings()
    return settings 