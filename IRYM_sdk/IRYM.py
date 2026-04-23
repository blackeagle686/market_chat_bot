from typing import Any
from IRYM_sdk.core.container import container
from IRYM_sdk.core.config import config
from IRYM_sdk.cache.redis_cache import RedisCache
from IRYM_sdk.llm.openai import OpenAILLM
from IRYM_sdk.llm.local import LocalLLM
from IRYM_sdk.vector.chroma import ChromaVectorDB
from IRYM_sdk.vector.qdrant import QdrantVectorDB
from IRYM_sdk.llm.vlm_openai import OpenAIVLM
from IRYM_sdk.llm.vlm_local import LocalVLM
from IRYM_sdk.insight.vlm_pipeline import VLMPipeline
from IRYM_sdk.insight.engine import InsightEngine
from IRYM_sdk.rag.pipeline import RAGPipeline
from IRYM_sdk.training.openai_finetuner import OpenAIFineTuner
from IRYM_sdk.memory.manager import MemoryManager
from IRYM_sdk.audio.local import LocalSTT, LocalTTS
from IRYM_sdk.audio.openai import OpenAISTT, OpenAITTS

def init_irym():
    # 1. Register Cache
    container.register("cache", RedisCache())
    
    # 2. Register LLM Providers (OpenAI only for serverless)
    llm_openai = OpenAILLM()
    container.register("llm_openai", llm_openai)
    container.register("llm", llm_openai)

    # 3. Register Embeddings
    from IRYM_sdk.vector.embeddings import SentenceTransformerEmbeddings
    embeddings = SentenceTransformerEmbeddings()
    container.register("embeddings", embeddings)

    # 4. Register VLM Providers (OpenAI only for serverless)
    vlm_openai = OpenAIVLM()
    container.register("vlm_openai", vlm_openai)
    container.register("vlm", vlm_openai)
    
    # 5. Register Vector DB based on config
    if config.VECTOR_DB_TYPE == "chroma":
        vector_db = ChromaVectorDB(embedding_service=embeddings)
    elif config.VECTOR_DB_TYPE == "qdrant":
        vector_db = QdrantVectorDB()
    else:
        raise ValueError(f"Unsupported vector DB type: {config.VECTOR_DB_TYPE}")
    
    container.register("vector_db", vector_db)

    # 6. Register Fine-Tuning Services
    try:
        from IRYM_sdk.training.local_finetuner import LocalFineTuner
        container.register("finetune_local", LocalFineTuner())
    except Exception:
        # Local fine-tuning is optional and may require torch / transformers.
        container.register("finetune_local", None)
    container.register("finetune_openai", OpenAIFineTuner())

    # 7. Register Memory Manager
    container.register("memory", MemoryManager(container.get("vector_db")))

    # 8. Register Audio Services
    container.register("stt_local", LocalSTT())
    container.register("stt_openai", OpenAISTT())
    container.register("tts_local", LocalTTS())
    container.register("tts_openai", OpenAITTS())

async def startup_irym():
    """
    Asynchronously initializes all services registered in the container.
    This includes Cache connections, Vector DB clients, and LLM pools.
    """
    # 1. Start Cache
    cache = container.get("cache")
    if hasattr(cache, "init"):
        await cache.init()
    
    # 2. Start LLM Provider (OpenAI only)
    llm_openai = container.get("llm_openai")
    if hasattr(llm_openai, "init"):
        await llm_openai.init()
        
    # 3. Start Vector DB
    vector_db = container.get("vector_db")
    if hasattr(vector_db, "init"):
        await vector_db.init()
    
    # 4. Start VLM Providers
    vlm_openai = container.get("vlm_openai")
    # 4. Start VLM Provider (OpenAI only)
    vlm_openai = container.get("vlm_openai")
    if hasattr(vlm_openai, "init"):
        await vlm_openai.init()
    
    # 5. Start Audio Services (OpenAI only)
    for service_name in ["stt_openai", "tts_openai"]:
        service = container.get(service_name)
        if hasattr(service, "init"):
            await service.init()
    
    print("[+] IRYM SDK Services started successfully.")

def get_rag_pipeline(prefer_local: bool = False) -> RAGPipeline:
    vector_db = container.get("vector_db")
    llm_openai = container.get("llm_openai")
    cache = container.get("cache")
    return RAGPipeline(vector_db, primary=llm_openai, fallback=None, cache=cache)

def get_insight_engine(openai_model: str = None, local_model: str = None, prefer_local: bool = True) -> InsightEngine:
    vector_db = container.get("vector_db")
    llm_openai = container.get("llm_openai")
    cache = container.get("cache")
    
    if openai_model:
        llm_openai.model = openai_model
        
    return InsightEngine(vector_db, llm_openai, None, cache)

def get_vlm_pipeline(openai_model: str = None, local_model: str = None, prefer_local: bool = True) -> VLMPipeline:
    vlm_openai = container.get("vlm_openai")
    vector_db = container.get("vector_db")
    cache = container.get("cache")
    
    if openai_model:
        vlm_openai.model = openai_model
    
    return VLMPipeline(vlm_openai, None, vector_db, cache)

def get_finetuner(provider: str = None) -> Any:
    """
    Returns the fine-tuning service based on provider ('local' or 'openai').
    Defaults to config.FINETUNE_PROVIDER.
    """
    provider = provider or config.FINETUNE_PROVIDER
    if provider == "openai":
        return container.get("finetune_openai")

    finetuner = container.get("finetune_local")
    if finetuner is None:
        # Local fine-tuning is optional and may not be available in lightweight deployments
        return container.get("finetune_openai")
    return finetuner

def get_llm() -> Any:
    return container.get("llm")

def get_memory() -> MemoryManager:
    return container.get("memory")

async def init_irym_full():
    """
    Complete initialization:
    1. init_irym (Registry)
    2. startup_irym (Connections)
    3. lifecycle.startup (Hooks)
    """
    from IRYM_sdk.core.lifecycle import lifecycle
    init_irym()
    await startup_irym()
    await lifecycle.startup()
    print("[+] IRYM SDK initialized and lifecycle hooks executed.")


def set_providers(llm_provider: str = None, vlm_provider: str = None) -> None:
    """
    Explicitly configure which provider to use for generic `llm` and `vlm`.

    llm_provider, vlm_provider: one of 'openai', 'local', or 'auto' (default 'auto').
    - 'openai' forces the OpenAI provider (may raise/print warnings if not available).
    - 'local' forces the Local provider.
    - 'auto' (or None) prefers OpenAI when available, otherwise local.

    Call this after `init_irym()` and before `startup_irym()` to customize behaviour.
    """
    # Helper to resolve a provider choice
    def resolve(choice, name_openai, name_local):
        if choice == "openai":
            return container.get(name_openai)
        if choice == "local":
            return container.get(name_local)
        # auto or None
        try:
            openai = container.get(name_openai)
            local = container.get(name_local)
            if hasattr(openai, "is_available") and openai.is_available():
                return openai
            return local
        except Exception:
            return container.get(name_local)

    if llm_provider is not None:
        llm = resolve(llm_provider, "llm_openai", "llm_local")
        container.register("llm", llm)

    if vlm_provider is not None:
        vlm = resolve(vlm_provider, "vlm_openai", "vlm_local")
        container.register("vlm", vlm)


def get_providers() -> dict:
    """Return currently configured generic providers for `llm` and `vlm`."""
    res = {}
    try:
        res["llm"] = container.get("llm")
    except Exception:
        res["llm"] = None
    try:
        res["vlm"] = container.get("vlm")
    except Exception:
        res["vlm"] = None
    return res
