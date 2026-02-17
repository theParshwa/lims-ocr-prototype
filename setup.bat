@echo off
REM ============================================================
REM LIMS OCR - Windows Setup Script
REM ============================================================

echo.
echo ============================================================
echo  LIMS OCR Document Processor - Setup
echo ============================================================
echo.

REM --- Backend setup ---
echo [1/4] Setting up Python backend...
cd backend

if not exist ".env" (
    copy .env.example .env
    echo.
    echo  >> .env file created from template.
    echo  >> IMPORTANT: Edit backend\.env and add your API key:
    echo  >>   OPENAI_API_KEY=sk-...
    echo  >>   (or ANTHROPIC_API_KEY for Anthropic Claude)
    echo.
)

echo [2/4] Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo [3/4] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [4/4] Setting up frontend...
cd ..\frontend
call npm install

echo.
echo ============================================================
echo  Setup complete!
echo.
echo  To start the application:
echo.
echo  Terminal 1 (Backend):
echo    cd backend
echo    venv\Scripts\activate
echo    uvicorn api.main:app --reload --port 8000
echo.
echo  Terminal 2 (Frontend):
echo    cd frontend
echo    npm run dev
echo.
echo  Then open: http://localhost:3000
echo  API docs:  http://localhost:8000/docs
echo ============================================================
echo.

REM Generate sample test documents
echo Generating sample test documents...
cd ..\backend
call venv\Scripts\activate.bat
python tests\create_sample_docs.py 2>nul || echo (python-docx not yet installed, run after pip install)

cd ..
