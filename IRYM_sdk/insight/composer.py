from typing import Optional

class PromptComposer:
    """Builds structured prompts systematically."""
    def build_prompt(self, question: str, docs: list, system_instruction: Optional[str] = None, context: Optional[dict] = None) -> str:
        formatted_docs = []
        for i, doc in enumerate(docs):
            content = doc.get("content", str(doc)) if isinstance(doc, dict) else str(doc)
            source = doc.get("metadata", {}).get("source", "Unknown") if isinstance(doc, dict) else "Unknown"
            formatted_docs.append(f"[Document {i+1}] (Source: {source})\n{content}")
            
        docs_text = "\n\n".join(formatted_docs)
        
        # Extract history from context if present
        history = context.get("history", "") if context else ""
        history_text = f"\nRecent Conversation History:\n{history}\n" if history else ""
        
        # Use provided system instruction or fallback to a default preamble
        preamble = system_instruction or "You are a helpful AI assistant with access to the following context."
        
        return f"""{preamble}
{history_text}
Context Information (Knowledge Base):
---------------------
{docs_text}
---------------------

User Question: {question}

Final Instruction:
1. ONLY use the provided "Context Information" to answer.
2. NUMERICAL LOGIC: When comparing prices, extract the numbers and compare them. (e.g., 21 is LESS than 1000).
3. If the answer is not in the context, state: "I'm sorry, but I don't have this item in our current catalog."
4. If asked to compare and one price is missing, state: "I have the price for [Item A], but not for [Item B], so I cannot compare."
5. DO NOT invent prices for items not in the context (like cars or competitors).
6. Never mention internal IDs, Variants, or Partition numbers.
"""
