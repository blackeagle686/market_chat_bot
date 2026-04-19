import os
import re
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from IRYM_sdk import ChatBot
from IRYM_sdk.core.lifecycle import lifecycle
import uvicorn
from gtts import gTTS
import uuid

def clean_text_for_speech(text: str) -> str:
    """Removes Markdown symbols so TTS reads only the words and numbers."""
    # Replace EGP with pounds for better TTS pronunciation
    text = re.sub(r'\bEGP\b', 'pounds', text)
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

# Initialize ChatBot with LongCat (OpenAI-compatible)
api_key = os.getenv("OPENAI_API_KEY", "ak_2yp3Xw1Ny7ky2pF7er9x93ZO9jj6G")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.longcat.chat/openai")
bot = (ChatBot(local=False)
       .with_openai(api_key=api_key, base_url=base_url)
       .with_rag("final_rag_dataset.xlsx")
       .with_memory()
       .with_system_prompt(
           "You are 'MarketAI', an intelligent question-answering assistant for a supermarket. "
           "Follow these rules strictly:\n"
           "1. For simple greetings ONLY (e.g., 'hello', 'hi', 'thanks'), respond politely and briefly.\n"
           "2. Treat ALL other inputs (like 'Nestle', 'ice cream', 'Obour Land', 'KitKat Variant 16') as product search queries. Do NOT greet the user if they type a product name.\n"
           "3. If the user asks for a description of a product, provide the product's description clearly.\n"
           "4. If the user asks general questions like 'where is meat' or 'is there any fish', provide a helpful answer using Markdown.\n"
           "5. Use ONLY the provided context for product details. If an item is truly missing from the context, say exactly: 'I don't have this item'. Do not apologize or add extra text.\n"
           "6. Extract prices from 'Price (EGP)' and compare numbers directly (e.g., 21 < 30).\n"
           "7. SEARCH using all context fields (Product Name, Variant, Category, Price). When searching for 'KitKat Variant 16', find the row where Variant=16 and the product name contains KitKat.\n"
           "8. In your ANSWER, do NOT show raw variant numbers, SKU IDs, or partition numbers — only show the product name and price.\n"
           "9. Format ALL your answers beautifully using Markdown. "
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

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """
    STT endpoint using Google SpeechRecognition API (Free).
    Converts uploaded WebM from browser to WAV, then extracts text.
    """
    import tempfile
    import subprocess
    
    try:
        import speech_recognition as sr
    except ImportError:
        print("[Transcribe] speech_recognition not installed. Please run: pip install SpeechRecognition")
        return JSONResponse({"text": "", "error": "SpeechRecognition library missing"}, status_code=500)

    audio_bytes = await audio.read()

    # Save WebM locally
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as webm_tmp:
        webm_tmp.write(audio_bytes)
        webm_path = webm_tmp.name
        
    wav_path = webm_path.replace(".webm", ".wav")

    try:
        # Convert WebM to WAV via ffmpeg
        subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path, wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        text = ""
        # Try Arabic first
        try:
            text = recognizer.recognize_google(audio_data, language="ar-EG")
        except sr.UnknownValueError:
            # Fallback to English
            try:
                text = recognizer.recognize_google(audio_data, language="en-US")
            except sr.UnknownValueError:
                text = ""

        return JSONResponse({"text": text})

    except Exception as e:
        print(f"[Transcribe] Error: {e}")
        return JSONResponse({"text": "", "error": str(e)}, status_code=500)
    finally:
        if os.path.exists(webm_path):
            os.unlink(webm_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
