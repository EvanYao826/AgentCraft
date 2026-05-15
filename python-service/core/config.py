import os
import logging
from typing import Dict, Any

class ConfigManager:
    """统一配置管理模块"""
    
    def __init__(self):
        """初始化配置管理器"""
        self._load_config()
        self._setup_logging()
    
    def _load_config(self):
        """加载配置项"""
        # AI Embeddings
        self.DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
        # Embedding模型选择: "dashscope" 使用云端API, "local" 使用本地中文模型
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "dashscope")
        # 本地Embedding模型名称（仅当EMBEDDING_MODEL=local时生效）
        self.LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        
        # Milvus Configuration
        self.MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
        self.MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
        self.MILVUS_USER = os.getenv("MILVUS_USER", "")
        self.MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD", "")

        # Redis Configuration
        self.REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
        self.REDIS_DB = int(os.getenv("REDIS_DB", "0"))

        # MySQL Configuration
        self.DB_HOST = os.getenv("MYSQL_HOST", "localhost")
        self.DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
        self.DB_USER = os.getenv("MYSQL_USERNAME", "root")
        self.DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
        self.DB_NAME = os.getenv("MYSQL_DATABASE", "ai_knowledge_db")
        
        # Vector Store Configuration
        self.USE_MILVUS = os.getenv("USE_MILVUS", "true").lower() == "true"
        self.VECTOR_STORE_PERSIST_DIR = os.getenv("VECTOR_STORE_PERSIST_DIR", "./faiss_index")
        self.VECTOR_STORE_COLLECTION_NAME = os.getenv("VECTOR_STORE_COLLECTION_NAME", "ai_knowledge_collection")
        
        # Rerank Configuration
        self.RERANKER_TYPE = os.getenv("RERANKER_TYPE", "simple")
        self.COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
        
        # Text Chunking Configuration
        self.CHUNK_STRATEGY = os.getenv("CHUNK_STRATEGY", "semantic")
        self.CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
        self.CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
        self.MIN_CHUNK_SIZE = int(os.getenv("MIN_CHUNK_SIZE", "100"))
        
        # Tesseract OCR Configuration（默认为空，由 parser.py 自动检测）
        self.TESSERACT_PATH = os.getenv("TESSERACT_PATH", "")
        
        # Temporary Files Configuration
        self.TEMP_DIR = os.getenv("TEMP_DIR", "./temp")
        # 确保临时目录存在
        os.makedirs(self.TEMP_DIR, exist_ok=True)
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # API Configuration
        self.API_HOST = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT = int(os.getenv("API_PORT", "8080"))
        
        # CORS Configuration
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    
    def _setup_logging(self):
        """设置日志配置"""
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Configuration loaded successfully")
    
    def get_config(self) -> Dict[str, Any]:
        """获取所有配置项"""
        return {
            "DASHSCOPE_API_KEY": "***" if self.DASHSCOPE_API_KEY else "",
            "MILVUS_HOST": self.MILVUS_HOST,
            "MILVUS_PORT": self.MILVUS_PORT,
            "USE_MILVUS": self.USE_MILVUS,
            "VECTOR_STORE_PERSIST_DIR": self.VECTOR_STORE_PERSIST_DIR,
            "VECTOR_STORE_COLLECTION_NAME": self.VECTOR_STORE_COLLECTION_NAME,
            "EMBEDDING_MODEL": self.EMBEDDING_MODEL,
            "LOCAL_EMBEDDING_MODEL": self.LOCAL_EMBEDDING_MODEL,
            "RERANKER_TYPE": self.RERANKER_TYPE,
            "CHUNK_STRATEGY": self.CHUNK_STRATEGY,
            "CHUNK_SIZE": self.CHUNK_SIZE,
            "CHUNK_OVERLAP": self.CHUNK_OVERLAP,
            "MIN_CHUNK_SIZE": self.MIN_CHUNK_SIZE,
            "TESSERACT_PATH": self.TESSERACT_PATH,
            "TEMP_DIR": self.TEMP_DIR,
            "LOG_LEVEL": self.LOG_LEVEL,
            "API_HOST": self.API_HOST,
            "API_PORT": self.API_PORT,
            "CORS_ORIGINS": self.CORS_ORIGINS
        }
    
    def validate_config(self) -> bool:
        """验证配置项"""
        is_valid = True
        
        # 验证必要的配置项
        if not self.DASHSCOPE_API_KEY:
            self.logger.warning("DASHSCOPE_API_KEY not set, will use local embeddings")
        
        # 验证Tesseract路径（空值表示由 parser.py 自动检测）
        if self.TESSERACT_PATH and not os.path.exists(self.TESSERACT_PATH):
            self.logger.warning(f"Tesseract not found at {self.TESSERACT_PATH}, will try other locations")
        
        return is_valid

# 创建全局配置实例
config = ConfigManager()
