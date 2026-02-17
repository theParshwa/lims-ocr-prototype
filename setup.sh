#!/usr/bin/env bash
# ============================================================
# LIMS OCR Document Processor - Linux/macOS Setup Script
# ============================================================

set -e

echo ""
echo "============================================================"
echo " LIMS OCR Document Processor - Setup"
echo "============================================================"
echo ""

# --- System dependencies ---
echo "[1/5] Checking system dependencies..."
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y tesseract-ocr poppler-utils libmagic1
elif command -v brew &>/dev/null; then
    brew install tesseract poppler
else
    echo "  WARNING: Could not install Tesseract/Poppler automatically."
    echo "  Please install them manually for OCR support."
fi

# --- Backend setup ---
echo "[2/5] Setting up Python backend..."
cd backend

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "  >> .env file created. Edit backend/.env and add your API key:"
    echo "     OPENAI_API_KEY=sk-..."
    echo "     (or ANTHROPIC_API_KEY for Anthropic Claude)"
    echo ""
fi

echo "[3/5] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[4/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[5/5] Setting up frontend..."
cd ../frontend
npm install

echo ""
echo "============================================================"
echo " Setup complete!"
echo ""
echo " To start the application:"
echo ""
echo " Terminal 1 (Backend):"
echo "   cd backend && source venv/bin/activate"
echo "   uvicorn api.main:app --reload --port 8000"
echo ""
echo " Terminal 2 (Frontend):"
echo "   cd frontend && npm run dev"
echo ""
echo " Then open: http://localhost:3000"
echo " API docs:  http://localhost:8000/docs"
echo "============================================================"
echo ""

# Generate sample test documents
echo "Generating sample test documents..."
cd ../backend
source venv/bin/activate
python tests/create_sample_docs.py

cd ..
