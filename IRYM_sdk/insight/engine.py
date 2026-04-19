from IRYM_sdk.insight.base import BaseInsightService
from IRYM_sdk.insight.retriever import VectorRetriever
from IRYM_sdk.insight.composer import PromptComposer
from IRYM_sdk.insight.optimizer import Optimizer
from typing import Optional
from IRYM_sdk.core.utils import async_confirm
from IRYM_sdk.observability.logger import get_logger

logger = get_logger("IRYM.Insight")

class InsightEngine(BaseInsightService):
    """
    Main orchestration layer.
    Manages vector retrieval, prompt building, LLM generation, and cache checking.

    Retrieval strategy (in order):
      1. Semantic search with optimized query.
      2. Semantic search with query variants (normalized, lowercased, word-split).
      3. Keyword / substring fallback search.
    """
    def __init__(self, vector_db, primary, fallback, cache=None):
        self.vector_db = vector_db
        self.primary = primary
        self.fallback = fallback
        self.cache = cache
        
        self.retriever = VectorRetriever(vector_db)
        self.composer = PromptComposer()
        self.optimizer = Optimizer()

    async def init(self):
        pass

    async def query(self, question: str, context: Optional[dict] = None, system_instruction: Optional[str] = None):
        optimized_query = self.optimizer.rewrite_query(question)
        if optimized_query != question:
            logger.info(f"Query optimized: {question} -> {optimized_query}")

        # 0. Provider selection
        provider = self.primary
        if hasattr(provider, "is_available") and not provider.is_available():
            confirmed = await async_confirm("Primary LLM provider is unavailable. Switch to Fallback?")
            if not confirmed:
                return "Operation cancelled by user: Primary unavailable and Fallback rejected."
            provider = self.fallback

        # 1. Cache check (fast path)
        cache_key = f"insight:{optimized_query}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Insight Cache Hit for key: {cache_key}")
                return cached
            logger.info(f"Insight Cache Miss for key: {cache_key}")

        # 2. Multi-step retrieval
        logger.info(f"Retrieving Knowledge for: {optimized_query[:60]}...")
        variants = self.optimizer.get_query_variants(optimized_query)
        docs = await self.retriever.retrieve_with_fallback(
            primary_query=optimized_query,
            variants=variants,
            limit=10,
        )

        # 3. Rerank & threshold filter
        if docs:
            logger.info(f"Retrieved {len(docs)} documents. Reranking...")
            docs = self.optimizer.rerank(docs, optimized_query)

        if docs:
            logger.info(f"Using {len(docs)} documents for context (best distance: {docs[0].get('distance', '?'):.3f})")
        else:
            logger.warning("No documents retrieved — proceeding with empty context.")

        # 4. Prompt construction
        prompt = self.composer.build_prompt(
            optimized_query, docs,
            system_instruction=system_instruction,
            context=context,
        )

        # 5. LLM Generation (with runtime fallback)
        try:
            response = await provider.generate(prompt)
        except Exception as e:
            logger.error(f"LLM provider failed: {e}")
            if provider == self.primary:
                confirmed = await async_confirm(f"Primary LLM failed ({e}). Switch to Fallback for this request?")
                if confirmed:
                    if hasattr(self.fallback, "is_available") and not self.fallback.is_available():
                        return "Error: Secondary provider is not configured. Cannot fallback."
                    logger.info("Retrying with secondary provider...")
                    try:
                        response = await self.fallback.generate(prompt)
                    except Exception as fallback_e:
                        return f"Error: Both primary and fallback providers failed.\nPrimary: {e}\nFallback: {fallback_e}"
                else:
                    return f"Error: Primary LLM failed and fallback was rejected. Details: {e}"
            else:
                raise e

        # 6. Cache response
        if self.cache:
            await self.cache.set(cache_key, response, ttl=300)

        return response
