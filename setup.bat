@echo off
echo === AgriSaathi Setup ===
echo.

cd /d "C:\Users\Dell\.gemini\antigravity\scratch\agri-saathi"

echo --- Step 1: Checking Python ---
"E:\python311\python.exe" --version

echo.
echo --- Step 2: Creating venv ---
"E:\python311\python.exe" -m venv .venv
if errorlevel 1 goto :error

echo.
echo --- Step 3: Activating venv ---
call .venv\Scripts\activate.bat

echo.
echo --- Step 4: Verifying venv Python ---
python --version
where python

echo.
echo --- Step 5: Upgrading pip ---
python -m pip install --upgrade pip

echo.
echo --- Step 6: Installing dependencies ---
pip install -e ".[dev]"
if errorlevel 1 goto :error

echo.
echo === Setup complete! ===
echo Next: run check.bat to verify everything works.
goto :eof

:error
echo.
echo === ERROR during setup ===
echo Paste the output above to your assistant.
pause