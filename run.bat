@echo off
TITLE Turnitin Lokal - Plagiarism Checker
chcp 65001 > NUL
setlocal enabledelayedexpansion

echo ============================================================
echo   Turnitin Lokal — Cek Plagiarisme Skripsi Gratis
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Cek atau deteksi Python & Venv
set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else if exist "D:\skripsi\skripsi_spam\Code_Spam_Email\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=D:\skripsi\skripsi_spam\Code_Spam_Email\.venv\Scripts\python.exe"
)

if "%PYTHON_CMD%"=="" (
    python --version > NUL 2>&1
    if errorlevel 1 (
        echo [ERROR] Python3 tidak ditemukan di sistem Anda!
        echo Silakan unduh dan install Python 3.10+ dari: https://www.python.org/downloads/
        echo PENTING: Centang "Add Python to PATH" saat instalasi.
        pause
        exit /b 1
    )
    
    echo [1/3] Membuat Virtual Environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat virtual environment!
        pause
        exit /b 1
    )
    set "PYTHON_CMD=.venv\Scripts\python.exe"
    
    echo [2/3] Mengunduh & menginstall modul dependensi (requirements.txt)...
    "%PYTHON_CMD%" -m pip install --upgrade pip > NUL 2>&1
    "%PYTHON_CMD%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Gagal menginstall dependensi!
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual Environment siap dipakai: %PYTHON_CMD%
)

REM 2. Salin .env.example ke .env jika belum ada
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Membuat file .env dari .env.example...
        copy .env.example .env > NUL
    )
)

REM 3. Otomatis Buka Web Browser ke http://localhost:5001 setelah 3 detik
start "" powershell -Command "Start-Sleep -Seconds 3; Start-Process 'http://localhost:5001'"

REM 4. Menjalankan Server Aplikasi
echo.
echo [3/3] Menjalankan Server Aplikasi...
echo Akses Web: http://localhost:5001
echo Tekan Ctrl+C di terminal ini untuk menghentikan server.
echo ============================================================
echo.

cd /d "%~dp0app"
"%PYTHON_CMD%" server.py

pause
