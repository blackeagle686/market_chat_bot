import os
import re
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from IRYM_sdk import ChatBot
from IRYM_sdk.core.lifecycle import lifecycle
import uvicorn
from gtts import gTTS
import uuid

def clean_text_for_speech(text: str) -> str:
    """Removes Markdown symbols so TTS reads only the words and numbers."""
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)
    # Replace markdown table pipes with commas for better speech pausing
    text = text.replace('|', ',')
    # Remove table separator lines (e.g. ---)
    text = re.sub(r'-{2,}', '', text)
    # Remove bold/italic markers
    text = text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
    # Remove header hashes
    text = re.sub(r'#+\s', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

app = FastAPI(title="Market AI ChatBot")

# Setup static files and templates
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize ChatBot with OpenAI
api_key = os.getenv("OPENAI_API_KEY", "ak_2yp3Xw1Ny7ky2pF7er9x93ZO9jj6G")
bot = (ChatBot(local=False)
       .with_openai(api_key=api_key)
       .with_rag("data_set.xlsx")
       .with_system_prompt(
           "You are 'MarketAI'. "
           "Use ONLY the provided context to answer. "
           "Extract prices from 'Price (EGP)'. "
           "Compare numbers directly (e.g., 21 < 30). "
           "If missing, say 'I don't have this item'. "
           "No ID/Variant numbers. "
           "Format your answers beautifully using Markdown. "
           "When listing products, ALWAYS use a Markdown table with columns: Product Name | Price | Partition."
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
    
    # Ensure audio directory exists
    audio_dir = os.path.join("static", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    
    # Generate audio file with unique ID to prevent browser caching
    unique_id = uuid.uuid4().hex[:8]
    audio_filename = f"response_{session_id}_{unique_id}.mp3"
    audio_path = os.path.join(audio_dir, audio_filename)
    
    try:
        clean_audio_text = clean_text_for_speech(response)
        tts = gTTS(text=clean_audio_text, lang='en')
        tts.save(audio_path)
        return {"answer": response, "audio": f"/static/audio/{audio_filename}"}
    except Exception as e:
        print(f"TTS Error: {e}")
        return {"answer": response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
