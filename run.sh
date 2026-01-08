#!/bin/bash
echo "🚀 Starting HireLink..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it."
    exit 1
fi

# Install dependencies if needed
if [ ! -f .installed ]; then
    echo "📦 Installing dependencies..."
    python3 -m pip install -r requirements.txt
    touch .installed
fi

# Run the app
echo "✨ Launching Streamlit App..."
python3 -m streamlit run app.py
