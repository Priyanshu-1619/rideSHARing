#!/bin/bash
# Production environment test script
# This script starts the application using Gunicorn (like on Render)

echo "🚀 Starting rideSHARing in production mode..."
echo "================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Export environment variables
export FLASK_ENV=production
export PORT=8000

# Create database directory if it doesn't exist
mkdir -p database

echo ""
echo "✅ Setup complete!"
echo "================================================"
echo "🌐 Starting Gunicorn server on 0.0.0.0:8000"
echo "🔗 Visit: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================"
echo ""

# Start the application with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 wsgi:app
