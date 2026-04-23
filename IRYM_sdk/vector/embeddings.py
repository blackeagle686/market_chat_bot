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

        self.model_name = model_name or config.EMBEDDING_MODEL or "nvidia/llama-nemotron-embed-vl-1b-v2:free"
        if OpenAIEmbeddings._client is None:
            OpenAIEmbeddings._client = OpenAI(
                api_key="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",
                base_url="https://openrouter.ai/api/v1",
            )
        self.client = OpenAIEmbeddings._client

    def _embed(self, texts: List[str]) -> List[List[float]]:
        # OpenRouter free models have strict rate limits and batch size limits.
        # Process in smaller batches and use standard text input instead of multimodal.
        batch_size = 10
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-OpenRouter-Title": "MarketChatBot",
                },
                model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
                input=batch,
                encoding_format="float"
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings

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
