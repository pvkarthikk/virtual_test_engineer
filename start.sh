#!/bin/bash
# Virtual Test Engineer Startup Script

echo "🚀 Starting Virtual Test Engineer..."
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Start the server
echo "🌐 Starting server on http://localhost:8080"
echo "Press Ctrl+C to stop"
echo ""

python -m src.main --reload