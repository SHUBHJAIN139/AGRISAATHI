@echo off
REM =============================================================================
REM AgriSaathi — Windows Verification Script
REM =============================================================================
REM Run this AFTER setup_windows.bat to verify the install.
REM Runs unit tests and checks critical imports.
REM
REM Usage: Double-click this file, or run from CMD:
REM   scripts\verify_windows.bat
REM =============================================================================

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0.."
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "ERRORS=0"
set "TESTS_RUN=0"

echo.
echo ============================================================
echo   AgriSaathi - Verification
echo ============================================================
echo.

REM --- Activate venv ---
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at %VENV_DIR%
    echo        Run scripts\setup_windows.bat first.
    set "ERRORS=1"
    goto :done
)
call "%VENV_DIR%\Scripts\activate.bat"

REM --- Change to project directory ---
pushd "%PROJECT_DIR%"

REM --- Test 1: Import smoke tests ---
echo [1/4] Running import smoke tests...
echo.
python -m pytest tests\unit\test_imports.py -v --tb=short 2>&1
if errorlevel 1 (
    echo.
    echo       FAIL: Import tests had failures
    set "ERRORS=1"
) else (
    echo       PASS
)
set /a "TESTS_RUN+=1"
echo.

REM --- Test 2: Security tests ---
echo [2/4] Running security tests...
echo.
python -m pytest tests\unit\test_security.py -v --tb=short 2>&1
if errorlevel 1 (
    echo.
    echo       FAIL: Security tests had failures
    set "ERRORS=1"
) else (
    echo       PASS
)
set /a "TESTS_RUN+=1"
echo.

REM --- Test 3: CropDoctor tests ---
echo [3/4] Running CropDoctor tests...
echo.
python -m pytest tests\unit\test_crop_doctor.py -v --tb=short 2>&1
if errorlevel 1 (
    echo.
    echo       FAIL: CropDoctor tests had failures
    set "ERRORS=1"
) else (
    echo       PASS
)
set /a "TESTS_RUN+=1"
echo.

REM --- Test 4: ADK LlmAgent import ---
echo [4/4] Verifying ADK LlmAgent import...
python -c "from google.adk.agents import LlmAgent; print('       google-adk LlmAgent ... OK')"
if errorlevel 1 (
    echo       FAIL: google-adk LlmAgent not importable
    set "ERRORS=1"
) else (
    set /a "TESTS_RUN+=1"
)
echo.

popd

:done
echo ============================================================
if "%ERRORS%"=="0" (
    echo   ALL %TESTS_RUN% CHECKS PASSED
    echo.
    echo   You're ready! Start the server:
    echo     .venv\Scripts\activate
    echo     python -m uvicorn api.main:app --port 8080
    echo.
    echo   Then open: http://localhost:8080/health
) else (
    echo   VERIFICATION FAILED - See errors above
    echo.
    echo   Common fixes:
    echo     - Re-run scripts\setup_windows.bat
    echo     - Check pip install output for build errors
    echo     - Ensure MOCK_LLM=true in .env
)
echo ============================================================
echo.

endlocal
pause
