@echo off
echo ============================================================
echo PRODUCT ENRICHER - Local Execution
echo ============================================================
cd /d D:\Projects\brand-protection-poc

REM Set PYTHONPATH to include current directory
set PYTHONPATH=%CD%

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please create a .env file with your SUPABASE_URL and SUPABASE_KEY.
    echo You can copy .env.example to .env and fill in the values.
    pause
    exit /b 1
)

echo Running enricher with default settings...
echo.
python enrichers/product_enricher.py 50

echo.
echo ============================================================
echo Done! Check enricher_status.json for progress.
echo ============================================================
pause
