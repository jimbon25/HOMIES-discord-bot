#!/bin/bash

# ==========================================
# Discord Bot - Android/Termux Setup Script
# Optimized for Cloud Emulator (Rooted)
# ==========================================

echo "🚀 Starting Discord Bot Setup for Android/Termux..."

# 1. Update system packages
echo "📦 Updating packages..."
pkg update -y && pkg upgrade -y

# 2. Install Python and essential dependencies
echo "🐍 Checking Python installation..."
pkg install python git libffi openssl -y

# 3. Project Directory setup
PROJECT_DIR="$(pwd)"
echo "📂 Working in directory: $PROJECT_DIR"

# 4. Setup Virtual Environment (VENV)
# This keeps dependencies isolated and prevents "anti-miss" errors
echo "🌐 Setting up Virtual Environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "✅ Virtual environment created."
fi

# Activate VENV
source venv/bin/activate

# 5. Install/Update Python Libraries (Anti-Error Version)
echo "📚 Installing/Updating required Python libraries..."
pip install --upgrade pip
pip install discord.py python-dotenv aiofiles cryptography requests

# Verify installation success
if [ $? -eq 0 ]; then
    echo "✅ All dependencies installed successfully!"
else
    echo "❌ ERROR: Failed to install dependencies. Check your internet connection."
    exit 1
fi

# 6. Sanity Checks
echo "🔍 Running sanity checks..."
if [ ! -f "bot.py" ]; then
    echo "❌ ERROR: bot.py not found in the current directory!"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found! Bot might fail to start without a TOKEN."
fi

# 7. Start the Bot with Wake Lock
# Wake lock prevents Android from killing the process when the screen is off
echo "🤖 Starting the Bot..."
if command -v termux-wake-lock &> /dev/null; then
    termux-wake-lock
    echo "🔒 Wake-lock enabled (preventing CPU sleep)."
fi

python bot.py
