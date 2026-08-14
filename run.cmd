@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] uv is not installed or not on PATH.
    echo Install it from https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

echo Syncing dependencies...
uv sync
if errorlevel 1 (
    echo [ERROR] uv sync failed. See output above.
    pause
    exit /b 1
)

if not defined OPENAI_API_KEY (
    if not exist .env (
        echo [WARNING] OPENAI_API_KEY is not set and no .env file was found.
        echo Copy .env.example to .env and fill in your key, or set OPENAI_API_KEY / OPENAI_BASE_URL as environment variables.
        echo The app will still launch, but LLM calls will fail until this is set.
        echo.
    )
)

echo Launching Codebase Understanding Agent on port 8541...
uv run streamlit run app.py --server.port 8541

echo.
echo App stopped.
pause
