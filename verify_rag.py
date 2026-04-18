import os
import asyncio
from IRYM_sdk import ChatBot
from IRYM_sdk.core.lifecycle import lifecycle

async def test_rag():
    # Set dummy key for testing
    os.environ["OPENAI_API_KEY"] = "sk-dummy"
    
    print("Initializing ChatBot with RAG...")
    bot = (ChatBot(local=True)
           .with_rag("data_set.xlsx")
           .with_system_prompt("You are a supermarket assistant.")
           .build())
    
    # Trigger lazy init
    instance = bot
    await instance._lazy_init()
    
    print("\nQuerying: 'What is the price of Juhayna Milk?'")
    # We use a mocked LLM response if possible or just check if it finds context
    # Since we can't easily mock the LLM inside the SDK without changing code,
    # we'll just check if the RAG pipeline is ready.
    
    rag = instance._rag_pipeline
    if rag:
        print("[+] RAG Pipeline initialized.")
        # Test retrieval only
        results = await rag.vector_db.search("Juhayna Milk", limit=2)
        print(f"[+] Found {len(results)} relevant chunks in data_set.xlsx:")
        for res in results:
            print(f" - {res.payload.get('text', 'No text')[:100]}...")
    else:
        print("[-] RAG Pipeline NOT initialized.")

if __name__ == "__main__":
    asyncio.run(test_rag())
