from typing import Optional

class PromptComposer:
    """Builds structured prompts systematically."""
    def build_prompt(self, question: str, docs: list, system_instruction: Optional[str] = None) -> str:
        formatted_docs = []
        for i, doc in enumerate(docs):
            content = doc.get("content", str(doc)) if isinstance(doc, dict) else str(doc)
            source = doc.get("metadata", {}).get("source", "Unknown") if isinstance(doc, dict) else "Unknown"
            formatted_docs.append(f"[Document {i+1}] (Source: {source})\n{content}")
            
        context = "\n\n".join(formatted_docs)
        
        # Use provided system instruction or fallback to a default preamble
        preamble = system_instruction or "You are a helpful AI assistant with access to the following context."
        
        return f"""{preamble}

Context Information:
---------------------
{context}
---------------------

User Question: {question}

Final Instruction: Answer the question precisely using the provided context. If the answer is not in the context, be honest but helpful.
"""
