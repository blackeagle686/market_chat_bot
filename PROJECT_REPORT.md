# 🛒 MarketAI — Project Report

**MarketAI** is an intelligent, voice-enabled supermarket assistant designed to help customers find products, check prices, and navigate the store. It combines a modern web interface with advanced AI (RAG) to provide accurate, real-time information from a product catalog.

## 🛠 Technology Stack

### **Backend (Python)**
*   **FastAPI**: The core web framework, chosen for its high performance and asynchronous support.
*   **SQLAlchemy**: ORM for managing the SQLite database.
*   **IRYM SDK**: A custom AI SDK used to build the RAG (Retrieval-Augmented Generation) pipeline.
*   **LongCat AI (OpenAI-Compatible)**: Used as the primary LLM provider for chat reasoning and product search.
*   **Redis**: Used for session management and potentially task queuing.

### **Frontend**
*   **HTML5 / Jinja2**: Template engine for server-side rendering.
*   **Vanilla CSS3**: Custom design system featuring Glassmorphism, Dark Mode, and premium animations.
*   **Vanilla JavaScript**: Handles real-time chat, voice recording, and UI state management.
*   **Marked.js**: For rendering LLM Markdown responses.

### **AI / Multimedia**
*   **RAG (Retrieval-Augmented Generation)**: Uses Excel-based datasets and ChromaDB (via IRYM SDK) for context-aware answers.
*   **gTTS (Google Text-to-Speech)**: Converts AI responses into natural-sounding audio.
*   **SpeechRecognition**: Handles STT (Speech-to-Text) using Google's API as a fallback for browsers without Web Speech support.
*   **Fuzzy Matching (RapidFuzz)**: Used for correcting user speech input and matching images to products.

### **Deployment**
*   **Systemd**: Manages the application and Ngrok as background services on Linux.
*   **Ngrok**: Provides a secure public tunnel for remote access.
*   **Bash Scripts**: Automated deployment (`deploy.sh`) and synchronization (`git_master.py`).

---

## 📡 API Endpoints

### **Core Interaction**
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Landing page (Splash screen). |
| `/chat` | `POST` | Processes user text, returns AI answer, audio URL, and detected product images. |
| `/transcribe` | `POST` | Converts uploaded audio files (WebM/WAV) into text. |
| `/catalog` | `GET` | Main product catalog browser. |
| `/search` | `GET` | Global search across all products. |

### **Data & Images**
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/product_image` | `GET` | Retrieves a specific product image URL via fuzzy name matching. |
| `/category/{id}` | `GET` | Shows all products within a specific category. |
| `/rate/{id}` | `POST` | Allows users to submit star ratings for products. |

### **Admin Panel**
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/admin/login` | `GET/POST` | Secure login for store administrators. |
| `/admin/products` | `GET` | Dashboard for managing the product list. |
| `/admin/product/edit/{id}` | `GET/POST` | Interface to update product details and upload new images. |

---

## 📂 Key Features

1.  **Automatic Image Detection**: The system identifies product names within AI responses and automatically displays their photos in the chat window.
2.  **Voice-First Interface**: Supports real-time microphone input with visual equalizer feedback.
3.  **Smart Corrections**: Uses a custom JSON-based dictionary (`stt_corrections.json`) to fix common mishearings (e.g., "Overland" → "Obour Land").
4.  **Admin Image-Product Matching**: Includes scripts to automatically pair thousands of product images with Excel data using OCR and fuzzy matching.
5.  **Multi-Session Memory**: The IRYM SDK maintains chat history for personalized shopping assistance.

---

## 🚀 Deployment Overview
The project is designed to run on a Linux server (Ubuntu) with a single command:
1.  `chmod +x deploy.sh`
2.  `./deploy.sh`

This script automates the installation of Redis, FFmpeg, Python dependencies, database migration, and sets up the **Ngrok tunnel** for global accessibility.
