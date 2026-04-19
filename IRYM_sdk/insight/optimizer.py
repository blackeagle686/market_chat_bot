import re
import unicodedata
from typing import List


class Optimizer:
    """Handles query normalization, variant generation, reranking, and distance filtering."""

    # Maximum cosine distance to accept a result (lower = more similar in Chroma)
    DISTANCE_THRESHOLD = 1.2  # Chroma returns L2 distances; 1.2 is a generous but sane cutoff

    # ------------------------------------------------------------------ #
    #  Text Normalization                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizes text for robust matching:
        - Strips whitespace
        - Lowercases
        - Removes Arabic diacritics (tashkeel)
        - Normalizes common Arabic letter variants (أ إ آ → ا, ة → ه, ى → ي)
        - Collapses multiple spaces
        """
        if not text:
            return ""

        text = text.strip().lower()

        # Remove Arabic diacritics (harakat / tashkeel)
        arabic_diacritics = re.compile(
            r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]'
        )
        text = arabic_diacritics.sub('', text)

        # Normalize Arabic letter variants
        text = re.sub(r'[أإآا]', 'ا', text)   # Alef variants → plain Alef
        text = text.replace('ة', 'ه')           # Taa marbuta → Haa
        text = text.replace('ى', 'ي')           # Alef maqsura → Yaa

        # Normalize unicode (e.g. accented Latin letters)
        text = unicodedata.normalize('NFKC', text)

        # Collapse extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    # ------------------------------------------------------------------ #
    #  Query Rewriting                                                     #
    # ------------------------------------------------------------------ #

    def rewrite_query(self, query: str) -> str:
        """Light cleaning for the primary semantic search query."""
        if not query:
            return ""
        return query.strip()

    def get_query_variants(self, query: str) -> List[str]:
        """
        Returns a deduplicated list of query variants to maximise recall:
          1. Original (stripped)
          2. Lowercased
          3. Normalized (Arabic + unicode)
          4. No-space version (handles 'ObourLand' vs 'Obour Land')
          5. Each individual word (for partial / brand matching)
        """
        variants = []
        original = query.strip()

        if not original:
            return variants

        candidates = [
            original,
            original.lower(),
            self.normalize_text(original),
            original.replace(' ', '').lower(),
        ]

        # Add individual words that are long enough to be meaningful
        words = [w for w in re.split(r'\s+', original) if len(w) >= 3]
        candidates.extend(words)

        # Deduplicate while preserving order
        seen = set()
        for c in candidates:
            if c and c not in seen:
                seen.add(c)
                variants.append(c)

        return variants

    # ------------------------------------------------------------------ #
    #  Reranking & Filtering                                               #
    # ------------------------------------------------------------------ #

    def rerank(self, docs: list, query: str) -> list:
        """
        Sorts retrieved documents by ascending distance (closer = better),
        then filters out anything beyond DISTANCE_THRESHOLD.
        Falls back to returning all docs if none pass the threshold (let the
        engine decide what to do with low-confidence results).
        """
        if not docs:
            return docs

        if isinstance(docs[0], dict) and "distance" in docs[0]:
            docs = sorted(docs, key=lambda x: x.get("distance", 9999))
            # Filter by threshold; keep all if every result is above threshold
            filtered = [d for d in docs if d.get("distance", 9999) <= self.DISTANCE_THRESHOLD]
            return filtered if filtered else docs  # graceful fallback

        return docs
