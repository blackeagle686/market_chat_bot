from typing import List, Optional


class VectorRetriever:
    """
    Multi-step retrieval with graceful fallback:
      Step 1 — Semantic search with the primary (possibly optimised) query.
      Step 2 — Semantic search with each query variant (if step 1 returns poor results).
      Step 3 — Keyword / substring search (if the vector store supports it).
    """

    # If the best semantic result has a distance above this, treat it as a miss
    # and try the fallback steps.
    POOR_MATCH_THRESHOLD = 0.9

    def __init__(self, vector_db):
        self.vector_db = vector_db

    # ------------------------------------------------------------------ #
    #  Public interface                                                    #
    # ------------------------------------------------------------------ #

    async def retrieve(self, question: str, limit: int = 10) -> List[dict]:
        """Simple semantic retrieval (kept for backwards compatibility)."""
        return await self.vector_db.search(question, limit=limit)

    async def retrieve_with_fallback(
        self,
        primary_query: str,
        variants: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[dict]:
        """
        Multi-step retrieval pipeline.

        1. Semantic search with primary_query.
        2. If results are poor, try each variant query and merge.
        3. If still poor, try keyword search (if supported by vector DB).
        """
        # --- Step 1: Primary semantic search ---
        docs = await self.vector_db.search(primary_query, limit=limit)
        if self._results_are_good(docs):
            return docs

        # --- Step 2: Try query variants ---
        if variants:
            merged = {d["id"]: d for d in docs}  # deduplicate by id
            for variant in variants:
                if variant == primary_query:
                    continue
                variant_docs = await self.vector_db.search(variant, limit=limit)
                for d in variant_docs:
                    doc_id = d.get("id", d.get("content", "")[:40])
                    if doc_id not in merged:
                        merged[doc_id] = d
                if self._results_are_good(list(merged.values())):
                    break  # good enough — stop early

            combined = list(merged.values())
            if self._results_are_good(combined):
                return combined

            # Use merged even if not "good" — it's better than nothing
            docs = combined

        # --- Step 3: Keyword / substring fallback ---
        if hasattr(self.vector_db, "search_by_keyword"):
            keyword = primary_query.strip()
            kw_docs = await self.vector_db.search_by_keyword(keyword, limit=limit)
            if kw_docs:
                # Merge keyword results with semantic results
                existing_ids = {d.get("id", d.get("content", "")[:40]) for d in docs}
                for d in kw_docs:
                    doc_id = d.get("id", d.get("content", "")[:40])
                    if doc_id not in existing_ids:
                        docs.append(d)
                        existing_ids.add(doc_id)

        return docs

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _results_are_good(self, docs: List[dict]) -> bool:
        """Returns True if at least one result has a distance below the threshold."""
        if not docs:
            return False
        best_distance = min(
            (d.get("distance", 9999) for d in docs if isinstance(d, dict)),
            default=9999,
        )
        return best_distance <= self.POOR_MATCH_THRESHOLD
