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

Final Instructions:
SEARCH RULE: Match the user's question to products in the context above, even if the question uses words like "Variant", a number, or a brand name. Use ALL fields in the context (name, variant, category, price) to find the right product.
ANSWER RULE 1: ONLY use the provided "Context Information" to answer.
ANSWER RULE 2: NUMERICAL LOGIC: When comparing prices, extract the numbers and compare them (e.g., 21 < 1000).
ANSWER RULE 3: If the product truly does not appear anywhere in the context, say exactly: "I don't have this item".
ANSWER RULE 4: If asked to compare and one price is missing, say: "I have the price for [Item A], but not for [Item B], so I cannot compare."
ANSWER RULE 5: DO NOT invent prices for items not found in the context.
FORMAT RULE: In your answer, do NOT show raw variant numbers, SKU IDs, or partition numbers — only show the product name and price.
"""
