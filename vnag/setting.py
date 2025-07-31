from typing import Any

from .utility import load_json


# RAG系统默认配置
SETTINGS: dict[str, Any] = {
    "llm.base_url": "https://api.openai.com/v1",
    "llm.api_key": "",
    "llm.model": "gpt-3.5-turbo",
    "llm.max_tokens": 2000,
    "llm.temperature": 0.7,
    
    "embedding.model_name": "BAAI/bge-large-zh-v1.5", 
    "embedding.device": "cpu",
    
    "vector_store.persist_directory": "chroma_db",
    
    "document.chunk_size": 1000,
    "document.chunk_overlap": 200,
    "document.supported_formats": [".md", ".txt", ".pdf", ".docx"],
    
    "token.max_tokens": 2000,
    "token.warning_threshold": 0.8,
}

SETTING_FILENAME: str = "rag_config.json"
SETTINGS.update(load_json(SETTING_FILENAME))