import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from IRYM_sdk import ChatBot
from IRYM_sdk.core.lifecycle import lifecycle
import uvicorn

app = FastAPI(title="Market AI ChatBot")

# Setup static files and templates
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize ChatBot with OpenAI
api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
bot = (ChatBot(local=False)
       .with_openai(api_key=api_key)
       .with_rag("data_set.xlsx")
       .with_memory()
       .with_system_prompt(
           "You are 'MarketAI', a professional supermarket assistant. "
           "Your goal is to help users find products, check prices, and provide descriptions from the supermarket catalog. "
           "CRITICAL: Always use the 'Price (EGP)' column for prices and the 'Description' column for details. "
           "Do not confuse the 'Partition' or other numeric columns with the price. "
           "Be polite, helpful, and concise. Use supermarket-style language. "
           "If a product is not found, offer to help with something else."
       )
       .build())


@app.on_event("startup")
async def startup_event():
    # The ChatBotInstance handles its own lazy initialization, 
    # but we can trigger it here if we want to ensure everything is ready.
    # For now, we'll let the first request trigger it or just call startup_irym indirectly.
    pass

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(text: str = Form(...), session_id: str = Form("default")):
    response = await bot.set_session(session_id).chat(text)
    return {"answer": response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
