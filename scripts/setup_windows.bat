@echo off
REM =============================================================================
REM AgriSaathi — Windows Setup Script
REM =============================================================================
REM Uses E:\python311\python.exe explicitly.
REM Creates venv if missing, installs deps, verifies critical imports.
REM
REM Usage: Double-click this file, or run from CMD:
REM   scripts\setup_windows.bat
REM =============================================================================

setlocal enabledelayedexpansion

set "PYTHON_EXE=E:\python311\python.exe"
set "PROJECT_DIR=%~dp0.."
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "ERRORS=0"

echo.
echo ============================================================
echo   AgriSaathi - Windows Setup
echo ============================================================
echo.

REM --- Step 1: Verify Python exists ---
echo [1/5] Checking Python at %PYTHON_EXE% ...
if not exist "%PYTHON_EXE%" (
    echo.
    echo ERROR: Python not found at %PYTHON_EXE%
    echo        Please install Python 3.11 at that path, or edit
    echo        the PYTHON_EXE variable at the top of this script.
    echo.
    set "ERRORS=1"
    goto :done
)

"%PYTHON_EXE%" --version
echo       OK
echo.

REM --- Step 2: Create venv if missing ---
echo [2/5] Checking virtual environment at %VENV_DIR% ...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo       Creating virtual environment...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        set "ERRORS=1"
        goto :done
    )
    echo       Created.
) else (
    echo       Already exists.
)
echo.

REM --- Step 3: Activate venv ---
echo [3/5] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    set "ERRORS=1"
    goto :done
)
echo       OK (using: %VIRTUAL_ENV%)
echo.

REM --- Step 4: Install dependencies ---
echo [4/5] Installing dependencies (pip install -e ".[dev]") ...
echo       This may take a few minutes on first run...
echo.
pip install --prefer-binary -e "%PROJECT_DIR%[dev]"
if errorlevel 1 (
    echo.
    echo WARNING: pip install had errors. Trying with --no-build-isolation ...
    pip install --prefer-binary --no-build-isolation -e "%PROJECT_DIR%[dev]"
    if errorlevel 1 (
        echo.
        echo ERROR: pip install failed. See output above for details.
        set "ERRORS=1"
        goto :done
    )
)
echo.
echo       pip install complete.
echo.

REM --- Step 5: Verify critical imports ---
echo [5/5] Verifying critical imports...
echo.

python -c "import fastapi; print('       fastapi', fastapi.__version__, '... OK')"
if errorlevel 1 (
    echo       FAIL: fastapi not importable
    set "ERRORS=1"
)

python -c "import jwt; print('       pyjwt', jwt.__version__, '... OK')"
if errorlevel 1 (
    echo       FAIL: pyjwt not importable
    set "ERRORS=1"
)

python -c "import structlog; print('       structlog', structlog.__version__, '... OK')"
if errorlevel 1 (
    echo       FAIL: structlog not importable
    set "ERRORS=1"
)

python -c "from google.adk.agents import LlmAgent; print('       google-adk LlmAgent ... OK')"
if errorlevel 1 (
    echo       FAIL: google-adk not importable
    set "ERRORS=1"
)

echo.

:done
echo ============================================================
if "%ERRORS%"=="0" (
    echo   SETUP PASSED - All checks OK
    echo.
    echo   Next steps:
    echo     1. Run: scripts\verify_windows.bat
    echo     2. Then: python -m uvicorn api.main:app --port 8080
) else (
    echo   SETUP FAILED - See errors above
    echo.
    echo   Common fixes:
    echo     - Ensure E:\python311\python.exe exists
    echo     - Run CMD as Administrator if permission errors
    echo     - Check your internet connection for pip
)
echo ============================================================
echo.

endlocal
pause
