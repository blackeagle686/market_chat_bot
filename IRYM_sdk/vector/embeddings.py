from abc import ABC, abstractmethod
from typing import List
import numpy as np
from IRYM_sdk.core.config import config

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class BaseEmbeddings(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass

class OpenAIEmbeddings(BaseEmbeddings):
    _client = None

    def __init__(self, model_name: str = None):
        if OpenAI is None:
            raise ImportError(
                "openai is not installed. Please install it using: pip install openai"
            )

        self.model_name = model_name or config.EMBEDDING_MODEL or "text-embedding-3-small"
        if OpenAIEmbeddings._client is None:
            OpenAIEmbeddings._client = OpenAI(
                api_key=getattr(config, "OPENAI_API_KEY", None),
                base_url=getattr(config, "OPENAI_BASE_URL", None) or None,
            )
        self.client = OpenAIEmbeddings._client

    def _embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(model=self.model_name, input=texts)
        return [item.embedding for item in response.data]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]

class SentenceTransformerEmbeddings(BaseEmbeddings):
    _model_cache = {}

    def __init__(self, model_name: str = None):
        model_to_use = model_name or config.EMBEDDING_MODEL
        
        if model_to_use not in SentenceTransformerEmbeddings._model_cache:
            if SentenceTransformer is None:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    "Please install it using: pip install sentence-transformers"
                )
            print(f"[*] Initializing Embedding Model: {model_to_use}...")
            SentenceTransformerEmbeddings._model_cache[model_to_use] = SentenceTransformer(model_to_use)
            print(f"[+] Embedding Model Loaded into cache.")
        
        self.model = SentenceTransformerEmbeddings._model_cache[model_to_use]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode([text])[0]
        return embedding.tolist()
