# 🛒 MarketAI: Smart Supermarket Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![IRYM SDK](https://img.shields.io/badge/IRYM_SDK-AI_Framework-blueviolet?style=for-the-badge)](https://github.com/blackeagle686/IRYM_sdk)
[![OpenAI](https://img.shields.io/badge/OpenAI-LLM-green?style=for-the-badge&logo=openai)](https://openai.com/)

**MarketAI** is a premium, AI-powered chatbot designed to revolutionize the supermarket shopping experience. Built with **FastAPI** and the **IRYM SDK**, it leverages advanced **RAG (Retrieval-Augmented Generation)** to provide instant information about products, prices, and descriptions from a catalog.

---

## ✨ Features

- **🧠 RAG-Powered Intelligence**: Instantly retrieves product data from `data_set.xlsx`.
- **💬 Natural Interactions**: Powered by OpenAI LLM for human-like supermarket assistance.
- **🌿 Fresh Aesthetics**: A modern, responsive **Glassmorphism** UI with emerald-green accents.
- **📱 Responsive Design**: Seamless experience across mobile, tablet, and desktop.
- **🚀 Colab-Ready**: Built-in support for testing on Google Colab with **ngrok** integration.
- **🗂️ Persistent Memory**: Remembers user context and past questions for a personalized experience.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, IRYM SDK, SQLAlchemy, Redis.
- **AI/LLM**: OpenAI (LLM), RAG Pipeline.
- **Frontend**: Bootstrap 5, Vanilla JavaScript, Custom CSS (Glassmorphism).
- **Deployment**: Ngrok, Uvicorn.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+
- Redis Server (for memory/caching)
- OpenAI API Key

### 2. Local Installation
```bash
# Clone the repository
git clone https://github.com/blackeagle686/market_chat_bot.git
cd market_chat_bot

# Install dependencies
pip install -r requirements.txt

# Set your API Key
export OPENAI_API_KEY="your-openai-key"

# Run the server
python main.py
```

### 3. Google Colab Testing
MarketAI is optimized for Colab! Just upload the project and run:
```python
import os
os.environ["OPENAI_API_KEY"] = "your-key"
os.environ["NGROK_AUTH_TOKEN"] = "your-ngrok-token"

!python run_colab.py
```

---

## 📂 Project Structure

```text
.
├── main.py              # Core FastAPI Application
├── run_colab.py         # Colab-specific runner with Ngrok
├── requirements.txt     # Production dependencies
├── data_set.xlsx        # Supermarket product catalog
├── static/
│   ├── main.js          # Frontend interaction logic
│   └── style.css        # Premium Glassmorphism styles
├── templates/
│   └── index.html       # Bootstrap 5 frontend template
└── IRYM_sdk/            # AI Infrastructure SDK (Submodule)
```

---

## 🎨 UI Preview

The interface features a sleek emerald-green theme with transparent cards, smooth animations, and a responsive chat window that makes finding products as easy as sending a message.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
Developed with ❤️ by the **MarketAI Team** using **IRYM SDK**.
