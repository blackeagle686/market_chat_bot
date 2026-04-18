import os
import uvicorn
from pyngrok import ngrok
import nest_asyncio
from main import app

# Check for Ngrok Auth Token
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
if NGROK_AUTH_TOKEN:
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
else:
    print("WARNING: NGROK_AUTH_TOKEN not found. Public URL might not work if token is required.")

# Set OpenAI API Key if provided
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not found. ChatBot might fail.")

# Colab needs nest_asyncio to run uvicorn in the same loop
nest_asyncio.apply()

def run():
    # Connect to ngrok
    public_url = ngrok.connect(8000)
    print(f" * MarketAI is running at: {public_url}")
    
    # Run Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run()
