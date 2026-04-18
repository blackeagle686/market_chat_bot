class VectorRetriever:
    """Handles vector DB abstractions for the Insight layer."""
    def __init__(self, vector_db):
        self.vector_db = vector_db

    async def retrieve(self, question: str, limit: int = 10):
        return await self.vector_db.search(question, limit=limit)
