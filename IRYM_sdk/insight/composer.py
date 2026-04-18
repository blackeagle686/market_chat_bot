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
2. If the answer is not explicitly mentioned in the context, you MUST state: "I'm sorry, but I don't have this item in our current catalog."
3. DO NOT use your own knowledge to invent prices or product availability.
4. Keep the persona of 'MarketAI' consistent.
"""
