#!/bin/bash

# Exit on any error
set -e

echo "--- Starting Native Deployment on mohamed-01095513686 (95.216.63.78) ---"

# 1. Install System Dependencies
echo "[1/5] Checking system dependencies..."
for pkg in python3-pip python3-venv redis-server ffmpeg git libmagic1 unzip; do
    if ! dpkg -s $pkg >/dev/null 2>&1; then
        echo "Installing $pkg..."
        sudo apt-get update -y && sudo apt-get install -y $pkg
    fi
done

# 2. Start Redis
echo "[2/5] Ensuring Redis is running..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 3. Setup Project
REPO_DIR="market_chat_bot"
REPO_URL="https://github.com/blackeagle686/market_chat_bot.git"

if [ -d "$REPO_DIR" ]; then
    echo "[3/5] Updating repository..."
    if [ "$(basename "$PWD")" != "$REPO_DIR" ]; then
        cd "$REPO_DIR"
    fi
    git fetch origin master
    git reset --hard origin/master
else
    echo "[3/5] Cloning repository..."
    git clone "$REPO_URL"
    cd "$REPO_DIR"
fi

# 4. Setup Virtual Environment and Requirements
if [ ! -d "venv" ]; then
    echo "[4/5] Creating new virtual environment..."
    python3 -m venv venv
else
    echo "[4/5] Using existing virtual environment."
fi

source venv/bin/activate
echo "Checking Python dependencies..."
pip install -r requirements.txt --quiet
pip install pyngrok --quiet

# --- NEW STEP: Upload Data ---
echo "[*] Uploading product data from Excel..."
PYTHONPATH=. ./venv/bin/python3 ./scripts/upload_data.py ./insight/data_set.xlsx
# -----------------------------

# 5. Setup Systemd Services
echo "[5/5] Configuring systemd services..."
PROJECT_PATH=$(pwd)
SERVICE_FILE="/etc/systemd/system/market_bot.service"
NGROK_SERVICE_FILE="/etc/systemd/system/market_ngrok.service"
NGROK_AUTH_TOKEN="36jW6kAV8Inp5SHYiuIicuuRols_7NkiWdLme3iULLJx3gMS5"

# Main App Service
sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Market Chat Bot FastAPI App
After=network.target redis-server.service

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_PATH
Environment=\"PATH=$PROJECT_PATH/venv/bin\"
Environment=\"OPENAI_API_KEY=ak_2yp3Xw1Ny7ky2pF7er9x93ZO9jj6G\"
Environment=\"OPENAI_BASE_URL=https://api.longcat.chat/openai\"
Environment=\"REDIS_URL=redis://localhost:6379\"
ExecStart=$PROJECT_PATH/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

# Ngrok Tunnel Service
sudo bash -c "cat <<EOF > $NGROK_SERVICE_FILE
[Unit]
Description=Ngrok Tunnel for Market Chat Bot
After=network.target market_bot.service

[Service]
User=$USER
WorkingDirectory=$PROJECT_PATH
Environment=\"PATH=$PROJECT_PATH/venv/bin\"
ExecStart=$PROJECT_PATH/venv/bin/python3 scripts/ngrok_tunnel.py $NGROK_AUTH_TOKEN
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload

echo "Starting services..."
sudo systemctl enable market_bot market_ngrok
sudo systemctl restart market_bot market_ngrok

echo "Waiting for ngrok tunnel to stabilize..."
sleep 5

NGROK_URL=$(cat ngrok_url.txt 2>/dev/null || echo "Pending... check later in ngrok_url.txt")

echo "===================================================="
echo "SUCCESS: Market Chat Bot is running with Ngrok!"
echo "Service Names: market_bot, market_ngrok"
echo "Local URL: http://localhost:8000"
echo "Public URL (Ngrok): $NGROK_URL"
echo "Check logs with: sudo journalctl -u market_bot -f"
echo "Check ngrok logs: sudo journalctl -u market_ngrok -f"
echo "===================================================="
