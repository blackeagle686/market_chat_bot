#!/bin/bash

# Exit on any error
set -e

echo "--- Starting Deployment on mohamed-01095513686 (95.216.63.78) ---"

# 1. Update system and install dependencies
echo "[1/4] Installing system dependencies (Docker, Git)..."
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose git

# 2. Clone or Update the repository
REPO_DIR="market_chat_bot"
REPO_URL="https://github.com/blackeagle686/market_chat_bot.git"

if [ -d "$REPO_DIR" ]; then
    echo "[2/4] Updating existing repository..."
    cd "$REPO_DIR"
    git pull origin master
else
    echo "[2/4] Cloning repository..."
    git clone "$REPO_URL"
    cd "$REPO_DIR"
fi

# 3. Build and Start the containers
echo "[3/4] Building and starting containers with Docker Compose..."
# Ensure any old containers are stopped
sudo docker-compose down || true
# Build and start in detached mode
sudo docker-compose up --build -d

# 4. Final check
echo "[4/4] Verifying deployment..."
sleep 5
if sudo docker ps | grep -q "market_chat_bot_app"; then
    echo "===================================================="
    echo "SUCCESS: Market Chat Bot is running!"
    echo "Access it at: http://95.216.63.78:8000"
    echo "===================================================="
else
    echo "ERROR: Deployment failed. Check logs with 'sudo docker-compose logs'"
    exit 1
fi
