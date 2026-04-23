import os
import re
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from IRYM_sdk import ChatBot
from IRYM_sdk.core.lifecycle import lifecycle
import uvicorn
from gtts import gTTS
import uuid
from sqlalchemy.orm import Session
from database import SessionLocal, Category, Product, init_db
from fastapi.responses import RedirectResponse

def clean_text_for_speech(text: str) -> str:
    """Removes Markdown symbols so TTS reads only the words and numbers."""
    # Remove the table header row
    text = re.sub(r'^\|?\s*Product Name\s*\|.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Replace EGP with pounds for better TTS pronunciation
    text = re.sub(r'\bEGP\b', 'pounds', text)
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove table separator lines (e.g. |---|---|)
    text = re.sub(r'^\|?\s*(?:-+\s*\|?)+\s*$', '', text, flags=re.MULTILINE)
    # Just in case there are standalone ---
    text = re.sub(r'-{2,}', '', text)
    
    # Replace markdown table pipes with commas for better speech pausing
    text = text.replace('|', ',')
    
    # Remove bold/italic markers
    text = text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
    # Remove header hashes
    text = re.sub(r'#+\s', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove leading/trailing/multiple commas that might be left over from empty table cells
    text = re.sub(r',\s*,', ',', text)
    text = text.strip(' ,')
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
bot = (ChatBot(local=False, vlm=False)
       .with_openai(api_key=api_key, base_url=base_url)
       .with_rag("data_set.xlsx")
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

# Global product catalog for fuzzy matching
PRODUCT_CATALOG = set()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    init_db() # Ensure tables are created
    global PRODUCT_CATALOG
    try:
        import pandas as pd
        # Load from Excel if RAG dataset exists (keep existing functionality)
        if os.path.exists("final_rag_dataset.xlsx"):
            df = pd.read_excel("final_rag_dataset.xlsx")
            if "Product Name" in df.columns:
                unique_products = df["Product Name"].dropna().unique().tolist()
                PRODUCT_CATALOG = {str(p).lower().strip() for p in unique_products}
                print(f"[+] Loaded {len(PRODUCT_CATALOG)} unique products into fuzzy matching catalog.")
        
        load_stt_corrections()
    except Exception as e:
        print(f"[-] Startup error: {e}")

# --- New Market Catalog Routes ---

@app.get("/catalog", response_class=HTMLResponse)
async def view_catalog(request: Request, db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return templates.TemplateResponse("catalog.html", {"request": request, "categories": categories})

@app.get("/category/{category_id}", response_class=HTMLResponse)
async def view_category(request: Request, category_id: int, q: str = None, page: int = 1, db: Session = Depends(get_db)):
    limit = 12
    offset = (page - 1) * limit
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        return RedirectResponse(url="/catalog")
    
    query = db.query(Product).filter(Product.category_id == category_id)
    if q:
        query = query.filter(Product.name.contains(q))
    
    total_products = query.count()
    products = query.offset(offset).limit(limit).all()
    total_pages = (total_products + limit - 1) // limit
    
    return templates.TemplateResponse("category_products.html", {
        "request": request,
        "category": category,
        "products": products,
        "page": page,
        "total_pages": total_pages,
        "query": q
    })

@app.get("/search", response_class=HTMLResponse)
async def global_search(request: Request, q: str, page: int = 1, db: Session = Depends(get_db)):
    limit = 12
    offset = (page - 1) * limit
    
    query = db.query(Product).filter(Product.name.contains(q))
    total_products = query.count()
    products = query.offset(offset).limit(limit).all()
    total_pages = (total_products + limit - 1) // limit
    
    return templates.TemplateResponse("category_products.html", {
        "request": request,
        "category": {"name": f"Search Results for '{q}'", "id": 0}, # Pseudo-category for template
        "products": products,
        "page": page,
        "total_pages": total_pages,
        "query": q,
        "is_search": True
    })

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    # Redirect to catalog as the new landing page, or keep original index
    return templates.TemplateResponse("index.html", {"request": request})

# --- Rest of the existing code (chat, transcribe, etc.) ---

def load_stt_corrections() -> dict:
    import json
    filepath = "stt_corrections.json"
    if not os.path.exists(filepath):
        default_corrections = {
            "overland": "obour land",
            "over land": "obour land",
            "obor land": "obour land",
            "football land": "obour land",
            "footbal land": "obour land",
            "foot ball land": "obour land",
            "donky": "domty",
            "donkey": "domty",
            "dom t": "domty",
            "jihaina": "juhayna",
            "johaina": "juhayna",
            "joe haina": "juhayna",
            "edita": "edita",
            "lamar": "lamar",
            "beyti": "beyti",
            "baity": "beyti"
        }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(default_corrections, f, indent=4)
        except Exception:
            pass
        return default_corrections
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[-] Failed to load {filepath}: {e}")
        return {}

def apply_query_corrections(query: str) -> str:
    """Fix common STT mishearings using an external JSON file and apply fuzzy matching."""
    query_lower = query.lower()
    
    corrections = load_stt_corrections()
    
    # Step 1: Dictionary replacements
    words = query_lower.split()
    # Also check multi-word phrases by doing a simple string replace
    for wrong, right in corrections.items():
        import re
        pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
        query_lower = pattern.sub(right, query_lower)

    # Step 2: Fuzzy match with catalog
    if PRODUCT_CATALOG:
        try:
            from rapidfuzz import process, fuzz
            # Extract the single best match from the catalog
            # token_set_ratio is great for STT because it handles "I want obour land" matching "obour land"
            match_tuple = process.extractOne(query_lower, PRODUCT_CATALOG, scorer=fuzz.token_set_ratio)
            if match_tuple:
                match, score, _ = match_tuple
                if score >= 65:  # Lower threshold works better with token_set_ratio
                    print(f"[Fuzzy] Corrected '{query}' -> '{match}' (score: {score:.1f})")
                    return match
        except ImportError:
            pass # fallback if rapidfuzz isn't installed
            
    return query_lower

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(text: str = Form(...), session_id: str = Form("default")):
    # Correct STT mishearings before processing
    corrected_text = apply_query_corrections(text)
    response = await bot.set_session(session_id).chat(corrected_text)
    
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
        # Use English
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
