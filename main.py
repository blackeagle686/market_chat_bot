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
from database import SessionLocal, Category, Product, User, init_db
from fastapi.responses import RedirectResponse

def clean_text_for_speech(text: str) -> str:
    """Removes Markdown symbols and adds descriptive words for prices/partitions."""
    
    # 1. Handle Markdown Tables specifically for better descriptive flow
    def process_table_rows(match):
        row = match.group(0).strip()
        # Skip separator rows like |---|---|
        if re.match(r'^\|?\s*(?:-+\s*\|?)+\s*$', row):
            return ""
        
        # Split and clean parts
        parts = [p.strip() for p in row.split('|') if p.strip()]
        
        # Skip header row
        if any(h in parts[0].lower() for h in ["product name", "item", "name"]):
            return ""
            
        if len(parts) >= 2:
            name = parts[0]
            price = parts[1]
            # Clean price (remove EGP etc)
            price_val = re.sub(r'[^\d\.]', '', price)
            desc = f"{name}, price is {price_val} pounds"
            
            if len(parts) >= 3:
                partition = parts[2]
                part_val = re.sub(r'[^\d]', '', partition)
                if part_val:
                    desc += f", partition number is {part_val}"
            # Add a significant pause between rows for better clarity
            return desc + " . . . "
        return row

    # Identify and process table rows before general stripping
    text = re.sub(r'^\|.*\|$', process_table_rows, text, flags=re.MULTILINE)

    # 2. General cleanup for non-table text
    # Replace EGP with 'pounds' and ensure 'price is' context if missing
    text = re.sub(r'(\d+(?:\.\d+)?)\s*EGP', r'price is \1 pounds', text, flags=re.IGNORECASE)
    text = re.sub(r'\bEGP\b', 'pounds', text, flags=re.IGNORECASE)
    
    # Remove remaining markdown and suggestions
    text = re.sub(r'\[Suggestions: [^\]]+\]', '', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = text.replace('|', ',')
    text = text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
    text = re.sub(r'#+\s', '', text)
    
    # Final whitespace and comma cleanup
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r',\s*,', ',', text)
    text = text.strip(' ,')
    
    return text

def extract_partition_number(text: str) -> int:
    """
    Extracts the partition number from the LLM's Markdown answer.
    Looks for 'Partition' followed by a number or the last column of a table.
    """
    # Try common patterns first
    # 1. "Partition: 5" or "Partition 5" or "partition:5"
    match = re.search(r'partition[:\s]+(\d+)', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # 2. Look in Markdown tables. Partition is usually the last column.
    # Pattern: | Name | Price | 5 |
    lines = text.split('\n')
    for line in lines:
        if '|' in line:
            # Split by | and filter out empty strings from the ends
            parts = [p.strip() for p in line.split('|') if p.strip()]
            # If we have at least 3 parts (Name, Price, Partition)
            if len(parts) >= 3:
                # Check if the last part is a number
                last_part = parts[-1]
                # Remove any non-numeric chars if needed, but simple \d+ is better
                num_match = re.search(r'(\d+)', last_part)
                if num_match:
                    return int(num_match.group(1))
                    
    return 0

from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="Market AI ChatBot")

# Session middleware for admin authentication
app.add_middleware(SessionMiddleware, secret_key="super-secret-key-change-me")

# Setup static files and templates
os.makedirs("static", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)
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
           "When listing products, ALWAYS use a Markdown table with columns: Product Name | Price | Partition.\n"
           "10. At the very end of every response, provide exactly 3 short follow-up suggestions for the user to help them shop better. "
           "Format them strictly as: [Suggestions: Suggestion 1, Suggestion 2, Suggestion 3]. Keep each suggestion under 5 words."
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
    
    # Simple migration: add rating and image_url columns if they don't exist
    db = SessionLocal()
    try:
        from sqlalchemy import text
        # Ignore errors if columns already exist
        try: db.execute(text("ALTER TABLE products ADD COLUMN rating FLOAT DEFAULT 4.5")); db.commit()
        except Exception: db.rollback()
        
        try: db.execute(text("ALTER TABLE products ADD COLUMN rating_count INTEGER DEFAULT 1")); db.commit()
        except Exception: db.rollback()
        
        try: db.execute(text("ALTER TABLE products ADD COLUMN image_url TEXT")); db.commit()
        except Exception: db.rollback()
        
        print("[+] Database migrated with rating and image_url columns.")
    finally:
        db.close()

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

@app.post("/rate/{product_id}")
async def rate_product(product_id: int, rating: int = Form(...), db: Session = Depends(get_db)):
    if not (1 <= rating <= 5):
        return JSONResponse({"error": "Rating must be between 1 and 5"}, status_code=400)
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return JSONResponse({"error": "Product not found"}, status_code=404)
    
    # Calculate new average rating
    new_count = (product.rating_count or 0) + 1
    new_rating = ((product.rating or 0.0) * (product.rating_count or 0) + rating) / new_count
    
    product.rating = round(new_rating, 1)
    product.rating_count = new_count
    
    db.commit()
    return {"new_rating": product.rating, "new_count": product.rating_count}

# --- Admin Routes ---

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password == password: 
        request.session["admin_logged_in"] = True
        return RedirectResponse(url="/admin/products", status_code=303)
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login")

def is_admin(request: Request):
    return request.session.get("admin_logged_in")

@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request, q: str = None, page: int = 1, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login")
    
    limit = 20
    offset = (page - 1) * limit
    
    query = db.query(Product)
    if q:
        query = query.filter(Product.name.contains(q))
    
    total_products = query.count()
    products = query.offset(offset).limit(limit).all()
    total_pages = (total_products + limit - 1) // limit
    
    return templates.TemplateResponse("admin_products.html", {
        "request": request,
        "products": products,
        "page": page,
        "total_pages": total_pages,
        "query": q
    })

@app.get("/admin/product/edit/{product_id}", response_class=HTMLResponse)
async def edit_product_page(request: Request, product_id: int, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login")
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse(url="/admin/products")
    
    categories = db.query(Category).all()
    return templates.TemplateResponse("admin_edit_product.html", {
        "request": request,
        "product": product,
        "categories": categories
    })

@app.post("/admin/product/edit/{product_id}")
async def edit_product(
    request: Request, 
    product_id: int, 
    name: str = Form(...),
    price: float = Form(...),
    variant: str = Form(None),
    partition: str = Form(None),
    category_id: int = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login")
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse(url="/admin/products")
    
    product.name = name
    product.price = price
    product.variant = variant
    product.partition = partition
    product.category_id = category_id
    
    if image and image.filename:
        # Save image
        file_extension = os.path.splitext(image.filename)[1]
        filename = f"product_{product_id}_{uuid.uuid4().hex[:8]}{file_extension}"
        filepath = os.path.join("static/uploads", filename)
        
        with open(filepath, "wb") as f:
            f.write(await image.read())
        
        product.image_url = f"/static/uploads/{filename}"
    
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=303)

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
        # Detect language for gTTS (simplistic: check for Arabic characters)
        has_arabic = any("\u0600" <= c <= "\u06FF" for c in response)
        lang = 'ar' if has_arabic else 'en'
        
        clean_audio_text = clean_text_for_speech(response)
        tts = gTTS(text=clean_audio_text, lang=lang)
        tts.save(audio_path)
        
        partition = extract_partition_number(response)
        return {
            "answer": response, 
            "audio": f"/static/audio/{audio_filename}",
            "partition": partition
        }
    except Exception as e:
        print(f"TTS Error: {e}")
        return {"answer": response, "partition": extract_partition_number(response)}

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), lang: str = Form("en")):
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
        # Use appropriate language dialect
        sr_lang = "ar-SA" if lang == "ar" else "en-US"
        try:
            text = recognizer.recognize_google(audio_data, language=sr_lang)
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

@app.post("/extract_partition")
async def extract_partition(text: str = Form(...)):
    partition = extract_partition_number(text)
    return {"partition": partition}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
